# Data Quality (DQ) Rules Register

This register governs the 12 automated row- and batch-level validation rules executed by `spark/dq_rules.py` and `spark/dq_job.py` across the 5 banking data quality dimensions.

## 1. Rule Catalog

| Rule ID | Dimension | Rule Name | Target Attributes | Validation Logic | Pass Threshold | Action on Row Failure |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `DQ_CMP_001` | Completeness | Mandatory Contract Keys Non-Null | `id`, `loan_amnt`, `funded_amnt`, `term`, `int_rate`, `grade`, `issue_d`, `loan_status`, `addr_state` | All 9 mandatory contract identifiers and servicing keys must be non-null and non-blank after trimming whitespace. | `99.90%` | Route row to `data/rejects/row_level/` with code `DQ_CMP_001` |
| `DQ_CMP_002` | Completeness | Underwriting Attributes Populated | `annual_inc`, `dti`, `fico_range_low`, `fico_range_high` (+ 30-col audit) | Core borrower underwriting fields must be non-null; job also emits a full 30-column null percentage audit (`null_profile_<batch>.csv`). | `99.50%` | Route row to `data/rejects/row_level/` with code `DQ_CMP_002` |
| `DQ_UNQ_001` | Uniqueness | Numeric & Unique Loan ID (First-Row Retention) | `id` | `id` must match `^[0-9]+$` (rejecting non-numeric summary footer rows) and have `row_number() OVER (PARTITION BY loan_id ORDER BY _row_seq) == 1`. First occurrence is retained; duplicate occurrences are rejected. | `99.95%` | Retain first occurrence; reject extra duplicates & non-numeric footer rows with `DQ_UNQ_001` |
| `DQ_VAL_001` | Validity | Credit Grade & Sub-Grade Domain | `grade`, `sub_grade`, `loan_status` | `grade` in `A..G`, `sub_grade` matches `^[A-G][1-5]$` with matching letter prefix, and normalized `loan_status` is in the 8 valid servicing statuses. | `99.90%` | Route row to `data/rejects/row_level/` with code `DQ_VAL_001` |
| `DQ_VAL_002` | Validity | US State Jurisdiction Code | `addr_state` | `addr_state` must be one of the 50 US state postal codes or `DC`. | `99.90%` | Route row to `data/rejects/row_level/` with code `DQ_VAL_002` |
| `DQ_VAL_003` | Validity | Rate, DTI `[0,100]` & Non-Negative Income Bounds | `int_rate`, `dti`, `annual_inc` | `int_rate` in `[5.0, 36.0]`, `dti` in `[0.0, 100.0]`, and `annual_inc >= 0`. Real LendingClub rows with `dti < 0` or `dti > 100` are strictly flagged and rejected rather than masked. | `99.00%` | Route row to `data/rejects/row_level/` with code `DQ_VAL_003` |
| `DQ_VAL_004` | Validity | Loan Amount & Term Bounds | `loan_amnt`, `term` | `loan_amnt` in `[$500, $40,000]` and parsed `term_months` in `{36, 60}`. | `99.90%` | Route row to `data/rejects/row_level/` with code `DQ_VAL_004` |
| `DQ_VAL_005` | Validity | Issue Date Format & Vintage Range | `issue_d` | `issue_d` parses cleanly via `MMM-yyyy` within `2007-01-01` through `2018-12-31`. | `99.90%` | Route row to `data/rejects/row_level/` with code `DQ_VAL_005` |
| `DQ_VAL_006` | Validity | FICO Score Range Bounds | `fico_range_low`, `fico_range_high` | Both `fico_range_low` and `fico_range_high` lie within `[300, 850]`. | `99.90%` | Route row to `data/rejects/row_level/` with code `DQ_VAL_006` |
| `DQ_CNS_001` | Consistency | Funded Amount <= Approved Loan Amount | `loan_amnt`, `funded_amnt`, `funded_amnt_inv` | `0 < funded_amnt <= loan_amnt` and `funded_amnt_inv <= funded_amnt` (within `$0.01` rounding tolerance). | `99.95%` | Route row to `data/rejects/row_level/` with code `DQ_CNS_001` |
| `DQ_CNS_002` | Consistency | UPB <= Funded, FICO Order & Terminal Status UPB | `out_prncp`, `funded_amnt`, `fico_range_low`, `fico_range_high`, `loan_status` | `0 <= out_prncp <= funded_amnt`, `fico_range_high >= fico_range_low`, and `out_prncp == 0` whenever normalized `loan_status` is `'Fully Paid'` or `'Charged Off'`. | `99.90%` | Route row to `data/rejects/row_level/` with code `DQ_CNS_002` |
| `DQ_TIM_001` | Timeliness | Payment Chronology & Feed SLA Timeliness | `last_pymnt_d`, `issue_d`, Batch Arrival Timestamp | When `last_pymnt_d` is populated, `last_pymnt_date >= issue_date`; batch arrival time is evaluated against the `06:30 IST` SLA cutoff. | `99.90%` | Reject chronological inversions; flag batch scorecard as `WARN_LATE_FEED` if arrival > `06:30 IST` |

---

## 2. Pre-Rule Normalization Policy
Before evaluating the 12 rules above, `normalize_feed_df()` performs three deterministic normalizations:
1. **Whitespace & Formatting Suffixes**: Trims leading/trailing spaces, strips `%` from `int_rate` and `revol_util`, and extracts integer months (`36` or `60`) from `term` (`" 36 months"`).
2. **Legacy Credit-Policy Status Mapping**: Maps legacy LendingClub statuses `"Does not meet the credit policy. Status:Fully Paid"` to `"Fully Paid"` and `"Does not meet the credit policy. Status:Charged Off"` to `"Charged Off"`, while preserving the original string in `raw_loan_status`.
3. **Multi-Rule Failure Tagging**: A single record failing multiple rules has all applicable `rule_id` codes concatenated with `|` in `reject_reason_codes` (e.g., `DQ_VAL_002|DQ_VAL_003`).
