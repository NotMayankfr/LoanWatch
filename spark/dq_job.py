#!/usr/bin/env python3
"""
PySpark Data Quality & Normalization Job (spark/dq_job.py).

Enforces the explicit 30-column schema, evaluates 12 rules across
Completeness, Uniqueness, Validity, Consistency, and Timeliness,
writes row-level rejects with pipe-delimited reason codes, writes
the batch DQ scorecard + 30-column null profile, and writes clean
records to Parquet partitioned by issue_ym.
"""

import argparse
import csv
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from spark.dq_rules import DQ_RULE_SPECS, apply_dq_rules, normalize_feed_df
from spark.schema import CANONICAL_COLUMNS, RAW_FEED_SCHEMA


def build_spark_session(app_name: str = "LoanWatch_DQ_Engine") -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .master(os.environ.get("SPARK_MASTER", "local[*]"))
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.driver.memory", "4g")
        .getOrCreate()
    )


def write_single_csv_from_df(df, target_csv: Path) -> int:
    """Writes a filtered reject DataFrame to a single deterministic CSV file."""
    target_csv.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = target_csv.parent / f".tmp_{target_csv.stem}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    df.coalesce(1).write.csv(
        str(tmp_dir),
        header=True,
        mode="overwrite",
        nullValue="",
        emptyValue="",
    )
    part_files = list(tmp_dir.glob("part-*.csv"))
    if part_files:
        shutil.move(str(part_files[0]), str(target_csv))
    shutil.rmtree(tmp_dir, ignore_errors=True)
    if not target_csv.exists():
        return 0
    with open(target_csv, "r", encoding="utf-8") as f:
        return max(0, sum(1 for _ in f) - 1)


