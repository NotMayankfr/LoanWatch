"""
Explicit 30-column schema definitions for the LendingClub vendor feed.
"""

from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

CANONICAL_COLUMNS: list[str] = [
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

# Raw landing schema: read all 30 fields as StringType first so raw formatting quirks
# (" 36 months", "13.56%", policy-code footer lines) can be audited before casting.
RAW_FEED_SCHEMA = StructType(
    [StructField(col_name, StringType(), nullable=True) for col_name in CANONICAL_COLUMNS]
)

CLEAN_PARQUET_SCHEMA = StructType(
    [
        StructField("loan_id", LongType(), nullable=False),
        StructField("loan_amnt", DoubleType(), nullable=False),
        StructField("funded_amnt", DoubleType(), nullable=False),
        StructField("funded_amnt_inv", DoubleType(), nullable=False),
        StructField("term_months", IntegerType(), nullable=False),
        StructField("int_rate", DoubleType(), nullable=False),
        StructField("installment", DoubleType(), nullable=True),
        StructField("grade", StringType(), nullable=False),
        StructField("sub_grade", StringType(), nullable=False),
        StructField("emp_length", StringType(), nullable=True),
        StructField("home_ownership", StringType(), nullable=True),
        StructField("annual_inc", DoubleType(), nullable=False),
        StructField("verification_status", StringType(), nullable=True),
        StructField("issue_d", StringType(), nullable=False),
        StructField("issue_date", DateType(), nullable=False),
        StructField("issue_ym", StringType(), nullable=False),
        StructField("loan_status", StringType(), nullable=False),
        StructField("raw_loan_status", StringType(), nullable=True),
        StructField("purpose", StringType(), nullable=True),
        StructField("addr_state", StringType(), nullable=False),
        StructField("dti", DoubleType(), nullable=False),
        StructField("delinq_2yrs", IntegerType(), nullable=True),
        StructField("fico_range_low", IntegerType(), nullable=False),
        StructField("fico_range_high", IntegerType(), nullable=False),
        StructField("revol_bal", DoubleType(), nullable=True),
        StructField("revol_util", DoubleType(), nullable=True),
        StructField("total_acc", IntegerType(), nullable=True),
        StructField("out_prncp", DoubleType(), nullable=False),
        StructField("total_pymnt", DoubleType(), nullable=True),
        StructField("total_rec_prncp", DoubleType(), nullable=True),
        StructField("total_rec_late_fee", DoubleType(), nullable=True),
        StructField("recoveries", DoubleType(), nullable=True),
        StructField("last_pymnt_d", StringType(), nullable=True),
        StructField("last_pymnt_date", DateType(), nullable=True),
        StructField("batch_date", StringType(), nullable=False),
    ]
)
