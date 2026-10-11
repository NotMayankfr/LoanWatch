# LoanWatch Operational Runbook (L1 / L2 Production Support)

## 1. Service Overview & SLA Schedule
- **Pipeline Name**: `LoanWatch` — Consumer Credit Portfolio DQ & Daily MIS Pipeline
- **Upstream Vendor**: `FirstMark_Servicing`
- **Delivery Mechanism**: Daily CSV drop (`loan_tape_YYYYMMDD.csv` + `loan_tape_YYYYMMDD.manifest`) into `~/LoanWatch/data/inbound/`
- **SLA Cutoff**: `06:30 IST` (`TZ=Asia/Kolkata` configured in `config/pipeline.env`)
- **Scheduled Cron Trigger**: `06:35 IST` Monday–Friday (`scripts/cron_loanwatch`)
- **Batch Reject Threshold**: `5.0%` (`MAX_REJECT_PCT=5.0`). Feeds with `<= 5.0%` row-level DQ failures promote clean rows and isolate bad rows to `data/rejects/row_level/`. Feeds exceeding `5.0%` halt promotion with exit code `20`.

---

## 2. Exit Code Reference

| Exit Code | Failure Stage | SLA Log Status | Meaning |
| :---: | :--- | :--- | :--- |
| `0` | Complete | `COMPLETED` | Feed ingested; clean Parquet, PostgreSQL tables, and MIS pack updated |
| `4` | Lockfile (`flock`) | *(Unchanged)* | Another `ingest.sh` instance holds `/tmp/loanwatch_ingest.lock` |
| `10` | Arrival Check | `REJECTED_MISSING` | `.csv` or `.manifest` missing from `data/inbound/` at run time |
| `11` | Checksum Check | `REJECTED_CHECKSUM` | `sha256sum` does not match manifest `SHA256` (includes truncated transfers) |
| `12` | Row Count Check | `REJECTED_ROWCOUNT` | Checksum valid, but `wc -l` data rows != manifest `EXPECTED_ROWS` |
| `13` | Header Check | `REJECTED_HEADER` | Column count != 30 or column names differ from `config/expected_columns.txt` |
| `20` | PySpark DQ Gate | `REJECTED_DQ_THRESHOLD` | Row-level DQ failure rate exceeded `5.0%` (`MAX_REJECT_PCT`) |

---

## 3. Incident Triage & Remediation Playbooks

### Scenario 1: Vendor Feed Late or Missing After `06:30 IST` (`Exit 10` or `SLA_STATUS=LATE`)
**Symptoms**:
- `reports/alerts/alert_<YYYYMMDD>_MISSING_FEED.txt` generated at `06:35 IST`, or `vendor_sla_history.csv` shows `sla_status=LATE`.

**Triage Steps**:
1. Check whether the vendor SFTP transfer is still in progress or landed after `06:35 IST`:
   ```bash
   ls -la --time-style=full-iso ~/LoanWatch/data/inbound/
   ```
2. If the file is still absent 15 minutes past the `06:30 IST` SLA (`06:45 IST`), raise a P2 Vendor Feed Escalation ticket quoting the `BATCH_DATE` and `VENDOR_ID=FirstMark_Servicing`.
3. Once the vendor drops both `loan_tape_<YYYYMMDD>.csv` and `loan_tape_<YYYYMMDD>.manifest`, re-trigger ingestion manually:
   ```bash
   cd ~/LoanWatch
   ./scripts/ingest.sh --batch-date <YYYYMMDD>
   ```
   `ingest.sh` will automatically detect the file's mtime (`> 06:30 IST`), record `sla_status=LATE` in `data/archive/vendor_sla_history.csv`, and replace the prior `MISSING` row idempotently.

---

