"""
Rule-based Data Quality (DQ) definitions across 5 dimensions:
Completeness, Uniqueness, Validity, Consistency, and Timeliness.
"""

from dataclasses import dataclass
from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F
from spark.schema import CANONICAL_COLUMNS

VALID_US_STATES: list[str] = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

VALID_GRADES: list[str] = ["A", "B", "C", "D", "E", "F", "G"]

VALID_LOAN_STATUSES: list[str] = [
    "Current",
    "Fully Paid",
    "Charged Off",
    "Late (31-120 days)",
    "In Grace Period",
    "Late (16-30 days)",
    "Default",
    "Issued",
]


@dataclass(frozen=True)
class DQRuleSpec:
    rule_id: str
    dimension: str
    rule_name: str
    threshold_pct: float
    description: str


DQ_RULE_SPECS: list[DQRuleSpec] = [
    DQRuleSpec(
        "DQ_CMP_001",
        "Completeness",
        "Mandatory Contract Keys Non-Null",
        99.90,
        "id, loan_amnt, funded_amnt, term, int_rate, grade, issue_d, loan_status, addr_state must be non-null",
    ),
    DQRuleSpec(
        "DQ_CMP_002",
        "Completeness",
        "Underwriting Attributes Populated",
        99.50,
        "annual_inc, dti, fico_range_low, fico_range_high must be populated",
    ),
    DQRuleSpec(
        "DQ_UNQ_001",
        "Uniqueness",
        "Numeric & Unique Loan ID (First-Row Retention)",
        99.95,
        "id must be numeric (rejects footer lines) and unique via row_number() == 1",
    ),
    DQRuleSpec(
        "DQ_VAL_001",
        "Validity",
        "Credit Grade & Sub-Grade Domain",
        99.90,
        "grade in A..G, sub_grade in A1..G5 matching grade prefix, valid loan_status",
    ),
    DQRuleSpec(
        "DQ_VAL_002",
        "Validity",
        "US State Jurisdiction Code",
        99.90,
        "addr_state in 50 US states + DC postal abbreviations",
    ),
    DQRuleSpec(
        "DQ_VAL_003",
        "Validity",
        "Rate, DTI [0,100] & Non-Negative Income Bounds",
        99.00,
        "int_rate in [5.0, 36.0], dti in [0.0, 100.0], annual_inc >= 0",
    ),
    DQRuleSpec(
        "DQ_VAL_004",
        "Validity",
        "Loan Amount & Term Bounds",
        99.90,
        "loan_amnt in [500, 40000] and term_months in {36, 60}",
    ),
    DQRuleSpec(
        "DQ_VAL_005",
        "Validity",
        "Issue Date Format & Vintage Range",
        99.90,
        "issue_d parses as MMM-yyyy within 2007-01-01..2018-12-31",
    ),
    DQRuleSpec(
        "DQ_VAL_006",
        "Validity",
        "FICO Score Range Bounds",
        99.90,
        "fico_range_low and fico_range_high within [300, 850]",
    ),
    DQRuleSpec(
        "DQ_CNS_001",
        "Consistency",
        "Funded Amount <= Approved Loan Amount",
        99.95,
        "0 < funded_amnt <= loan_amnt and funded_amnt_inv <= funded_amnt",
    ),
    DQRuleSpec(
        "DQ_CNS_002",
        "Consistency",
        "UPB <= Funded, FICO High >= Low & Zero UPB on Terminal Status",
        99.90,
        "0 <= out_prncp <= funded_amnt, fico_high >= fico_low, out_prncp == 0 when Fully Paid/Charged Off",
    ),
    DQRuleSpec(
        "DQ_TIM_001",
        "Timeliness",
        "Payment Chronology & SLA Timeliness",
        99.90,
        "last_pymnt_d (when present) >= issue_d",
    ),
]


def _clean_str(col_name: str) -> Column:
    trimmed = F.trim(F.col(col_name))
    return F.when(trimmed == "", F.lit(None).cast("string")).otherwise(trimmed)


