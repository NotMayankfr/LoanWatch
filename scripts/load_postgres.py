#!/usr/bin/env python3
"""
Idempotent PostgreSQL loader (scripts/load_postgres.py).

Loads clean Parquet partitions for a batch into loans_clean using
a staging table + DELETE batch + INSERT ... ON CONFLICT (loan_id) DO UPDATE,
and syncs DQ scorecards, 30-column null profiles, and vendor SLA logs.
"""

import argparse
import csv
import io
import os
import sys
from pathlib import Path
import pandas as pd
import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOAN_TABLE_COLS = [
    "loan_id",
    "loan_amnt",
    "funded_amnt",
    "funded_amnt_inv",
    "term_months",
    "int_rate",
    "installment",
    "grade",
    "sub_grade",
    "emp_length",
    "home_ownership",
    "annual_inc",
    "verification_status",
    "issue_d",
    "issue_date",
    "issue_ym",
    "loan_status",
    "raw_loan_status",
    "purpose",
    "addr_state",
    "dti",
    "delinq_2yrs",
    "fico_range_low",
    "fico_range_high",
    "revol_bal",
    "revol_util",
    "total_acc",
    "out_prncp",
    "total_pymnt",
    "total_rec_prncp",
    "total_rec_late_fee",
    "recoveries",
    "last_pymnt_d",
    "last_pymnt_date",
    "batch_date",
]


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "127.0.0.1"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "loanwatch"),
        user=os.environ.get("PGUSER", "loanwatch_app"),
        password=os.environ.get("PGPASSWORD", "loanwatch_pass"),
    )


def ensure_ddl_and_views(conn) -> None:
    sql_dir = PROJECT_ROOT / "sql"
    sql_files = sorted(sql_dir.glob("*.sql"))
    with conn.cursor() as cur:
        for sf in sql_files:
            cur.execute(sf.read_text(encoding="utf-8"))
    conn.commit()


def load_clean_parquet_batch(conn, batch_date: str) -> int:
    batch_dir = PROJECT_ROOT / "data" / "archive" / "clean_parquet" / f"batch_date={batch_date}"
    if not batch_dir.exists():
        print(f"[load_postgres] No clean Parquet directory for batch {batch_date}; skipping loan load.")
        return 0

    df = pd.read_parquet(batch_dir)
    if df.empty:
        return 0

    df["batch_date"] = batch_date
    df["issue_ym"] = df["issue_ym"].astype(str)

    # Deduplicate by loan_id within dataframe if needed (retaining first)
    df = df.drop_duplicates(subset=["loan_id"], keep="first")

    int_cols = ["loan_id", "term_months", "delinq_2yrs", "fico_range_low", "fico_range_high", "total_acc"]
    for ic in int_cols:
        if ic in df.columns:
            df[ic] = pd.to_numeric(df[ic], errors="coerce").astype("Int64")

    df = df[LOAN_TABLE_COLS]

    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)

    col_list_sql = ", ".join(LOAN_TABLE_COLS)
    update_set_sql = ", ".join(
        [f"{c} = EXCLUDED.{c}" for c in LOAN_TABLE_COLS if c != "loan_id"]
        + ["loaded_at = NOW()"]
    )

    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE tmp_loans_stage (LIKE loans_clean INCLUDING DEFAULTS) ON COMMIT DROP;")
        cur.copy_expert(
            f"COPY tmp_loans_stage ({col_list_sql}) FROM STDIN WITH (FORMAT CSV, NULL '')",
            buf,
        )
        # Idempotent batch replacement + conflict upsert across batches
        cur.execute("DELETE FROM loans_clean WHERE batch_date = %s;", (batch_date,))
        cur.execute(
            f"""
            INSERT INTO loans_clean ({col_list_sql})
            SELECT {col_list_sql}
            FROM tmp_loans_stage
            ON CONFLICT (loan_id) DO UPDATE SET
                {update_set_sql};
            """
        )
    conn.commit()
    print(f"[load_postgres] Upserted {len(df):,} clean loans for batch {batch_date}")
    return len(df)


