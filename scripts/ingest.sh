#!/usr/bin/env bash
# Gatekeeper shell script for daily vendor loan tape ingestion.
# Exit codes:
#   0  - Feed ingested cleanly (or row-level rejects within 5.0% threshold)
#   4  - Lock contention (overlapping run blocked via flock)
#   10 - Missing feed or manifest file in data/inbound/
#   11 - SHA-256 checksum mismatch (includes truncated transfers)
#   12 - Manifest EXPECTED_ROWS mismatch (with valid SHA-256)
#   13 - Header column count or column name mismatch against 30-column contract
#   20 - PySpark DQ reject rate exceeded MAX_REJECT_PCT (5.0%)

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=../config/pipeline.env
source "${PROJECT_ROOT}/config/pipeline.env"

if [[ -f "${PROJECT_ROOT}/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.venv/bin/activate"
fi

BATCH_DATE=""
SKIP_DOWNSTREAM=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --batch-date)
            BATCH_DATE="$2"
            shift 2
            ;;
        --skip-downstream)
            SKIP_DOWNSTREAM=1
            shift 1
            ;;
        *)
            echo "Usage: $0 --batch-date YYYYMMDD [--skip-downstream]" >&2
            exit 2
            ;;
    esac
done

if [[ -z "${BATCH_DATE}" ]]; then
    echo "ERROR: --batch-date YYYYMMDD is required." >&2
    exit 2
fi

LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}" \
         "${PROJECT_ROOT}/data/inbound" \
         "${PROJECT_ROOT}/data/processing" \
         "${PROJECT_ROOT}/data/archive/raw" \
         "${PROJECT_ROOT}/data/archive/scorecards" \
         "${PROJECT_ROOT}/data/rejects/file_level" \
         "${PROJECT_ROOT}/data/rejects/row_level" \
         "${PROJECT_ROOT}/reports/alerts"

LOG_FILE="${LOG_DIR}/ingest_${BATCH_DATE}.log"
SLA_HISTORY="${PROJECT_ROOT}/data/archive/vendor_sla_history.csv"

if [[ ! -f "${SLA_HISTORY}" ]]; then
    echo "batch_date,vendor_id,feed_file,arrival_time_ist,sla_cutoff_ist,sla_status,expected_rows,actual_rows,clean_rows,rejected_rows,reject_pct,pipeline_status,exit_code,notes" > "${SLA_HISTORY}"
fi

log() {
    local level="$1"
    shift
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S %Z')
    echo "[${ts}] [${level}] [batch=${BATCH_DATE}] $*" | tee -a "${LOG_FILE}"
}

record_sla_row() {
    local feed_file="$1"
    local arrival_ist="$2"
    local sla_status="$3"
    local exp_rows="$4"
    local act_rows="$5"
    local clean_rows="$6"
    local rej_rows="$7"
    local rej_pct="$8"
    local pipe_status="$9"
    local code="${10}"
    local note="${11}"

    # Remove any prior entry for the same batch_date to keep SLA log idempotent
    if grep -q "^${BATCH_DATE}," "${SLA_HISTORY}" 2>/dev/null; then
        grep -v "^${BATCH_DATE}," "${SLA_HISTORY}" > "${SLA_HISTORY}.tmp"
        mv "${SLA_HISTORY}.tmp" "${SLA_HISTORY}"
    fi
    echo "${BATCH_DATE},${VENDOR_NAME},${feed_file},${arrival_ist},${SLA_CUTOFF_HHMM},${sla_status},${exp_rows},${act_rows},${clean_rows},${rej_rows},${rej_pct},${pipe_status},${code},${note}" >> "${SLA_HISTORY}"
}

write_alert() {
    local code="$1"
    local category="$2"
    local detail="$3"
    local alert_file="${PROJECT_ROOT}/reports/alerts/alert_${BATCH_DATE}_${category}.txt"

    cat > "${alert_file}" <<EOF
========================================================================
LOANWATCH PIPELINE INCIDENT ALERT
========================================================================
Timestamp (IST) : $(date '+%Y-%m-%d %H:%M:%S %Z')
Batch Date      : ${BATCH_DATE}
Vendor          : ${VENDOR_NAME}
Incident Type   : ${category}
Exit Code       : ${code}
Details         : ${detail}
Action Required : Consult docs/RUNBOOK.md for L1/L2 remediation steps.
========================================================================
EOF
    log "ALERT" "Wrote incident summary to ${alert_file}"
}

