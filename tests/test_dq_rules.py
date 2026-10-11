"""
Unit tests for LoanWatch PySpark normalization and 12 DQ rules (spark/dq_rules.py).
"""

from spark.dq_rules import apply_dq_rules, normalize_feed_df
from spark.schema import CANONICAL_COLUMNS, RAW_FEED_SCHEMA


def _valid_base_row(**overrides) -> dict:
    base = {
        "id": "68407277",
        "loan_amnt": "10000.0",
        "funded_amnt": "10000.0",
        "funded_amnt_inv": "10000.0",
        "term": " 36 months",
        "int_rate": "11.49%",
        "installment": "329.72",
        "grade": "B",
        "sub_grade": "B5",
        "emp_length": "10+ years",
        "home_ownership": "MORTGAGE",
        "annual_inc": "75000.0",
        "verification_status": "Verified",
        "issue_d": "Dec-2017",
        "loan_status": "Current",
        "purpose": "debt_consolidation",
        "addr_state": "NY",
        "dti": "18.45",
        "delinq_2yrs": "0.0",
        "fico_range_low": "710.0",
        "fico_range_high": "714.0",
        "revol_bal": "12400.0",
        "revol_util": "42.1%",
        "total_acc": "19.0",
        "out_prncp": "4250.00",
        "total_pymnt": "6800.00",
        "total_rec_prncp": "5750.00",
        "total_rec_late_fee": "0.0",
        "recoveries": "0.0",
        "last_pymnt_d": "Oct-2018",
    }
    base.update(overrides)
    return base


def _eval_rows(spark, rows: list[dict]):
    tuples = [[r.get(c) for c in CANONICAL_COLUMNS] for r in rows]
    raw_df = spark.createDataFrame(tuples, schema=RAW_FEED_SCHEMA)
    norm_df = normalize_feed_df(raw_df, batch_date="20261005")
    return apply_dq_rules(norm_df).orderBy("_row_seq").collect()


def test_clean_record_passes_all_12_rules(spark):
    res = _eval_rows(spark, [_valid_base_row()])[0]
    assert res["reject_count"] == 0
    assert res["reject_reason_codes"] == ""
    assert res["term_months"] == 36
    assert abs(res["int_rate_num"] - 11.49) < 1e-6
    assert res["issue_ym"] == "2017-12"


def test_legacy_credit_policy_status_normalization(spark):
    rows = [
        _valid_base_row(
            id="100001",
            loan_status="Does not meet the credit policy. Status:Fully Paid",
            out_prncp="0.0",
        ),
        _valid_base_row(
            id="100002",
            loan_status="Does not meet the credit policy. Status:Charged Off",
            out_prncp="0.0",
        ),
    ]
    res = _eval_rows(spark, rows)
    assert res[0]["loan_status"] == "Fully Paid"
    assert res[0]["raw_loan_status"] == "Does not meet the credit policy. Status:Fully Paid"
    assert res[0]["reject_count"] == 0

    assert res[1]["loan_status"] == "Charged Off"
    assert res[1]["reject_count"] == 0


def test_uniqueness_keeps_first_row_and_rejects_duplicates_and_footers(spark):
    rows = [
        _valid_base_row(id="555001", loan_amnt="12000.0", funded_amnt="12000.0", funded_amnt_inv="12000.0"),
        _valid_base_row(id="555001", loan_amnt="12000.0", funded_amnt="12000.0", funded_amnt_inv="12000.0"),
        _valid_base_row(id="Total amount funded in policy code 1: 1465324575", loan_amnt=None),
    ]
    res = _eval_rows(spark, rows)
    # First occurrence passes DQ_UNQ_001
    assert res[0]["pass_DQ_UNQ_001"] is True
    assert res[0]["reject_count"] == 0

    # Second duplicate occurrence fails DQ_UNQ_001
    assert res[1]["pass_DQ_UNQ_001"] is False
    assert "DQ_UNQ_001" in res[1]["reject_reason_codes"].split("|")

    # Non-numeric summary footer line fails DQ_UNQ_001 and DQ_CMP_001
    assert res[2]["pass_DQ_UNQ_001"] is False
    assert "DQ_UNQ_001" in res[2]["reject_reason_codes"].split("|")


def test_out_of_range_dti_and_invalid_state_rejected(spark):
    rows = [
        _valid_base_row(id="700001", dti="-1.0"),
        _valid_base_row(id="700002", dti="999.0", addr_state="XX"),
    ]
    res = _eval_rows(spark, rows)
    assert res[0]["pass_DQ_VAL_003"] is False
    assert res[0]["reject_reason_codes"] == "DQ_VAL_003"

    assert res[1]["pass_DQ_VAL_002"] is False
    assert res[1]["pass_DQ_VAL_003"] is False
    assert set(res[1]["reject_reason_codes"].split("|")) == {"DQ_VAL_002", "DQ_VAL_003"}


def test_consistency_funded_gt_loan_and_terminal_upb(spark):
    rows = [
        _valid_base_row(id="800001", loan_amnt="10000.0", funded_amnt="15000.0"),
        _valid_base_row(id="800002", loan_status="Charged Off", out_prncp="1200.0"),
    ]
    res = _eval_rows(spark, rows)
    assert res[0]["pass_DQ_CNS_001"] is False
    assert "DQ_CNS_001" in res[0]["reject_reason_codes"]

    assert res[1]["pass_DQ_CNS_002"] is False
    assert "DQ_CNS_002" in res[1]["reject_reason_codes"]