def load_scorecard_and_null_profile(conn, batch_date: str) -> None:
    sc_dir = PROJECT_ROOT / "data" / "archive" / "scorecards"
    sc_file = sc_dir / f"scorecard_{batch_date}.csv"
    np_file = sc_dir / f"null_profile_{batch_date}.csv"

    with conn.cursor() as cur:
        if sc_file.exists():
            cur.execute("DELETE FROM dq_scorecard_history WHERE batch_date = %s;", (batch_date,))
            with open(sc_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cur.execute(
                        """
                        INSERT INTO dq_scorecard_history (
                            batch_date, rule_id, dimension, rule_name,
                            records_checked, records_failed, pass_pct,
                            threshold_pct, rule_status, sla_status, arrival_time_ist
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (batch_date, rule_id) DO UPDATE SET
                            records_checked = EXCLUDED.records_checked,
                            records_failed = EXCLUDED.records_failed,
                            pass_pct = EXCLUDED.pass_pct,
                            rule_status = EXCLUDED.rule_status,
                            sla_status = EXCLUDED.sla_status,
                            arrival_time_ist = EXCLUDED.arrival_time_ist,
                            loaded_at = NOW();
                        """,
                        (
                            row["batch_date"],
                            row["rule_id"],
                            row["dimension"],
                            row["rule_name"],
                            int(row["records_checked"]),
                            int(row["records_failed"]),
                            float(row["pass_pct"]),
                            float(row["threshold_pct"]),
                            row["rule_status"],
                            row["sla_status"],
                            row.get("arrival_time_ist", ""),
                        ),
                    )

        if np_file.exists():
            cur.execute("DELETE FROM dq_column_null_profile WHERE batch_date = %s;", (batch_date,))
            with open(np_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cur.execute(
                        """
                        INSERT INTO dq_column_null_profile (
                            batch_date, column_name, records_checked, null_count, null_pct
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (batch_date, column_name) DO UPDATE SET
                            records_checked = EXCLUDED.records_checked,
                            null_count = EXCLUDED.null_count,
                            null_pct = EXCLUDED.null_pct,
                            loaded_at = NOW();
                        """,
                        (
                            row["batch_date"],
                            row["column_name"],
                            int(row["records_checked"]),
                            int(row["null_count"]),
                            float(row["null_pct"]),
                        ),
                    )
    conn.commit()


def sync_sla_history(conn) -> None:
    sla_file = PROJECT_ROOT / "data" / "archive" / "vendor_sla_history.csv"
    if not sla_file.exists():
        return
    with conn.cursor() as cur, open(sla_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cur.execute(
                """
                INSERT INTO vendor_feed_sla_log (
                    batch_date, vendor_id, feed_file, arrival_time_ist,
                    sla_cutoff_ist, sla_status, expected_rows, actual_rows,
                    clean_rows, rejected_rows, reject_pct, pipeline_status,
                    exit_code, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (batch_date) DO UPDATE SET
                    arrival_time_ist = EXCLUDED.arrival_time_ist,
                    sla_status = EXCLUDED.sla_status,
                    expected_rows = EXCLUDED.expected_rows,
                    actual_rows = EXCLUDED.actual_rows,
                    clean_rows = EXCLUDED.clean_rows,
                    rejected_rows = EXCLUDED.rejected_rows,
                    reject_pct = EXCLUDED.reject_pct,
                    pipeline_status = EXCLUDED.pipeline_status,
                    exit_code = EXCLUDED.exit_code,
                    notes = EXCLUDED.notes,
                    loaded_at = NOW();
                """,
                (
                    row["batch_date"],
                    row["vendor_id"],
                    row["feed_file"],
                    row["arrival_time_ist"],
                    row["sla_cutoff_ist"],
                    row["sla_status"],
                    int(row["expected_rows"] or 0),
                    int(row["actual_rows"] or 0),
                    int(row["clean_rows"] or 0),
                    int(row["rejected_rows"] or 0),
                    float(row["reject_pct"] or 0.0),
                    row["pipeline_status"],
                    int(row["exit_code"] or 0),
                    row.get("notes", ""),
                ),
            )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Load clean batch data and metadata into PostgreSQL.")
    parser.add_argument("--batch-date", help="Specific batch date YYYYMMDD to load")
    parser.add_argument("--sync-sla-only", action="store_true", help="Only sync vendor_sla_history.csv")
    args = parser.parse_args()

    conn = get_conn()
    try:
        ensure_ddl_and_views(conn)
        sync_sla_history(conn)
        if args.sync_sla_only:
            return 0
        if args.batch_date:
            load_clean_parquet_batch(conn, args.batch_date)
            load_scorecard_and_null_profile(conn, args.batch_date)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
