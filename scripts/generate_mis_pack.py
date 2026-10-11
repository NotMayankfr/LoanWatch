#!/usr/bin/env python3
"""
Daily Excel MIS Pack Generator (scripts/generate_mis_pack.py).

Queries the PostgreSQL analytical views, DQ scorecard tables, vendor SLA log,
and tri-system reconciliation outputs to produce a formatted 5-tab workbook:
  1. Executive_Summary (including real Tri-System Reconciliation table)
  2. DQ_Scorecard (12 rules + 30-column null profile + embedded chart)
  3. Delinquency_Vintage (30+ DPD & severe delinquency proxy + LAG MoM bps)
  4. Exposure_Concentration (Top 25 segments + top state/purpose ranks)
  5. Vendor_SLA_Tracker (All daily & negative-test feed outcomes)
"""

import argparse
import sys
import warnings
from pathlib import Path
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, message=".*pandas only supports SQLAlchemy.*")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.load_postgres import get_conn


def build_mis_pack(batch_date: str, output_xlsx: Path) -> None:
    conn = get_conn()
    try:
        kpi_sql = """
        SELECT
            COUNT(*) AS total_loans,
            ROUND(SUM(funded_amnt), 2) AS total_funded,
            ROUND(SUM(out_prncp), 2) AS total_upb,
            ROUND(SUM(int_rate * funded_amnt) / NULLIF(SUM(funded_amnt), 0), 4) AS wac_pct,
            ROUND(
                SUM(CASE WHEN loan_status IN ('Late (31-120 days)', 'Default') THEN 1 ELSE 0 END)::NUMERIC
                * 100.0 / NULLIF(COUNT(*), 0), 4
            ) AS delinq_30p_rate_pct,
            ROUND(
                SUM(CASE WHEN loan_status IN ('Default', 'Charged Off') THEN 1 ELSE 0 END)::NUMERIC
                * 100.0 / NULLIF(COUNT(*), 0), 4
            ) AS severe_delinq_rate_pct
        FROM loans_clean;
        """
        kpi_df = pd.read_sql_query(kpi_sql, conn)

        grade_summary_sql = """
        SELECT
            grade,
            COUNT(*) AS loan_count,
            ROUND(SUM(funded_amnt), 2) AS funded_amnt,
            ROUND(SUM(out_prncp), 2) AS current_upb,
            ROUND(SUM(int_rate * funded_amnt) / NULLIF(SUM(funded_amnt), 0), 4) AS wac_pct,
            ROUND(AVG((fico_range_low + fico_range_high) / 2.0), 1) AS avg_fico,
            ROUND(AVG(dti), 2) AS avg_dti,
            ROUND(
                SUM(CASE WHEN loan_status IN ('Late (31-120 days)', 'Default') THEN 1 ELSE 0 END)::NUMERIC
                * 100.0 / NULLIF(COUNT(*), 0), 4
            ) AS delinq_30p_rate_pct,
            ROUND(
                SUM(CASE WHEN loan_status IN ('Default', 'Charged Off') THEN 1 ELSE 0 END)::NUMERIC
                * 100.0 / NULLIF(COUNT(*), 0), 4
            ) AS severe_delinq_rate_pct
        FROM loans_clean
        GROUP BY grade
        ORDER BY grade;
        """
        grade_df = pd.read_sql_query(grade_summary_sql, conn)

        pg_recon_df = pd.read_sql_query(
            "SELECT * FROM vw_reconciliation_2017_by_grade ORDER BY grade;", conn
        )

        sc_df = pd.read_sql_query(
            """
            SELECT batch_date, rule_id, dimension, rule_name,
                   records_checked, records_failed, pass_pct,
                   threshold_pct, rule_status, sla_status, arrival_time_ist
            FROM dq_scorecard_history
            WHERE batch_date = %s
            ORDER BY rule_id;
            """,
            conn,
            params=(batch_date,),
        )

        null_df = pd.read_sql_query(
            """
            SELECT batch_date, column_name, records_checked, null_count, null_pct
            FROM dq_column_null_profile
            WHERE batch_date = %s
            ORDER BY null_count DESC, column_name;
            """,
            conn,
            params=(batch_date,),
        )

        delinq_df = pd.read_sql_query(
            """
            SELECT *
            FROM vw_delinquency_by_grade_vintage
            WHERE issue_ym >= '2016-01'
            ORDER BY issue_ym DESC, grade;
            """,
            conn,
        )

        top_conc_df = pd.read_sql_query(
            "SELECT * FROM vw_top_concentration_segments ORDER BY portfolio_exposure_rank;",
            conn,
        )

        state_purpose_df = pd.read_sql_query(
            """
            SELECT *
            FROM vw_exposure_by_purpose_state
            WHERE purpose_rank_in_state <= 3
            ORDER BY funded_exposure DESC
            LIMIT 45;
            """,
            conn,
        )

        sla_df = pd.read_sql_query(
            """
            SELECT batch_date, vendor_id, feed_file, arrival_time_ist,
                   sla_cutoff_ist, sla_status, expected_rows, actual_rows,
                   clean_rows, rejected_rows, reject_pct, pipeline_status,
                   exit_code, notes
            FROM vendor_feed_sla_log
            ORDER BY batch_date;
            """,
            conn,
        )
    finally:
        conn.close()

    sas_csv = PROJECT_ROOT / "sas" / "sas_recon_output_2017.csv"
    if sas_csv.exists() and not pg_recon_df.empty:
        sas_df = pd.read_csv(sas_csv)
        recon_merged = pg_recon_df.merge(
            sas_df, on="grade", suffixes=("_pg", "_sas"), how="left"
        )
        recon_merged["count_variance"] = (
            recon_merged["loan_count_pg"] - recon_merged["loan_count_sas"]
        )
        recon_merged["funded_variance_usd"] = (
            recon_merged["sum_funded_amnt_pg"] - recon_merged["sum_funded_amnt_sas"]
        ).round(2)
        recon_merged["wac_diff_bps"] = (
            (recon_merged["wac_int_rate_pct_pg"] - recon_merged["wac_int_rate_pct_sas"]) * 100.0
        ).round(4)
        recon_table = recon_merged[
            [
                "grade",
                "loan_count_pg",
                "loan_count_sas",
                "count_variance",
                "sum_funded_amnt_pg",
                "sum_funded_amnt_sas",
                "funded_variance_usd",
                "wac_int_rate_pct_pg",
                "wac_int_rate_pct_sas",
                "wac_diff_bps",
                "delinq_30p_rate_pct_pg",
                "delinq_30p_rate_pct_sas",
                "severe_delinq_rate_pct_pg",
                "severe_delinq_rate_pct_sas",
            ]
        ]
    else:
        recon_table = pg_recon_df

    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_xlsx, engine="xlsxwriter") as writer:
        wb = writer.book

        # Institutional banking formatting styles
        title_fmt = wb.add_format(
            {"bold": True, "font_size": 13, "font_color": "#FFFFFF", "bg_color": "#1B365D"}
        )
        sec_fmt = wb.add_format(
            {"bold": True, "font_size": 11, "font_color": "#1B365D", "bottom": 2}
        )
        hdr_fmt = wb.add_format(
            {
                "bold": True,
                "font_size": 10,
                "font_color": "#FFFFFF",
                "bg_color": "#2C5282",
                "border": 1,
            }
        )
        pass_fmt = wb.add_format({"bg_color": "#C6F6D5", "font_color": "#22543D", "bold": True})
        fail_fmt = wb.add_format({"bg_color": "#FED7D7", "font_color": "#742A2A", "bold": True})

        # Tab 1: Executive_Summary
        kpi_df.to_excel(writer, sheet_name="Executive_Summary", startrow=2, index=False)
        grade_df.to_excel(writer, sheet_name="Executive_Summary", startrow=6, index=False)
        recon_start = 6 + len(grade_df) + 3
        recon_table.to_excel(
            writer, sheet_name="Executive_Summary", startrow=recon_start, index=False
        )
        ws_exec = writer.sheets["Executive_Summary"]
        ws_exec.write(0, 0, f"LoanWatch Consumer Credit Portfolio MIS Pack — Batch {batch_date}", title_fmt)
        ws_exec.write(1, 0, "1. Portfolio Headline KPIs", sec_fmt)
        ws_exec.write(5, 0, "2. Credit Grade Distribution & Delinquency Summary", sec_fmt)
        ws_exec.write(
            recon_start - 1,
            0,
            "3. 2017 Cohort Tri-System Reconciliation (PostgreSQL vs SAS Studio)",
            sec_fmt,
        )
        ws_exec.set_column(0, 14, 18)

        # Tab 2: DQ_Scorecard
        sc_df.to_excel(writer, sheet_name="DQ_Scorecard", startrow=2, index=False)
        null_start = 2 + len(sc_df) + 4
        null_df.to_excel(writer, sheet_name="DQ_Scorecard", startrow=null_start, index=False)
        ws_dq = writer.sheets["DQ_Scorecard"]
        ws_dq.write(0, 0, f"Data Quality Scorecard & 30-Column Completeness Profile ({batch_date})", title_fmt)
        ws_dq.write(1, 0, "1. 12-Rule Data Quality Gatekeeper Scorecard", sec_fmt)
        ws_dq.write(null_start - 1, 0, "2. 30-Column Null Percentage Audit", sec_fmt)
        ws_dq.set_column(0, 10, 20)
        ws_dq.set_column(3, 3, 42)

        if not sc_df.empty:
            ws_dq.conditional_format(
                3, 8, 2 + len(sc_df), 8,
                {"type": "cell", "criteria": "equal to", "value": '"PASS"', "format": pass_fmt},
            )
            ws_dq.conditional_format(
                3, 8, 2 + len(sc_df), 8,
                {"type": "cell", "criteria": "not equal to", "value": '"PASS"', "format": fail_fmt},
            )
            chart = wb.add_chart({"type": "column"})
            chart.add_series(
                {
                    "name": "Pass %",
                    "categories": ["DQ_Scorecard", 3, 1, 2 + len(sc_df), 1],
                    "values": ["DQ_Scorecard", 3, 6, 2 + len(sc_df), 6],
                    "fill": {"color": "#2B6CB0"},
                }
            )
            chart.set_title({"name": f"DQ Rule Pass Rate (%) — Batch {batch_date}"})
            chart.set_y_axis({"min": 95, "max": 100})
            chart.set_size({"width": 640, "height": 300})
            ws_dq.insert_chart(2, 12, chart)

        # Tab 3: Delinquency_Vintage
        delinq_df.to_excel(writer, sheet_name="Delinquency_Vintage", startrow=2, index=False)
        ws_del = writer.sheets["Delinquency_Vintage"]
        ws_del.write(
            0, 0,
            "Delinquency (30+ DPD) & Severe Delinquency Proxy by Grade & Vintage (with MoM bps)",
            title_fmt,
        )
        ws_del.set_column(0, 13, 18)
        ws_del.freeze_panes(3, 2)

        # Tab 4: Exposure_Concentration
        top_conc_df.to_excel(writer, sheet_name="Exposure_Concentration", startrow=2, index=False)
        sp_start = 2 + len(top_conc_df) + 4
        state_purpose_df.to_excel(
            writer, sheet_name="Exposure_Concentration", startrow=sp_start, index=False
        )
        ws_exp = writer.sheets["Exposure_Concentration"]
        ws_exp.write(0, 0, "Portfolio Concentration Risk & State/Purpose Exposure Ranking", title_fmt)
        ws_exp.write(1, 0, "1. Top 25 State x Grade x Purpose Concentration Segments", sec_fmt)
        ws_exp.write(sp_start - 1, 0, "2. Top 3 Loan Purposes within Leading States (DENSE_RANK)", sec_fmt)
        ws_exp.set_column(0, 11, 20)

        # Tab 5: Vendor_SLA_Tracker
        sla_df.to_excel(writer, sheet_name="Vendor_SLA_Tracker", startrow=2, index=False)
        ws_sla = writer.sheets["Vendor_SLA_Tracker"]
        ws_sla.write(0, 0, "Vendor Feed Delivery SLA & Gatekeeper Audit Log (06:30 IST Cutoff)", title_fmt)
        ws_sla.set_column(0, 12, 18)
        ws_sla.set_column(13, 13, 48)
        for col_idx, col_name in enumerate(sla_df.columns):
            ws_sla.write(2, col_idx, col_name, hdr_fmt)

    print(f"[generate_mis_pack] Generated Excel MIS Pack: {output_xlsx}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate daily Excel MIS pack.")
    parser.add_argument("--batch-date", default="20261009", help="Reference batch date YYYYMMDD")
    parser.add_argument("--output", help="Optional explicit .xlsx output path")
    args = parser.parse_args()

    out_path = (
        Path(args.output)
        if args.output
        else PROJECT_ROOT / "reports" / f"LoanWatch_MIS_Pack_{args.batch_date}.xlsx"
    )
    build_mis_pack(args.batch_date, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
