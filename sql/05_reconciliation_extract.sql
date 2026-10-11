-- Deterministic 2017 vintage reconciliation control totals by credit grade.
-- Used to cross-check PostgreSQL vs PySpark vs SAS Studio (sas/loanwatch_recon.sas).

CREATE OR REPLACE VIEW vw_reconciliation_2017_by_grade AS
SELECT
    grade,
    COUNT(*) AS loan_count,
    ROUND(SUM(loan_amnt), 2) AS sum_loan_amnt,
    ROUND(SUM(funded_amnt), 2) AS sum_funded_amnt,
    ROUND(SUM(out_prncp), 2) AS sum_out_prncp,
    ROUND(AVG(int_rate), 6) AS mean_int_rate_pct,
    ROUND(
        SUM(int_rate * funded_amnt) / NULLIF(SUM(funded_amnt), 0),
        6
    ) AS wac_int_rate_pct,
    SUM(
        CASE WHEN loan_status IN ('Late (31-120 days)', 'Default') THEN 1 ELSE 0 END
    ) AS delinq_30p_count,
    SUM(
        CASE WHEN loan_status IN ('Default', 'Charged Off') THEN 1 ELSE 0 END
    ) AS severe_delinq_count,
    ROUND(
        SUM(CASE WHEN loan_status IN ('Late (31-120 days)', 'Default') THEN 1 ELSE 0 END)::NUMERIC
        * 100.0 / NULLIF(COUNT(*), 0),
        6
    ) AS delinq_30p_rate_pct,
    ROUND(
        SUM(CASE WHEN loan_status IN ('Default', 'Charged Off') THEN 1 ELSE 0 END)::NUMERIC
        * 100.0 / NULLIF(COUNT(*), 0),
        6
    ) AS severe_delinq_rate_pct,
    ROUND(
        SUM(
            CASE
                WHEN loan_status = 'Charged Off'
                THEN GREATEST(funded_amnt - COALESCE(total_rec_prncp, 0), 0)
                ELSE 0
            END
        ),
        2
    ) AS gross_chargeoff_principal,
    ROUND(
        SUM(CASE WHEN loan_status = 'Charged Off' THEN COALESCE(recoveries, 0) ELSE 0 END),
        2
    ) AS total_recoveries
FROM loans_clean
WHERE issue_ym LIKE '2017-%'
GROUP BY grade
ORDER BY grade;