def run_dq_job(
    input_csv: Path,
    batch_date: str,
    sla_status: str,
    arrival_time: str,
    max_reject_pct: float,
    summary_out: Path | None,
) -> int:
    spark = build_spark_session(f"LoanWatch_DQ_{batch_date}")
    spark.sparkContext.setLogLevel("WARN")

    raw_df = (
        spark.read.format("csv")
        .option("header", "true")
        .option("mode", "PERMISSIVE")
        .schema(RAW_FEED_SCHEMA)
        .load(str(input_csv))
    )

    norm_df = normalize_feed_df(raw_df, batch_date)
    evaluated_df = apply_dq_rules(norm_df).persist()

    # Single-pass aggregation for total rows, rejected rows, 12 rule counts, and 30 column null counts
    agg_exprs = [
        F.count(F.lit(1)).alias("total_rows"),
        F.sum(F.when(F.col("reject_count") > 0, 1).otherwise(0)).alias("rejected_rows"),
    ]
    for spec in DQ_RULE_SPECS:
        agg_exprs.append(
            F.sum(F.when(~F.col(f"pass_{spec.rule_id}"), 1).otherwise(0)).alias(
                f"fail_{spec.rule_id}"
            )
        )
    for col_name in CANONICAL_COLUMNS:
        agg_exprs.append(
            F.sum(F.when(F.col(col_name).isNull(), 1).otherwise(0)).alias(f"null_{col_name}")
        )

    metrics_row = evaluated_df.agg(*agg_exprs).collect()[0].asDict()
    total_rows = int(metrics_row["total_rows"] or 0)
    rejected_rows = int(metrics_row["rejected_rows"] or 0)
    clean_rows = total_rows - rejected_rows
    reject_pct = round((rejected_rows / total_rows * 100.0), 4) if total_rows > 0 else 0.0

    scorecard_dir = PROJECT_ROOT / "data" / "archive" / "scorecards"
    scorecard_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write 12-rule DQ scorecard
    scorecard_path = scorecard_dir / f"scorecard_{batch_date}.csv"
    with open(scorecard_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "batch_date",
                "rule_id",
                "dimension",
                "rule_name",
                "records_checked",
                "records_failed",
                "pass_pct",
                "threshold_pct",
                "rule_status",
                "sla_status",
                "arrival_time_ist",
            ]
        )
        for spec in DQ_RULE_SPECS:
            failed = int(metrics_row.get(f"fail_{spec.rule_id}") or 0)
            # Timeliness rule incorporates feed arrival SLA status at the batch level
            if spec.rule_id == "DQ_TIM_001" and sla_status != "ON_TIME":
                rule_status = "WARN_LATE_FEED"
            else:
                pass_rate = ((total_rows - failed) / total_rows * 100.0) if total_rows > 0 else 100.0
                rule_status = "PASS" if pass_rate >= spec.threshold_pct else "FAIL"

            pass_pct = round(((total_rows - failed) / total_rows * 100.0), 4) if total_rows > 0 else 100.0
            writer.writerow(
                [
                    batch_date,
                    spec.rule_id,
                    spec.dimension,
                    spec.rule_name,
                    total_rows,
                    failed,
                    f"{pass_pct:.4f}",
                    f"{spec.threshold_pct:.2f}",
                    rule_status,
                    sla_status,
                    arrival_time,
                ]
            )

    # 2. Write 30-column Completeness / Null % profile
    null_profile_path = scorecard_dir / f"null_profile_{batch_date}.csv"
    with open(null_profile_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["batch_date", "column_name", "records_checked", "null_count", "null_pct"])
        for col_name in CANONICAL_COLUMNS:
            ncount = int(metrics_row.get(f"null_{col_name}") or 0)
            npct = round((ncount / total_rows * 100.0), 4) if total_rows > 0 else 0.0
            writer.writerow([batch_date, col_name, total_rows, ncount, f"{npct:.4f}"])

    # 3. Write failing rows to data/rejects/row_level/rejects_<batch_date>.csv
    reject_cols = CANONICAL_COLUMNS + ["reject_count", "reject_reason_codes", "batch_date"]
    rejects_df = evaluated_df.filter(F.col("reject_count") > 0).select(*reject_cols)
    rejects_csv_path = PROJECT_ROOT / "data" / "rejects" / "row_level" / f"rejects_{batch_date}.csv"
    write_single_csv_from_df(rejects_df, rejects_csv_path)

    summary_payload = {
        "batch_date": batch_date,
        "sla_status": sla_status,
        "arrival_time_ist": arrival_time,
        "total_rows": total_rows,
        "clean_rows": clean_rows,
        "rejected_rows": rejected_rows,
        "reject_pct": f"{reject_pct:.2f}",
        "max_reject_pct": f"{max_reject_pct:.2f}",
    }
    if summary_out:
        summary_out.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_out, "w", encoding="utf-8") as sf:
            json.dump(summary_payload, sf, indent=2)

    # 4. Enforce batch-level DQ reject threshold (Exit 20 if breached)
    if reject_pct > max_reject_pct:
        print(
            f"[dq_job] BATCH REJECTED: batch={batch_date} reject_pct={reject_pct:.2f}% "
            f"> max_reject_pct={max_reject_pct:.2f}% (rejected={rejected_rows:,}/{total_rows:,})",
            file=sys.stderr,
        )
        evaluated_df.unpersist()
        spark.stop()
        return 20

    # 5. Write clean rows to Parquet partitioned by issue_ym (and batch staging for Postgres load)
    clean_df = evaluated_df.filter(F.col("reject_count") == 0).select(
        F.col("loan_id"),
        F.col("loan_amnt_num").alias("loan_amnt"),
        F.col("funded_amnt_num").alias("funded_amnt"),
        F.col("funded_amnt_inv_num").alias("funded_amnt_inv"),
        F.col("term_months"),
        F.col("int_rate_num").alias("int_rate"),
        F.col("installment_num").alias("installment"),
        F.col("grade"),
        F.col("sub_grade"),
        F.col("emp_length"),
        F.col("home_ownership"),
        F.col("annual_inc_num").alias("annual_inc"),
        F.col("verification_status"),
        F.col("issue_d"),
        F.col("issue_date"),
        F.col("issue_ym"),
        F.col("loan_status"),
        F.col("raw_loan_status"),
        F.col("purpose"),
        F.col("addr_state"),
        F.col("dti_num").alias("dti"),
        F.coalesce(F.col("delinq_2yrs_num"), F.lit(0)).alias("delinq_2yrs"),
        F.col("fico_low_num").alias("fico_range_low"),
        F.col("fico_high_num").alias("fico_range_high"),
        F.coalesce(F.col("revol_bal_num"), F.lit(0.0)).alias("revol_bal"),
        F.col("revol_util_num").alias("revol_util"),
        F.col("total_acc_num").alias("total_acc"),
        F.col("out_prncp_num").alias("out_prncp"),
        F.coalesce(F.col("total_pymnt_num"), F.lit(0.0)).alias("total_pymnt"),
        F.coalesce(F.col("total_rec_prncp_num"), F.lit(0.0)).alias("total_rec_prncp"),
        F.coalesce(F.col("total_rec_late_fee_num"), F.lit(0.0)).alias("total_rec_late_fee"),
        F.coalesce(F.col("recoveries_num"), F.lit(0.0)).alias("recoveries"),
        F.col("last_pymnt_d"),
        F.col("last_pymnt_date"),
        F.col("batch_date"),
    )

    parquet_root = PROJECT_ROOT / "data" / "archive" / "clean_parquet"
    batch_parquet_dir = parquet_root / f"batch_date={batch_date}"

    clean_df.drop("batch_date").write.mode("overwrite").partitionBy("issue_ym").parquet(
        str(batch_parquet_dir)
    )

    print(
        f"[dq_job] Completed batch={batch_date}: checked={total_rows:,}, "
        f"clean={clean_rows:,}, rejected={rejected_rows:,} ({reject_pct:.2f}%)"
    )
    evaluated_df.unpersist()
    spark.stop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LoanWatch PySpark DQ job.")
    parser.add_argument("--input", required=True, help="Path to staged CSV file")
    parser.add_argument("--batch-date", required=True, help="Batch date YYYYMMDD")
    parser.add_argument("--sla-status", default="ON_TIME", help="ON_TIME or LATE")
    parser.add_argument("--arrival-time", default="06:00", help="Arrival HH:MM in IST")
    parser.add_argument("--max-reject-pct", type=float, default=5.0, help="Max reject % threshold")
    parser.add_argument("--summary-out", help="Optional JSON path for summary metrics")
    args = parser.parse_args()

    return run_dq_job(
        input_csv=Path(args.input),
        batch_date=args.batch_date,
        sla_status=args.sla_status,
        arrival_time=args.arrival_time,
        max_reject_pct=args.max_reject_pct,
        summary_out=Path(args.summary_out) if args.summary_out else None,
    )


if __name__ == "__main__":
    sys.exit(main())