def normalize_feed_df(raw_df: DataFrame, batch_date: str) -> DataFrame:
    """
    Trims whitespace, strips '%' and 'months' suffixes, normalizes legacy
    LendingClub credit-policy statuses to their base status, and casts fields.
    """
    df = raw_df
    for c in CANONICAL_COLUMNS:
        if c in df.columns:
            df = df.withColumn(c, _clean_str(c))

    df = df.withColumn("_row_seq", F.monotonically_increasing_id())
    df = df.withColumn("raw_loan_status", F.col("loan_status"))

    # Map "Does not meet the credit policy. Status:Fully Paid" -> "Fully Paid"
    # and "Does not meet the credit policy. Status:Charged Off" -> "Charged Off"
    df = df.withColumn(
        "loan_status",
        F.when(
            F.col("loan_status").like("Does not meet the credit policy. Status:%"),
            F.trim(F.regexp_extract(F.col("loan_status"), r"Status:(.*)$", 1)),
        ).otherwise(F.col("loan_status")),
    )

    df = (
        df.withColumn(
            "is_numeric_id",
            F.col("id").isNotNull() & F.col("id").rlike(r"^[0-9]+$"),
        )
        .withColumn(
            "loan_id",
            F.when(F.col("is_numeric_id"), F.col("id").cast("long")).otherwise(F.lit(None).cast("long")),
        )
        .withColumn("loan_amnt_num", F.col("loan_amnt").cast("double"))
        .withColumn("funded_amnt_num", F.col("funded_amnt").cast("double"))
        .withColumn("funded_amnt_inv_num", F.col("funded_amnt_inv").cast("double"))
        .withColumn(
            "term_months",
            F.regexp_replace(F.col("term"), r"[^0-9]", "").cast("int"),
        )
        .withColumn(
            "int_rate_num",
            F.regexp_replace(F.col("int_rate"), "%", "").cast("double"),
        )
        .withColumn("installment_num", F.col("installment").cast("double"))
        .withColumn("annual_inc_num", F.col("annual_inc").cast("double"))
        .withColumn("dti_num", F.col("dti").cast("double"))
        .withColumn("delinq_2yrs_num", F.col("delinq_2yrs").cast("double").cast("int"))
        .withColumn("fico_low_num", F.col("fico_range_low").cast("double").cast("int"))
        .withColumn("fico_high_num", F.col("fico_range_high").cast("double").cast("int"))
        .withColumn("revol_bal_num", F.col("revol_bal").cast("double"))
        .withColumn(
            "revol_util_num",
            F.regexp_replace(F.col("revol_util"), "%", "").cast("double"),
        )
        .withColumn("total_acc_num", F.col("total_acc").cast("double").cast("int"))
        .withColumn("out_prncp_num", F.col("out_prncp").cast("double"))
        .withColumn("total_pymnt_num", F.col("total_pymnt").cast("double"))
        .withColumn("total_rec_prncp_num", F.col("total_rec_prncp").cast("double"))
        .withColumn("total_rec_late_fee_num", F.col("total_rec_late_fee").cast("double"))
        .withColumn("recoveries_num", F.col("recoveries").cast("double"))
        .withColumn("issue_date", F.to_date(F.col("issue_d"), "MMM-yyyy"))
        .withColumn("issue_ym", F.date_format(F.col("issue_date"), "yyyy-MM"))
        .withColumn("last_pymnt_date", F.to_date(F.col("last_pymnt_d"), "MMM-yyyy"))
        .withColumn("batch_date", F.lit(batch_date))
    )

    # First-row retention window for numeric loan IDs; non-numeric IDs get row_num = 0
    id_win = Window.partitionBy("loan_id").orderBy(F.col("_row_seq").asc())
    df = df.withColumn(
        "_id_row_num",
        F.when(F.col("is_numeric_id"), F.row_number().over(id_win)).otherwise(F.lit(0)),
    )
    return df


