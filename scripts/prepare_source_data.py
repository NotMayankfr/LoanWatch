#!/usr/bin/env python3
"""
Extracts the 30 canonical servicing columns from the Kaggle LendingClub
accepted loans archive (accepted_2007_to_2018Q4.csv) into data/raw/lending_club_30col.csv.

If the Kaggle file is absent on a fresh clone without the Dataset/ directory,
a clearly labeled synthetic fallback can be invoked via --allow-synthetic-fallback.
"""

import argparse
import csv
import gzip
import os
import sys
from pathlib import Path
import pandas as pd

CANONICAL_COLUMNS = [
    "id",
    "loan_amnt",
    "funded_amnt",
    "funded_amnt_inv",
    "term",
    "int_rate",
    "installment",
    "grade",
    "sub_grade",
    "emp_length",
    "home_ownership",
    "annual_inc",
    "verification_status",
    "issue_d",
    "loan_status",
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
]

DEFAULT_SEARCH_PATHS = [
    Path("Dataset/accepted_2007_to_2018q4.csv/accepted_2007_to_2018Q4.csv"),
    Path("/mnt/c/Project/LoanWatch/Dataset/accepted_2007_to_2018q4.csv/accepted_2007_to_2018Q4.csv"),
    Path("Dataset/accepted_2007_to_2018Q4.csv.gz"),
    Path("/mnt/c/Project/LoanWatch/Dataset/accepted_2007_to_2018Q4.csv.gz"),
    Path("data/raw/accepted_2007_to_2018Q4.csv"),
]


def resolve_kaggle_source(explicit_path: str | None) -> Path | None:
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            return p
        raise FileNotFoundError(f"Specified source file not found: {explicit_path}")

    for candidate in DEFAULT_SEARCH_PATHS:
        if candidate.is_file():
            return candidate
    return None


def extract_canonical_columns(src_path: Path, dest_path: Path) -> int:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    total_rows = 0
    compression = "gzip" if src_path.suffix == ".gz" else None

    reader = pd.read_csv(
        src_path,
        usecols=CANONICAL_COLUMNS,
        dtype=str,
        na_filter=False,
        chunksize=250_000,
        compression=compression,
        low_memory=False,
    )

    first_chunk = True
    for chunk in reader:
        chunk = chunk[CANONICAL_COLUMNS]
        # Strip stray CR/LF or embedded commas so downstream POSIX awk/cut field
        # indexing remains deterministic without full RFC-4180 quote parsing in shell.
        for col in CANONICAL_COLUMNS:
            chunk[col] = (
                chunk[col]
                .str.replace("\r", "", regex=False)
                .str.replace("\n", " ", regex=False)
                .str.replace(",", ";", regex=False)
            )

        chunk.to_csv(
            dest_path,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            index=False,
            quoting=csv.QUOTE_NONE,
            escapechar="\\",
            lineterminator="\n",
        )
        total_rows += len(chunk)
        first_chunk = False
        print(f"[prepare_source_data] Extracted {total_rows:,} rows...", flush=True)

    return total_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare 30-column LendingClub source CSV.")
    parser.add_argument("--source", help="Path to Kaggle accepted_2007_to_2018Q4.csv or .csv.gz")
    parser.add_argument(
        "--output",
        default="data/raw/lending_club_30col.csv",
        help="Output path for the 30-column CSV",
    )
    args = parser.parse_args()

    dest_path = Path(args.output)
    src_path = resolve_kaggle_source(args.source)
    if src_path is None:
        print(
            "ERROR: Kaggle accepted_2007_to_2018Q4.csv not found in Dataset/ or data/raw/.",
            file=sys.stderr,
        )
        return 1

    sz_bytes = src_path.stat().st_size
    print(
        f"[prepare_source_data] Reading Kaggle archive: {src_path} "
        f"({sz_bytes:,} bytes / {sz_bytes / (1024**3):.2f} GiB)"
    )
    rows = extract_canonical_columns(src_path, dest_path)
    out_bytes = dest_path.stat().st_size
    print(
        f"[prepare_source_data] Completed: {rows:,} data rows written to {dest_path} "
        f"({out_bytes:,} bytes / {out_bytes / (1024**2):.1f} MiB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
