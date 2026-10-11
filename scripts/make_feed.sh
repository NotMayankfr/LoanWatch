#!/usr/bin/env bash
# Splits data/raw/lending_club_30col.csv into 5 daily vendor feeds (20261005..20261009)
# with SHA-256 manifests and generates the 6 negative-test scenarios (20261010..20261015).

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=../config/pipeline.env
source "${PROJECT_ROOT}/config/pipeline.env"

RAW_CSV="${PROJECT_ROOT}/data/raw/lending_club_30col.csv"
INBOUND_DIR="${PROJECT_ROOT}/data/inbound"

mkdir -p "${INBOUND_DIR}" \
         "${PROJECT_ROOT}/data/processing" \
         "${PROJECT_ROOT}/data/archive/raw" \
         "${PROJECT_ROOT}/data/archive/clean_parquet" \
         "${PROJECT_ROOT}/data/archive/scorecards" \
         "${PROJECT_ROOT}/data/rejects/file_level" \
         "${PROJECT_ROOT}/data/rejects/row_level" \
         "${PROJECT_ROOT}/reports/alerts" \
         "${PROJECT_ROOT}/reports/figures"

if [[ ! -f "${RAW_CSV}" ]]; then
    echo "[make_feed] Preparing 30-column source file from Kaggle archive..."
    python3 "${PROJECT_ROOT}/scripts/prepare_source_data.py" --output "${RAW_CSV}"
fi

TOTAL_LINES=$(wc -l < "${RAW_CSV}" | tr -d ' ')
TOTAL_DATA_ROWS=$((TOTAL_LINES - 1))
HEADER_LINE=$(head -n 1 "${RAW_CSV}" | tr -d '\r')

echo "[make_feed] Source file: ${RAW_CSV} (${TOTAL_DATA_ROWS} data rows)"

write_manifest() {
    local csv_file="$1"
    local batch_date="$2"
    local expected_rows="$3"
    local sha256_val="$4"
    local manifest_file="${csv_file%.csv}.manifest"

    cat > "${manifest_file}" <<EOF
FEED_FILE=$(basename "${csv_file}")
VENDOR_ID=${VENDOR_NAME}
BATCH_DATE=${batch_date}
SLA_DEADLINE_IST=${SLA_CUTOFF_HHMM}
EXPECTED_ROWS=${expected_rows}
SHA256=${sha256_val}
EOF
}

# Split full dataset across 5 daily feeds: 20261005 through 20261009
BATCH_DATES=("20261005" "20261006" "20261007" "20261008" "20261009")
ARRIVAL_TIMES=(
    "2026-10-05 06:12:00"
    "2026-10-06 06:08:00"
    "2026-10-07 06:21:00"
    "2026-10-08 07:18:00"
    "2026-10-09 06:15:00"
)

ROWS_PER_FEED=$(( (TOTAL_DATA_ROWS + 4) / 5 ))

echo "[make_feed] Splitting ${TOTAL_DATA_ROWS} rows across 5 daily feeds (~${ROWS_PER_FEED} rows/feed)..."

awk -v outdir="${INBOUND_DIR}" \
    -v per_feed="${ROWS_PER_FEED}" \
    'BEGIN {
        split("20261005 20261006 20261007 20261008 20261009", dates, " ")
        file_idx = 0
    }
    NR == 1 {
        header = $0
        next
    }
    {
        data_row = NR - 1
        target_idx = int((data_row - 1) / per_feed) + 1
        if (target_idx > 5) target_idx = 5
        if (target_idx != file_idx) {
            if (file_idx > 0) close(current_file)
            file_idx = target_idx
            current_file = outdir "/loan_tape_" dates[file_idx] ".csv"
            print header > current_file
        }
        print $0 > current_file
    }
    END {
        if (file_idx > 0) close(current_file)
    }' "${RAW_CSV}"

for i in "${!BATCH_DATES[@]}"; do
    bdate="${BATCH_DATES[$i]}"
    mtime="${ARRIVAL_TIMES[$i]}"
    f="${INBOUND_DIR}/loan_tape_${bdate}.csv"
    rows=$(( $(wc -l < "${f}") - 1 ))
    sha=$(sha256sum "${f}" | awk '{print $1}')
    write_manifest "${f}" "${bdate}" "${rows}" "${sha}"
    touch -d "${mtime}" "${f}" "${f%.csv}.manifest"
    echo "[make_feed] Created ${f##*/} (rows=${rows}, mtime='${mtime} IST')"
done

# Base 10,000-row clean slice (1 header + 10,000 data rows) for negative-test scenarios
BASE_SLICE="${INBOUND_DIR}/_base_10k.tmp"
head -n 10001 "${RAW_CSV}" > "${BASE_SLICE}"