# Acquire exclusive non-blocking lock on FD 200
exec 200>"${LOCK_FILE}"
if ! flock -n 200; then
    log "ERROR" "Another ingest.sh process holds ${LOCK_FILE}. Aborting with exit 4."
    exit 4
fi

FEED_BASENAME="loan_tape_${BATCH_DATE}.csv"
MANIFEST_BASENAME="loan_tape_${BATCH_DATE}.manifest"
INBOUND_CSV="${PROJECT_ROOT}/data/inbound/${FEED_BASENAME}"
INBOUND_MAN="${PROJECT_ROOT}/data/inbound/${MANIFEST_BASENAME}"

log "INFO" "Starting ingestion gatekeeper for ${FEED_BASENAME}"

# 1. Check arrival in data/inbound/
if [[ ! -f "${INBOUND_CSV}" || ! -f "${INBOUND_MAN}" ]]; then
    log "ERROR" "Missing feed or manifest in data/inbound/ for batch ${BATCH_DATE}"
    record_sla_row "${FEED_BASENAME}" "N/A" "MISSING" 0 0 0 0 "0.00" "REJECTED_MISSING" 10 "Feed or manifest not present by cutoff"
    write_alert 10 "MISSING_FEED" "Expected ${FEED_BASENAME} and ${MANIFEST_BASENAME} in data/inbound/, but file was absent."
    exit 10
fi

# Evaluate file arrival mtime in IST (TZ=Asia/Kolkata sourced from pipeline.env)
MTIME_EPOCH=$(stat -c '%Y' "${INBOUND_CSV}")
ARRIVAL_HHMM=$(date -d "@${MTIME_EPOCH}" '+%H:%M')
ARRIVAL_FULL=$(date -d "@${MTIME_EPOCH}" '+%Y-%m-%d %H:%M:%S %Z')

if [[ "${ARRIVAL_HHMM}" > "${SLA_CUTOFF_HHMM}" ]]; then
    SLA_STATUS="LATE"
    log "WARN" "Feed arrived LATE at ${ARRIVAL_FULL} (SLA cutoff ${SLA_CUTOFF_HHMM} IST)"
else
    SLA_STATUS="ON_TIME"
    log "INFO" "Feed arrived ON_TIME at ${ARRIVAL_FULL} (SLA cutoff ${SLA_CUTOFF_HHMM} IST)"
fi

# 2. Move from inbound to processing
PROC_CSV="${PROJECT_ROOT}/data/processing/${FEED_BASENAME}"
PROC_MAN="${PROJECT_ROOT}/data/processing/${MANIFEST_BASENAME}"
mv "${INBOUND_CSV}" "${PROC_CSV}"
mv "${INBOUND_MAN}" "${PROC_MAN}"

MANIFEST_SHA=$(grep '^SHA256=' "${PROC_MAN}" | cut -d'=' -f2 | tr -d '\r ')
MANIFEST_ROWS=$(grep '^EXPECTED_ROWS=' "${PROC_MAN}" | cut -d'=' -f2 | tr -d '\r ')

# 3. Verify SHA-256 Checksum (Truncated files fail here first -> Exit 11)
ACTUAL_SHA=$(sha256sum "${PROC_CSV}" | awk '{print $1}')
ACTUAL_ROWS=$(( $(wc -l < "${PROC_CSV}") - 1 ))

