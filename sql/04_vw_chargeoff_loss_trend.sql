-- Gross Charge-Offs, Recoveries, Net Credit Loss (NCL), and 3-month rolling average loss rate.

CREATE OR REPLACE VIEW vw_chargeoff_loss_trend AS
WITH monthly_loss AS (
    SELECT
        issue_ym,
        COUNT(*) AS originated_loans,
        ROUND(SUM(funded_amnt), 2) AS originated_funded_amnt,
        SUM(CASE WHEN loan_status = 'Charged Off' THEN 1 ELSE 0 END) AS charged_off_loans,
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
        ) AS post_co_recoveries
    FROM loans_clean
    GROUP BY issue_ym
),
loss_metrics AS (
    SELECT
        issue_ym,
        originated_loans,
        originated_funded_amnt,
        charged_off_loans,
        gross_chargeoff_principal,
        post_co_recoveries,
        ROUND(gross_chargeoff_principal - post_co_recoveries, 2) AS net_credit_loss,
        ROUND(
            charged_off_loans::NUMERIC * 100.0 / NULLIF(originated_loans, 0),
            4
        ) AS chargeoff_unit_rate_pct,
        ROUND(
            (gross_chargeoff_principal - post_co_recoveries) * 100.0
            / NULLIF(originated_funded_amnt, 0),
            4
        ) AS net_loss_rate_pct
    FROM monthly_loss
)
SELECT
    issue_ym,
    originated_loans,
    originated_funded_amnt,
    charged_off_loans,
    gross_chargeoff_principal,
    post_co_recoveries,
    net_credit_loss,
    chargeoff_unit_rate_pct,
    net_loss_rate_pct,
    ROUND(
        AVG(net_loss_rate_pct) OVER (
            ORDER BY issue_ym
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ),
        4
    ) AS rolling_3m_net_loss_rate_pct,
    ROUND(
        (
            net_loss_rate_pct
            - LAG(net_loss_rate_pct, 1) OVER (ORDER BY issue_ym)
        ) * 100.0,
        2
    ) AS mom_net_loss_change_bps
FROM loss_metrics;
