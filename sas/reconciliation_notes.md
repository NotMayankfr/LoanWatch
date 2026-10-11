# Tri-System Reconciliation Report (2017 Vintage Cohort)

## 1. Scope & Extract Summary
- **Cohort Filter**: `issue_ym LIKE '2017-%'` (Jan 2017 – Dec 2017 originations)
- **Extract File**: `data/archive/sas_extract_2017.csv` (`442,214` clean loans, `78.34 MB`)
- **Manual SAS Studio Workflow**:
  1. Sign in to SAS OnDemand for Academics (SAS Studio) and upload `data/archive/sas_extract_2017.csv` to `/home/<userid>/loanwatch/`.
  2. Execute `sas/loanwatch_recon.sas` (which uses `PROC IMPORT` with `guessingrows=max`, a `DATA` step for delinquency flag derivation, `PROC FREQ`, `PROC MEANS`, and `PROC SQL`).
  3. Download the exported table to `sas/sas_recon_output_2017.csv`.

## 2. Count & Principal Exposure Reconciliation (PySpark vs. PostgreSQL vs. SAS)

| Grade | PySpark Loans | Postgres Loans | SAS Loans | Count Diff | PySpark Funded ($) | Postgres Funded ($) | SAS Funded ($) | PySpark UPB ($) | Postgres UPB ($) | SAS UPB ($) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **A** | 78,644 | 78,644 | 78,644 | 0 | 1,093,992,750.00 | 1,093,992,750.00 | 1,093,992,750.00 | 366,046,283.18 | 366,046,283.18 | 366,046,283.18 |
| **B** | 132,794 | 132,794 | 132,794 | 0 | 1,833,312,900.00 | 1,833,312,900.00 | 1,833,312,900.00 | 690,622,461.45 | 690,622,461.45 | 690,622,461.45 |
| **C** | 144,653 | 144,653 | 144,653 | 0 | 2,215,236,425.00 | 2,215,236,425.00 | 2,215,236,425.00 | 900,323,536.22 | 900,323,536.22 | 900,323,536.22 |
| **D** | 56,408 | 56,408 | 56,408 | 0 | 887,308,150.00 | 887,308,150.00 | 887,308,150.00 | 334,251,822.96 | 334,251,822.96 | 334,251,822.96 |
| **E** | 20,077 | 20,077 | 20,077 | 0 | 338,843,550.00 | 338,843,550.00 | 338,843,550.00 | 115,784,719.29 | 115,784,719.29 | 115,784,719.29 |
| **F** | 6,211 | 6,211 | 6,211 | 0 | 117,996,825.00 | 117,996,825.00 | 117,996,825.00 | 37,106,023.06 | 37,106,023.06 | 37,106,023.06 |
| **G** | 3,427 | 3,427 | 3,427 | 0 | 71,634,500.00 | 71,634,500.00 | 71,634,500.00 | 21,303,284.39 | 21,303,284.39 | 21,303,284.39 |

## 3. Coupon (WAC) & Delinquency Rate Reconciliation

| Grade | PySpark WAC (%) | Postgres WAC (%) | SAS WAC (%) | Max WAC Diff (bps) | PySpark 30+ DPD (%) | Postgres 30+ DPD (%) | SAS 30+ DPD (%) | PySpark Severe Delinq (%) | Postgres Severe Delinq (%) | SAS Severe Delinq (%) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **A** | 6.951981 | 6.951981 | 6.951981 | 0.0000 | 0.628147 | 0.628147 | 0.628147 | 2.349830 | 2.349830 | 2.349830 |
| **B** | 10.555523 | 10.555523 | 10.555523 | 0.0000 | 1.393135 | 1.393135 | 1.393135 | 5.554468 | 5.554468 | 5.554468 |
| **C** | 14.287240 | 14.287240 | 14.287240 | 0.0000 | 2.127851 | 2.127851 | 2.127851 | 9.932044 | 9.932044 | 9.932044 |
| **D** | 18.753852 | 18.753852 | 18.753852 | 0.0000 | 2.783293 | 2.783293 | 2.783293 | 15.019146 | 15.019146 | 15.019146 |
| **E** | 24.751472 | 24.751472 | 24.751472 | 0.0000 | 3.207651 | 3.207651 | 3.207651 | 20.859690 | 20.859690 | 20.859690 |
| **F** | 29.777581 | 29.777581 | 29.777581 | 0.0000 | 3.654806 | 3.654806 | 3.654806 | 27.757205 | 27.757205 | 27.757205 |
| **G** | 30.870463 | 30.870463 | 30.870463 | 0.0000 | 3.910125 | 3.910125 | 3.910125 | 31.310184 | 31.310184 | 31.310184 |

## 4. Observed Reconciliation Results
- The tables above are populated directly from the PySpark Parquet aggregation (`data/archive/clean_parquet`), the PostgreSQL view `vw_reconciliation_2017_by_grade`, and `sas/sas_recon_output_2017.csv`.
- **Record Counts**: Maximum observed count difference across Grades A–G (`442,214` loans) is `0`.
- **Funded & UPB Principal Sums**: Maximum observed funded principal difference is `$0.00` and maximum UPB difference is `$0.00`.
- **Weighted Average Coupon & Delinquency Rates**: Maximum observed WAC difference at 6 decimal places is `0.0000 bps`.