if [[ "${ACTUAL_SHA}" != "${MANIFEST_SHA}" ]]; then
    log "ERROR" "SHA-256 mismatch: manifest=${MANIFEST_SHA} actual=${ACTUAL_SHA} (actual_rows=${ACTUAL_ROWS}, expected_rows=${MANIFEST_ROWS})"
    mv "${PROC_CSV}" "${PROJECT_ROOT}/data/rejects/file_level/${FEED_BASENAME}"
    mv "${PROC_MAN}" "${PROJECT_ROOT}/data/rejects/file_level/${MANIFEST_BASENAME}"
    record_sla_row "${FEED_BASENAME}" "${ARRIVAL_HHMM}" "${SLA_STATUS}" "${MANIFEST_ROWS}" "${ACTUAL_ROWS}" 0 "${ACTUAL_ROWS}" "100.00" "REJECTED_CHECKSUM" 11 "SHA256 mismatch (manifest ${MANIFEST_SHA:0:12} vs actual ${ACTUAL_SHA:0:12})"
    write_alert 11 "CHECKSUM_MISMATCH" "SHA-256 verification failed for ${FEED_BASENAME}. Expected ${MANIFEST_SHA}, got ${ACTUAL_SHA} (rows=${ACTUAL_ROWS} vs manifest=${MANIFEST_ROWS})."
    exit 11
fi
log "INFO" "SHA-256 checksum verified (${ACTUAL_SHA:0:16}...)"

# 4. Verify Row Count against Manifest (Exit 12 when checksum is valid but row count differs)
if [[ "${ACTUAL_ROWS}" -ne "${MANIFEST_ROWS}" ]]; then
    log "ERROR" "Row count mismatch: manifest EXPECTED_ROWS=${MANIFEST_ROWS}, actual wc -l data rows=${ACTUAL_ROWS}"
    mv "${PROC_CSV}" "${PROJECT_ROOT}/data/rejects/file_level/${FEED_BASENAME}"
    mv "${PROC_MAN}" "${PROJECT_ROOT}/data/rejects/file_level/${MANIFEST_BASENAME}"
    record_sla_row "${FEED_BASENAME}" "${ARRIVAL_HHMM}" "${SLA_STATUS}" "${MANIFEST_ROWS}" "${ACTUAL_ROWS}" 0 "${ACTUAL_ROWS}" "100.00" "REJECTED_ROWCOUNT" 12 "Manifest declared ${MANIFEST_ROWS} rows but file contains ${ACTUAL_ROWS}"
    write_alert 12 "ROWCOUNT_MISMATCH" "Manifest row count (${MANIFEST_ROWS}) does not match actual data row count (${ACTUAL_ROWS})."
    exit 12
fi
log "INFO" "Row count verified against manifest (${ACTUAL_ROWS} rows)"

# 5. Validate Header & Column Count with head, awk, and cut (Exit 13)
EXPECTED_HEADER=$(head -n 1 "${PROJECT_ROOT}/config/expected_columns.txt" | tr -d '\r')
ACTUAL_HEADER=$(head -n 1 "${PROC_CSV}" | tr -d '\r')
ACTUAL_COL_COUNT=$(echo "${ACTUAL_HEADER}" | awk -F',' '{print NF}')
FIRST_30_COLS=$(echo "${ACTUAL_HEADER}" | cut -d',' -f1-30)

if [[ "${ACTUAL_COL_COUNT}" -ne "${EXPECTED_COL_COUNT}" || "${FIRST_30_COLS}" != "${EXPECTED_HEADER}" ]]; then
    log "ERROR" "Header validation failed: cols=${ACTUAL_COL_COUNT} (expected ${EXPECTED_COL_COUNT})"
    mv "${PROC_CSV}" "${PROJECT_ROOT}/data/rejects/file_level/${FEED_BASENAME}"
    mv "${PROC_MAN}" "${PROJECT_ROOT}/data/rejects/file_level/${MANIFEST_BASENAME}"
    record_sla_row "${FEED_BASENAME}" "${ARRIVAL_HHMM}" "${SLA_STATUS}" "${MANIFEST_ROWS}" "${ACTUAL_ROWS}" 0 "${ACTUAL_ROWS}" "100.00" "REJECTED_HEADER" 13 "Header drift detected against config/expected_columns.txt"
    write_alert 13 "HEADER_DRIFT" "Header mismatch on ${FEED_BASENAME}. Expected 30 canonical columns, got ${ACTUAL_COL_COUNT} columns."
    exit 13
fi
log "INFO" "Header validated (${ACTUAL_COL_COUNT} canonical columns)"

