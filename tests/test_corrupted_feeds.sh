#!/usr/bin/env bash
# End-to-end verification of the 6 negative-test scenarios through scripts/ingest.sh:
#   - 20261010 (Truncated file)                         -> Exit 11 (checksum fires first)
#   - 20261011 (Wrong EXPECTED_ROWS, valid checksum)    -> Exit 12
#   - 20261012 (Renamed column in header)               -> Exit 13
#   - 20261013 (Small ~1% payload breach)               -> Exit 0 with row-level rejects written
#   - 20261014 (>8% payload breach)                     -> Exit 20
#   - 20261015 (Missing feed)                           -> Exit 10

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INGEST="${PROJECT_ROOT}/scripts/ingest.sh"

PASS_COUNT=0
FAIL_COUNT=0

assert_exit_code() {
    local batch_date="$1"
    local expected_code="$2"
    local label="$3"

    "${INGEST}" --batch-date "${batch_date}" --skip-downstream >/dev/null 2>&1
    local actual_code=$?

    if [[ "${actual_code}" -eq "${expected_code}" ]]; then
        echo "[PASS] ${batch_date} (${label}): expected exit ${expected_code}, got ${actual_code}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "[FAIL] ${batch_date} (${label}): expected exit ${expected_code}, got ${actual_code}" >&2
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

echo "=== Running 6 Negative-Test Scenarios Against scripts/ingest.sh ==="

assert_exit_code "20261010" 11 "Truncated file -> SHA-256 checksum fails first"
assert_exit_code "20261011" 12 "Manifest EXPECTED_ROWS mismatch with valid SHA-256"
assert_exit_code "20261012" 13 "Renamed column in header (loan_amnt -> principal_amt)"
assert_exit_code "20261013" 0  "Small ~1% payload breach (<5.0% threshold)"
assert_exit_code "20261014" 20 ">8% payload breach (exceeds 5.0% threshold)"
assert_exit_code "20261015" 10 "Missing feed in data/inbound/"

# Verify row-level rejects were written for 20261013 (small breach)
REJECT_FILE_13="${PROJECT_ROOT}/data/rejects/row_level/rejects_20261013.csv"
if [[ -f "${REJECT_FILE_13}" ]]; then
    REJ_LINES=$(( $(wc -l < "${REJECT_FILE_13}") - 1 ))
    if [[ "${REJ_LINES}" -ge 100 ]]; then
        echo "[PASS] 20261013 row-level rejects verified: ${REJ_LINES} bad rows written to ${REJECT_FILE_13##*/}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "[FAIL] 20261013 expected >= 100 row-level rejects, found ${REJ_LINES}" >&2
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
else
    echo "[FAIL] 20261013 reject file ${REJECT_FILE_13} not found" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Remove test batch_date=20261013 parquet folder so clean_parquet holds only production batches
rm -rf "${PROJECT_ROOT}/data/archive/clean_parquet/batch_date=20261013"

# Sync all negative-test SLA outcomes to PostgreSQL vendor_feed_sla_log
python3 "${PROJECT_ROOT}/scripts/load_postgres.py" --sync-sla-only >/dev/null 2>&1 || true

echo "=== Summary: ${PASS_COUNT} passed, ${FAIL_COUNT} failed ==="
[[ "${FAIL_COUNT}" -eq 0 ]]
