-- Core relational schema for LoanWatch (PostgreSQL 16)
-- Supports idempotent batch upserts via ON CONFLICT (loan_id) DO UPDATE.

CREATE TABLE IF NOT EXISTS loans_clean (
    loan_id             BIGINT PRIMARY KEY,
    loan_amnt           NUMERIC(14, 2) NOT NULL,
    funded_amnt         NUMERIC(14, 2) NOT NULL,
    funded_amnt_inv     NUMERIC(14, 2) NOT NULL,
    term_months         INTEGER NOT NULL,
    int_rate            NUMERIC(8, 4) NOT NULL,
    installment         NUMERIC(12, 2),
    grade               VARCHAR(4) NOT NULL,
    sub_grade           VARCHAR(6) NOT NULL,
    emp_length          VARCHAR(32),
    home_ownership      VARCHAR(32),
    annual_inc          NUMERIC(16, 2) NOT NULL,
    verification_status VARCHAR(32),
    issue_d             VARCHAR(16) NOT NULL,
    issue_date          DATE NOT NULL,
    issue_ym            VARCHAR(7) NOT NULL,
    loan_status         VARCHAR(40) NOT NULL,
    raw_loan_status     VARCHAR(80),
    purpose             VARCHAR(64),
    addr_state          VARCHAR(4) NOT NULL,
    dti                 NUMERIC(10, 4) NOT NULL,
    delinq_2yrs         INTEGER,
    fico_range_low      INTEGER NOT NULL,
    fico_range_high     INTEGER NOT NULL,
    revol_bal           NUMERIC(16, 2),
    revol_util          NUMERIC(8, 4),
    total_acc           INTEGER,
    out_prncp           NUMERIC(14, 2) NOT NULL,
    total_pymnt         NUMERIC(16, 2),
    total_rec_prncp     NUMERIC(14, 2),
    total_rec_late_fee  NUMERIC(12, 2),
    recoveries          NUMERIC(14, 2),
    last_pymnt_d        VARCHAR(16),
    last_pymnt_date     DATE,
    batch_date          VARCHAR(8) NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_loans_clean_vintage_grade
    ON loans_clean (issue_ym, grade);

CREATE INDEX IF NOT EXISTS idx_loans_clean_state_purpose
    ON loans_clean (addr_state, purpose);

CREATE INDEX IF NOT EXISTS idx_loans_clean_batch_date
    ON loans_clean (batch_date);

CREATE TABLE IF NOT EXISTS dq_scorecard_history (
    batch_date          VARCHAR(8) NOT NULL,
    rule_id             VARCHAR(16) NOT NULL,
    dimension           VARCHAR(32) NOT NULL,
    rule_name           VARCHAR(128) NOT NULL,
    records_checked     BIGINT NOT NULL,
    records_failed      BIGINT NOT NULL,
    pass_pct            NUMERIC(8, 4) NOT NULL,
    threshold_pct       NUMERIC(8, 4) NOT NULL,
    rule_status         VARCHAR(24) NOT NULL,
    sla_status          VARCHAR(24) NOT NULL,
    arrival_time_ist    VARCHAR(16),
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (batch_date, rule_id)
);

CREATE TABLE IF NOT EXISTS dq_column_null_profile (
    batch_date          VARCHAR(8) NOT NULL,
    column_name         VARCHAR(64) NOT NULL,
    records_checked     BIGINT NOT NULL,
    null_count          BIGINT NOT NULL,
    null_pct            NUMERIC(8, 4) NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (batch_date, column_name)
);

CREATE TABLE IF NOT EXISTS vendor_feed_sla_log (
    batch_date          VARCHAR(8) PRIMARY KEY,
    vendor_id           VARCHAR(64) NOT NULL,
    feed_file           VARCHAR(128) NOT NULL,
    arrival_time_ist    VARCHAR(16) NOT NULL,
    sla_cutoff_ist      VARCHAR(16) NOT NULL,
    sla_status          VARCHAR(24) NOT NULL,
    expected_rows       BIGINT NOT NULL,
    actual_rows         BIGINT NOT NULL,
    clean_rows          BIGINT NOT NULL,
    rejected_rows       BIGINT NOT NULL,
    reject_pct          NUMERIC(8, 4) NOT NULL,
    pipeline_status     VARCHAR(32) NOT NULL,
    exit_code           INTEGER NOT NULL,
    notes               TEXT,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