# Scenario 1 (20261010): Truncated file -> Expected Exit 11 (checksum fires first)
F_20261010="${INBOUND_DIR}/loan_tape_20261010.csv"
cp "${BASE_SLICE}" "${F_20261010}"
ORIG_ROWS_10=10000
ORIG_SHA_10=$(sha256sum "${F_20261010}" | awk '{print $1}')
head -n 1251 "${BASE_SLICE}" > "${F_20261010}"
write_manifest "${F_20261010}" "20261010" "${ORIG_ROWS_10}" "${ORIG_SHA_10}"
touch -d "2026-10-10 06:10:00" "${F_20261010}" "${F_20261010%.csv}.manifest"
echo "[make_feed] Scenario 1 (20261010): Truncated file (1250 actual vs 10000 manifest, orig SHA) -> Exit 11"

# Scenario 2 (20261011): Wrong EXPECTED_ROWS with valid checksum -> Expected Exit 12
F_20261011="${INBOUND_DIR}/loan_tape_20261011.csv"
cp "${BASE_SLICE}" "${F_20261011}"
SHA_11=$(sha256sum "${F_20261011}" | awk '{print $1}')
write_manifest "${F_20261011}" "20261011" "10500" "${SHA_11}"
touch -d "2026-10-11 06:12:00" "${F_20261011}" "${F_20261011%.csv}.manifest"
echo "[make_feed] Scenario 2 (20261011): Manifest EXPECTED_ROWS=10500 (actual 10000, valid SHA) -> Exit 12"

# Scenario 3 (20261012): Renamed column in header -> Expected Exit 13
F_20261012="${INBOUND_DIR}/loan_tape_20261012.csv"
awk 'NR==1 {sub(/loan_amnt/, "principal_amt")} {print}' "${BASE_SLICE}" > "${F_20261012}"
ROWS_12=$(( $(wc -l < "${F_20261012}") - 1 ))
SHA_12=$(sha256sum "${F_20261012}" | awk '{print $1}')
write_manifest "${F_20261012}" "20261012" "${ROWS_12}" "${SHA_12}"
touch -d "2026-10-12 06:14:00" "${F_20261012}" "${F_20261012%.csv}.manifest"
echo "[make_feed] Scenario 3 (20261012): Header column renamed (loan_amnt -> principal_amt) -> Exit 13"

# Scenario 4 (20261013): Small payload breach (~1.0% bad rows) -> Expected Exit 0 with row-level rejects
F_20261013="${INBOUND_DIR}/loan_tape_20261013.csv"
awk -F',' -v OFS=',' '
    NR == 1 { print; next }
    NR == 2 { saved_row = $0; print; next }
    NR >= 3 && NR <= 27 {
        # 25 exact duplicate loan IDs
        print saved_row
        next
    }
    NR >= 28 && NR <= 52 {
        # 25 consistency breaches: funded_amnt > loan_amnt
        $3 = $2 + 5000
        print
        next
    }
    NR >= 53 && NR <= 77 {
        # 25 validity breaches: invalid state code XX and extreme DTI 999
        $17 = "XX"
        $18 = "999.0"
        print
        next
    }
    NR >= 78 && NR <= 102 {
        # 25 completeness breaches: null grade and null issue_d
        $8 = ""
        $14 = ""
        print
        next
    }
    { print }
' "${BASE_SLICE}" > "${F_20261013}"
ROWS_13=$(( $(wc -l < "${F_20261013}") - 1 ))
SHA_13=$(sha256sum "${F_20261013}" | awk '{print $1}')
write_manifest "${F_20261013}" "20261013" "${ROWS_13}" "${SHA_13}"
touch -d "2026-10-13 06:16:00" "${F_20261013}" "${F_20261013%.csv}.manifest"
echo "[make_feed] Scenario 4 (20261013): Small payload breach (~1.0% bad rows, real manifest) -> Exit 0 w/ rejects"

# Scenario 5 (20261014): >8% payload breach (9.5% bad rows) -> Expected Exit 20
F_20261014="${INBOUND_DIR}/loan_tape_20261014.csv"
awk -F',' -v OFS=',' '
    NR == 1 { print; next }
    NR >= 2 && NR <= 951 {
        # 950 rows (9.5%) corrupted with funded_amnt > loan_amnt and invalid grade Z
        $3 = $2 + 10000
        $8 = "Z"
        $17 = "ZZ"
        print
        next
    }
    { print }
' "${BASE_SLICE}" > "${F_20261014}"
ROWS_14=$(( $(wc -l < "${F_20261014}") - 1 ))
SHA_14=$(sha256sum "${F_20261014}" | awk '{print $1}')
write_manifest "${F_20261014}" "20261014" "${ROWS_14}" "${SHA_14}"
touch -d "2026-10-14 06:18:00" "${F_20261014}" "${F_20261014%.csv}.manifest"
echo "[make_feed] Scenario 5 (20261014): High payload breach (9.5% bad rows > 5.0% limit) -> Exit 20"

# Scenario 6 (20261015): Missing feed -> Expected Exit 10
rm -f "${INBOUND_DIR}/loan_tape_20261015.csv" "${INBOUND_DIR}/loan_tape_20261015.manifest"
echo "[make_feed] Scenario 6 (20261015): No file generated in data/inbound/ -> Exit 10"

rm -f "${BASE_SLICE}"
echo "[make_feed] Feed generation complete."
