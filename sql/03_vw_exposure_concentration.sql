-- Exposure by Purpose & State with DENSE_RANK() and state/portfolio share %.
-- Also defines vw_top_concentration_segments for top 25 state x grade x purpose concentrations.

CREATE OR REPLACE VIEW vw_exposure_by_purpose_state AS
WITH state_purpose AS (
    SELECT
        addr_state,
        COALESCE(purpose, 'other') AS purpose,
        COUNT(*) AS loan_count,
        ROUND(SUM(funded_amnt), 2) AS funded_exposure,
        ROUND(SUM(out_prncp), 2) AS current_upb,
        ROUND(AVG(int_rate), 4) AS avg_int_rate_pct,
        ROUND(AVG((fico_range_low + fico_range_high) / 2.0), 1) AS avg_fico,
        ROUND(AVG(dti), 2) AS avg_dti
    FROM loans_clean
    GROUP BY addr_state, COALESCE(purpose, 'other')
)
SELECT
    addr_state,
    purpose,
    loan_count,
    funded_exposure,
    current_upb,
    avg_int_rate_pct,
    avg_fico,
    avg_dti,
    ROUND(
        funded_exposure * 100.0
        / NULLIF(SUM(funded_exposure) OVER (PARTITION BY addr_state), 0),
        2
    ) AS share_of_state_funded_pct,
    ROUND(
        funded_exposure * 100.0
        / NULLIF(SUM(funded_exposure) OVER (), 0),
        4
    ) AS share_of_portfolio_funded_pct,
    DENSE_RANK() OVER (
        PARTITION BY addr_state
        ORDER BY funded_exposure DESC
    ) AS purpose_rank_in_state
FROM state_purpose;

CREATE OR REPLACE VIEW vw_top_concentration_segments AS
WITH seg_agg AS (
    SELECT
        addr_state,
        grade,
        COALESCE(purpose, 'other') AS purpose,
        COUNT(*) AS loan_count,
        ROUND(SUM(funded_amnt), 2) AS funded_exposure,
        ROUND(SUM(out_prncp), 2) AS current_upb,
        ROUND(
            SUM(int_rate * funded_amnt) / NULLIF(SUM(funded_amnt), 0),
            4
        ) AS wac_pct,
        ROUND(
            SUM(CASE WHEN loan_status IN ('Default', 'Charged Off') THEN 1 ELSE 0 END)::NUMERIC
            * 100.0 / NULLIF(COUNT(*), 0),
            4
        ) AS severe_delinq_rate_pct
    FROM loans_clean
    GROUP BY addr_state, grade, COALESCE(purpose, 'other')
),
ranked AS (
    SELECT
        addr_state,
        grade,
        purpose,
        loan_count,
        funded_exposure,
        current_upb,
        wac_pct,
        severe_delinq_rate_pct,
        ROUND(
            funded_exposure * 100.0 / NULLIF(SUM(funded_exposure) OVER (), 0),
            4
        ) AS portfolio_funded_share_pct,
        ROUND(
            SUM(funded_exposure) OVER (
                ORDER BY funded_exposure DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0 / NULLIF(SUM(funded_exposure) OVER (), 0),
            2
        ) AS cumulative_funded_share_pct,
        DENSE_RANK() OVER (ORDER BY funded_exposure DESC) AS portfolio_exposure_rank
    FROM seg_agg
)
SELECT *
FROM ranked
WHERE portfolio_exposure_rank <= 25;