### Scenario 2: Checksum Mismatch (`Exit 11`) or Manifest Row-Count Mismatch (`Exit 12`)
**Symptoms**:
- `ingest.sh` exits with `11` (`CHECKSUM_MISMATCH`) or `12` (`ROWCOUNT_MISMATCH`).
- Offending files are quarantined in `~/LoanWatch/data/rejects/file_level/`.
- Note: **Truncated files fail at the checksum step (`Exit 11`)** because the SHA-256 check runs immediately before the row-count check. `Exit 12` indicates the vendor computed a valid SHA-256 over the file they sent, but wrote an inaccurate `EXPECTED_ROWS` count in the `.manifest`.

**Triage Steps**:
1. Inspect the quarantined file and manifest:
   ```bash
   cd ~/LoanWatch/data/rejects/file_level
   cat loan_tape_<YYYYMMDD>.manifest
   sha256sum loan_tape_<YYYYMMDD>.csv
   echo "Actual data rows: $(( $(wc -l < loan_tape_<YYYYMMDD>.csv) - 1 ))"
   ```
2. **If `Exit 11` (Checksum Mismatch / Truncation)**:
   - Never override the manifest checksum locally. Request a fresh re-transmission from the vendor.
3. **If `Exit 12` (Valid SHA-256, Manifest Row-Count Generation Bug)**:
   - Confirm with the vendor whether the payload is complete and only the manifest counter was miscalculated, or have the vendor re-issue the `.manifest` file.

---

### Scenario 3: Upstream Schema / Header Drift (`Exit 13`)
**Symptoms**:
- `reports/alerts/alert_<YYYYMMDD>_HEADER_DRIFT.txt` emitted; files moved to `data/rejects/file_level/`.

**Triage Steps**:
1. Compare the quarantined header against the 30-column canonical contract:
   ```bash
   diff -u \
     <(head -n 1 ~/LoanWatch/config/expected_columns.txt | tr ',' '\n') \
     <(head -n 1 ~/LoanWatch/data/rejects/file_level/loan_tape_<YYYYMMDD>.csv | tr -d '\r' | tr ',' '\n')
   ```
2. If the vendor renamed a column without prior change-control notice (e.g. `loan_amnt` -> `principal_amt`), reject the drop back to the vendor or, if an emergency schema mapping is approved by Data Governance, apply a pre-ingestion header alias and document the exception.

---

### Scenario 4: PySpark DQ Pass Rate Drops Below 95.0% (`Exit 20`)
**Symptoms**:
- `ingest.sh` exits with `20` (`DQ_THRESHOLD_BREACH`).
- Clean rows are **not** promoted to `data/archive/clean_parquet/` or PostgreSQL.

**Triage Steps**:
1. Inspect the batch DQ scorecard to identify which of the 12 rules drove the spike:
   ```bash
   column -s, -t < ~/LoanWatch/data/archive/scorecards/scorecard_<YYYYMMDD>.csv
   ```
2. Sample the row-level reject file to inspect the exact `reject_reason_codes` combinations:
   ```bash
   cut -d',' -f32 ~/LoanWatch/data/rejects/row_level/rejects_<YYYYMMDD>.csv | sort | uniq -c | sort -nr | head -n 10
   ```
3. Send the top failing `rule_id` summary and a redacted sample of rejected `loan_id`s to the vendor data steward for correction.

---

### Scenario 5: Stale Lockfile Recovery (`Exit 4`)
**Symptoms**:
- `ingest.sh` aborts immediately with `[ERROR] Another ingest.sh process holds /tmp/loanwatch_ingest.lock. Aborting with exit 4.`

**Triage Steps**:
1. Verify whether an active `ingest.sh` or `dq_job.py` process is actually holding the descriptor:
   ```bash
   fuser -v /tmp/loanwatch_ingest.lock || ps aux | grep -E "ingest.sh|dq_job.py"
   ```
2. Because `flock` binds to the open kernel file description (FD 200), a terminated process automatically releases the lock. If a hung Spark JVM child process is still holding FD 200 open after a timeout, terminate the hung PID and remove the lockfile:
   ```bash
   kill -15 <HUNG_PID>
   rm -f /tmp/loanwatch_ingest.lock
   ```
