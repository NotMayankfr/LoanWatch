-- 30+ DPD, severe delinquency (proxy), and WAC by Grade & Vintage with LAG() MoM bps change.
-- Delinquency definitions:
--   is_delinq_30p    : loan_status IN ('Late (31-120 days)', 'Default')
--   is_severe_delinq : loan_status IN ('Default', 'Charged Off')

CREATE OR REPLACE VIEW vw_delinquency_by_grade_vintage AS
WITH base_flags AS (
    SELECT
        issue_ym,
        grade,
        loan_id,
        loan_amnt,
        funded_amnt,
        out_prncp,
        int_rate,
        CASE
            WHEN loan_status IN ('Late (31-120 days)', 'Default') THEN 1
            ELSE 0
        END AS is_delinq_30p,
        CASE
            WHEN loan_status IN ('Default', 'Charged Off') THEN 1
            ELSE 0
        END AS is_severe_delinq
    FROM loans_clean
),
cohort_agg AS (
    SELECT
        issue_ym,
        grade,
        COUNT(*) AS loan_count,
        ROUND(SUM(funded_amnt), 2) AS total_funded_amnt,
        ROUND(SUM(out_prncp), 2) AS total_upb,
        ROUND(
            SUM(int_rate * funded_amnt) / NULLIF(SUM(funded_amnt), 0),
            4
        ) AS wac_pct,
        SUM(is_delinq_30p) AS delinq_30p_loans,
        SUM(is_severe_delinq) AS severe_delinq_loans,
        ROUND(
            SUM(is_delinq_30p)::NUMERIC * 100.0 / NULLIF(COUNT(*), 0),
            4
        ) AS delinq_30p_loan_rate_pct,
        ROUND(
            SUM(CASE WHEN is_delinq_30p = 1 THEN out_prncp ELSE 0 END) * 100.0
            / NULLIF(SUM(out_prncp), 0),
            4
        ) AS delinq_30p_upb_rate_pct,
        ROUND(
            SUM(is_severe_delinq)::NUMERIC * 100.0 / NULLIF(COUNT(*), 0),
            4
        ) AS severe_delinq_rate_pct
    FROM base_flags
    GROUP BY issue_ym, grade
)
SELECT
    issue_ym,
    grade,
    loan_count,
    total_funded_amnt,
    total_upb,
    wac_pct,
    delinq_30p_loans,
    severe_delinq_loans,
    delinq_30p_loan_rate_pct,
    COALESCE(delinq_30p_upb_rate_pct, 0.0000) AS delinq_30p_upb_rate_pct,
    severe_delinq_rate_pct,
    ROUND(
        (
            delinq_30p_loan_rate_pct
            - LAG(delinq_30p_loan_rate_pct, 1) OVER (
                PARTITION BY grade ORDER BY issue_ym
            )
        ) * 100.0,
        2
    ) AS mom_delinq_30p_change_bps,
    ROUND(
        (
            severe_delinq_rate_pct
            - LAG(severe_delinq_rate_pct, 1) OVER (
                PARTITION BY grade ORDER BY issue_ym
            )
        ) * 100.0,
        2
    ) AS mom_severe_delinq_change_bps,
    RANK() OVER (
        PARTITION BY issue_ym
        ORDER BY delinq_30p_loan_rate_pct DESC
    ) AS delinq_rank_in_vintage
FROM cohort_agg;