def apply_dq_rules(df: DataFrame) -> DataFrame:
    """
    Attaches boolean pass flags (pass_DQ_*) for all 12 rules plus a
    pipe-delimited reject_reason_codes string column.
    """
    pass_cmp_001 = (
        F.col("id").isNotNull()
        & F.col("loan_amnt").isNotNull()
        & F.col("funded_amnt").isNotNull()
        & F.col("term").isNotNull()
        & F.col("int_rate").isNotNull()
        & F.col("grade").isNotNull()
        & F.col("issue_d").isNotNull()
        & F.col("loan_status").isNotNull()
        & F.col("addr_state").isNotNull()
    )

    pass_cmp_002 = (
        F.col("annual_inc").isNotNull()
        & F.col("dti").isNotNull()
        & F.col("fico_range_low").isNotNull()
        & F.col("fico_range_high").isNotNull()
    )

    pass_unq_001 = F.col("is_numeric_id") & (F.col("_id_row_num") == 1)

    pass_val_001 = (
        F.col("grade").isin(VALID_GRADES)
        & F.col("sub_grade").rlike(r"^[A-G][1-5]$")
        & (F.substring(F.col("sub_grade"), 1, 1) == F.col("grade"))
        & F.col("loan_status").isin(VALID_LOAN_STATUSES)
    )

    pass_val_002 = F.col("addr_state").isin(VALID_US_STATES)

    pass_val_003 = (
        F.col("int_rate_num").isNotNull()
        & F.col("int_rate_num").between(5.0, 36.0)
        & F.col("dti_num").isNotNull()
        & F.col("dti_num").between(0.0, 100.0)
        & F.col("annual_inc_num").isNotNull()
        & (F.col("annual_inc_num") >= 0.0)
    )

    pass_val_004 = (
        F.col("loan_amnt_num").isNotNull()
        & F.col("loan_amnt_num").between(500.0, 40000.0)
        & F.col("term_months").isin([36, 60])
    )

    pass_val_005 = (
        F.col("issue_date").isNotNull()
        & (F.col("issue_date") >= F.lit("2007-01-01").cast("date"))
        & (F.col("issue_date") <= F.lit("2018-12-31").cast("date"))
    )

    pass_val_006 = (
        F.col("fico_low_num").isNotNull()
        & F.col("fico_low_num").between(300, 850)
        & F.col("fico_high_num").isNotNull()
        & F.col("fico_high_num").between(300, 850)
    )

    pass_cns_001 = (
        F.col("loan_amnt_num").isNotNull()
        & F.col("funded_amnt_num").isNotNull()
        & F.col("funded_amnt_inv_num").isNotNull()
        & (F.col("funded_amnt_num") > 0.0)
        & (F.col("funded_amnt_num") <= F.col("loan_amnt_num") + 0.01)
        & (F.col("funded_amnt_inv_num") <= F.col("funded_amnt_num") + 0.01)
    )

    terminal_upb_ok = F.when(
        F.col("loan_status").isin(["Fully Paid", "Charged Off"]),
        F.col("out_prncp_num") <= 0.01,
    ).otherwise(F.lit(True))

    pass_cns_002 = (
        F.col("out_prncp_num").isNotNull()
        & (F.col("out_prncp_num") >= 0.0)
        & (F.col("out_prncp_num") <= F.col("funded_amnt_num") + 0.01)
        & (F.col("fico_high_num") >= F.col("fico_low_num"))
        & terminal_upb_ok
    )

    pass_tim_001 = F.when(
        F.col("last_pymnt_d").isNotNull(),
        F.col("last_pymnt_date").isNotNull()
        & F.col("issue_date").isNotNull()
        & (F.col("last_pymnt_date") >= F.col("issue_date")),
    ).otherwise(F.lit(True))

    rule_map = [
        ("DQ_CMP_001", pass_cmp_001),
        ("DQ_CMP_002", pass_cmp_002),
        ("DQ_UNQ_001", pass_unq_001),
        ("DQ_VAL_001", pass_val_001),
        ("DQ_VAL_002", pass_val_002),
        ("DQ_VAL_003", pass_val_003),
        ("DQ_VAL_004", pass_val_004),
        ("DQ_VAL_005", pass_val_005),
        ("DQ_VAL_006", pass_val_006),
        ("DQ_CNS_001", pass_cns_001),
        ("DQ_CNS_002", pass_cns_002),
        ("DQ_TIM_001", pass_tim_001),
    ]

    for rule_id, expr in rule_map:
        df = df.withColumn(f"pass_{rule_id}", F.coalesce(expr, F.lit(False)))

    reason_tokens = [
        F.when(~F.col(f"pass_{rule_id}"), F.lit(rule_id)).otherwise(F.lit(""))
        for rule_id, _ in rule_map
    ]
    df = df.withColumn(
        "_reason_arr",
        F.array_remove(F.array(*reason_tokens), ""),
    )
    df = df.withColumn("reject_count", F.size(F.col("_reason_arr")))
    df = df.withColumn("reject_reason_codes", F.concat_ws("|", F.col("_reason_arr")))
    df = df.drop("_reason_arr")
    return df