# 6. Run PySpark DQ Engine
SUMMARY_JSON="${PROJECT_ROOT}/data/archive/scorecards/summary_${BATCH_DATE}.json"
set +e
python3 "${PROJECT_ROOT}/spark/dq_job.py" \
    --input "${PROC_CSV}" \
    --batch-date "${BATCH_DATE}" \
    --sla-status "${SLA_STATUS}" \
    --arrival-time "${ARRIVAL_HHMM}" \
    --max-reject-pct "${MAX_REJECT_PCT}" \
    --summary-out "${SUMMARY_JSON}" >> "${LOG_FILE}" 2>&1
SPARK_EXIT=$?
set -e

if [[ -f "${SUMMARY_JSON}" ]]; then
    CLEAN_ROWS=$(jq -r '.clean_rows' "${SUMMARY_JSON}")
    REJECTED_ROWS=$(jq -r '.rejected_rows' "${SUMMARY_JSON}")
    REJECT_PCT=$(jq -r '.reject_pct' "${SUMMARY_JSON}")
else
    CLEAN_ROWS=0
    REJECTED_ROWS="${ACTUAL_ROWS}"
    REJECT_PCT="100.00"
fi

if [[ "${SPARK_EXIT}" -eq 20 ]]; then
    log "ERROR" "PySpark DQ breach: reject rate ${REJECT_PCT}% exceeds MAX_REJECT_PCT (${MAX_REJECT_PCT}%)"
    mv "${PROC_CSV}" "${PROJECT_ROOT}/data/rejects/file_level/${FEED_BASENAME}"
    mv "${PROC_MAN}" "${PROJECT_ROOT}/data/rejects/file_level/${MANIFEST_BASENAME}"
    record_sla_row "${FEED_BASENAME}" "${ARRIVAL_HHMM}" "${SLA_STATUS}" "${MANIFEST_ROWS}" "${ACTUAL_ROWS}" "${CLEAN_ROWS}" "${REJECTED_ROWS}" "${REJECT_PCT}" "REJECTED_DQ_THRESHOLD" 20 "DQ reject rate ${REJECT_PCT}% > ${MAX_REJECT_PCT}% threshold"
    write_alert 20 "DQ_THRESHOLD_BREACH" "Batch ${BATCH_DATE} rejected: ${REJECTED_ROWS}/${ACTUAL_ROWS} rows failed DQ (${REJECT_PCT}% > ${MAX_REJECT_PCT}% threshold)."
    exit 20
elif [[ "${SPARK_EXIT}" -ne 0 ]]; then
    log "ERROR" "PySpark job failed unexpectedly with exit code ${SPARK_EXIT}"
    mv "${PROC_CSV}" "${PROJECT_ROOT}/data/rejects/file_level/${FEED_BASENAME}"
    mv "${PROC_MAN}" "${PROJECT_ROOT}/data/rejects/file_level/${MANIFEST_BASENAME}"
    exit "${SPARK_EXIT}"
fi

# Archive raw feed & manifest on pass
mv "${PROC_CSV}" "${PROJECT_ROOT}/data/archive/raw/${FEED_BASENAME}"
mv "${PROC_MAN}" "${PROJECT_ROOT}/data/archive/raw/${MANIFEST_BASENAME}"
record_sla_row "${FEED_BASENAME}" "${ARRIVAL_HHMM}" "${SLA_STATUS}" "${MANIFEST_ROWS}" "${ACTUAL_ROWS}" "${CLEAN_ROWS}" "${REJECTED_ROWS}" "${REJECT_PCT}" "COMPLETED" 0 "Clean=${CLEAN_ROWS}, Rejected=${REJECTED_ROWS} (${REJECT_PCT}%)"
log "INFO" "PySpark DQ completed: clean=${CLEAN_ROWS}, rejected=${REJECTED_ROWS} (${REJECT_PCT}%)"

if [[ "${SKIP_DOWNSTREAM}" -eq 0 ]]; then
    log "INFO" "Loading clean partition & scorecard for batch ${BATCH_DATE} into PostgreSQL..."
    python3 "${PROJECT_ROOT}/scripts/load_postgres.py" --batch-date "${BATCH_DATE}" >> "${LOG_FILE}" 2>&1
    log "INFO" "PostgreSQL load completed for batch ${BATCH_DATE}."
fi

log "INFO" "Batch ${BATCH_DATE} ingestion finished with exit 0."
exit 0
