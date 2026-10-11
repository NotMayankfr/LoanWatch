# LoanWatch Data Dictionary (30 Canonical Columns)

This dictionary defines the 30 canonical columns extracted from the LendingClub accepted-loans tape (`accepted_2007_to_2018Q4.csv`), their physical types in PySpark and PostgreSQL, and their banking MIS definitions.

| # | Column Name | Raw CSV Example | PySpark Type (Clean) | PostgreSQL Type | Banking / Consumer Credit MIS Definition |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `id` (`loan_id`) | `"68407277"` | `LongType` | `BIGINT PRIMARY KEY` | Unique loan contract identifier assigned at origination. Non-numeric footer rows are rejected by `DQ_UNQ_001`. |
| 2 | `loan_amnt` | `"3600.0"` | `DoubleType` | `NUMERIC(14,2)` | Approved/requested gross loan principal amount ($500–$40,000). |
| 3 | `funded_amnt` | `"3600.0"` | `DoubleType` | `NUMERIC(14,2)` | Total principal amount committed/funded at origination (`funded_amnt <= loan_amnt`). |
| 4 | `funded_amnt_inv` | `"3600.0"` | `DoubleType` | `NUMERIC(14,2)` | Portion of funded principal backed by institutional/retail investors (`<= funded_amnt`). |
| 5 | `term` (`term_months`) | `" 36 months"` | `IntegerType` | `INTEGER` | Contractual amortization term in months (`36` or `60`). |
| 6 | `int_rate` | `"13.99"` | `DoubleType` | `NUMERIC(8,4)` | Contractual nominal annual interest rate (coupon %) on the loan. Used to compute portfolio WAC. |
| 7 | `installment` | `"123.03"` | `DoubleType` | `NUMERIC(12,2)` | Scheduled monthly principal and interest payment owed by the borrower. |
| 8 | `grade` | `"C"` | `StringType` | `VARCHAR(4)` | Internal credit risk grade assigned at underwriting (`A` highest quality through `G` highest risk). |
| 9 | `sub_grade` | `"C4"` | `StringType` | `VARCHAR(6)` | Granular credit risk notch within grade (`A1`–`G5`). |
| 10 | `emp_length` | `"10+ years"` | `StringType` | `VARCHAR(32)` | Borrower self-reported employment tenure (`< 1 year` to `10+ years`). |
| 11 | `home_ownership` | `"MORTGAGE"` | `StringType` | `VARCHAR(32)` | Borrower housing tenure status (`MORTGAGE`, `RENT`, `OWN`, `ANY`, `OTHER`, `NONE`). |
| 12 | `annual_inc` | `"55000.0"` | `DoubleType` | `NUMERIC(16,2)` | Borrower self-reported or verified gross annual income in USD. |
| 13 | `verification_status` | `"Not Verified"` | `StringType` | `VARCHAR(32)` | Income verification status (`Verified`, `Source Verified`, `Not Verified`). |
| 14 | `issue_d` | `"Dec-2015"` | `StringType` | `VARCHAR(16)` | Month and year the loan was funded (`MMM-yyyy`). Derived into `issue_date` (`DATE`) and `issue_ym` (`YYYY-MM`). |
| 15 | `loan_status` | `"Fully Paid"` | `StringType` | `VARCHAR(40)` | Current servicing status. Legacy `"Does not meet the credit policy. Status:<X>"` strings are mapped to `<X>`, while `raw_loan_status` retains the original string. |
| 16 | `purpose` | `"debt_consolidation"` | `StringType` | `VARCHAR(64)` | Borrower stated purpose for the loan (`debt_consolidation`, `credit_card`, `home_improvement`, etc.). |
| 17 | `addr_state` | `"PA"` | `StringType` | `VARCHAR(4)` | Two-letter US state/DC postal code of borrower residence. |
| 18 | `dti` | `"5.91"` | `DoubleType` | `NUMERIC(10,4)` | Debt-to-Income ratio (%) excluding mortgage. Validated against `[0.0, 100.0]` by `DQ_VAL_003`. |
| 19 | `delinq_2yrs` | `"0.0"` | `IntegerType` | `INTEGER` | Number of 30+ DPD delinquency incidences on the borrower's credit file in the past 24 months. |
| 20 | `fico_range_low` | `"675.0"` | `IntegerType` | `INTEGER` | Lower bound of borrower's FICO score range at origination (`300`–`850`). |
| 21 | `fico_range_high` | `"679.0"` | `IntegerType` | `INTEGER` | Upper bound of borrower's FICO score range at origination (`>= fico_range_low`). |
| 22 | `revol_bal` | `"2765.0"` | `DoubleType` | `NUMERIC(16,2)` | Total credit revolving balance across all trade lines at origination. |
| 23 | `revol_util` | `"29.7"` | `DoubleType` | `NUMERIC(8,4)` | Revolving line utilization rate (% of available revolving credit used). |
| 24 | `total_acc` | `"13.0"` | `IntegerType` | `INTEGER` | Total number of credit lines ever opened in the borrower's credit file. |
| 25 | `out_prncp` | `"0.0"` | `DoubleType` | `NUMERIC(14,2)` | Remaining Unpaid Principal Balance (**UPB**). Must be `0.00` for `'Fully Paid'` and `'Charged Off'` loans. |
| 26 | `total_pymnt` | `"4421.72"` | `DoubleType` | `NUMERIC(16,2)` | Cumulative payments (principal + interest + fees + recoveries) received to date. |
| 27 | `total_rec_prncp` | `"3600.0"` | `DoubleType` | `NUMERIC(14,2)` | Cumulative scheduled and unscheduled principal received to date. |
| 28 | `total_rec_late_fee` | `"0.0"` | `DoubleType` | `NUMERIC(12,2)` | Cumulative late fees collected to date. |
| 29 | `recoveries` | `"0.0"` | `DoubleType` | `NUMERIC(14,2)` | Post-charge-off gross recoveries collected. Subtracted from charged-off principal to compute Net Credit Loss (NCL). |
| 30 | `last_pymnt_d` | `"Jan-2019"` | `StringType` | `VARCHAR(16)` | Month and year the most recent borrower payment was received (`MMM-yyyy`). |

---

## Derived Analytical Fields (PostgreSQL & SAS)
- **`is_delinq_30p` (30+ DPD)**: `1` when `loan_status IN ('Late (31-120 days)', 'Default')`, else `0`.
- **`is_severe_delinq` (Severe Delinquency Proxy)**: `1` when `loan_status IN ('Default', 'Charged Off')`, else `0`.
- **`gross_chargeoff_principal`**: `GREATEST(funded_amnt - COALESCE(total_rec_prncp, 0), 0)` when `loan_status = 'Charged Off'`, else `0`.
- **`net_credit_loss` (NCL)**: `gross_chargeoff_principal - post_co_recoveries`.
- **`wac_pct` (Weighted Average Coupon)**: `SUM(int_rate * funded_amnt) / SUM(funded_amnt)`.
