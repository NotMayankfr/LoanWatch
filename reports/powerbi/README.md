# LoanWatch Enterprise Power BI Reporting Pack
### Production DirectQuery & Import Architecture for Consumer Credit Portfolio Risk & Data Governance

---

## 1. Executive Summary

The **LoanWatch Power BI Reporting Pack** delivers real-time executive and operational intelligence across credit portfolio risk, vintage delinquency tracking, and automated data quality (DQ) governance. Built to emulate the information architecture of Tier-1 bank treasury and retail credit risk units (e.g., Citi Global Consumer Banking / Credit Risk MIS), this reporting suite connects directly to the underlying PostgreSQL analytics data warehouse fed by the PySpark data pipeline.

The suite contains three purpose-built dashboard pages:
1. **Executive Portfolio & Credit Risk Overview** (`01_executive_portfolio_risk.svg`): High-level snapshot of portfolio balance, exposure concentration, pricing (WAC), geographic risk, and active unpaid principal balance (UPB).
2. **Vintage Performance, Delinquency & Charge-Off Analytics** (`02_vintage_delinquency_chargeoff.svg`): Vintage cohort maturation curves, severe delinquency risk distributions, and net credit loss (NCL) / recovery rate trends.
3. **Data Quality Governance & Vendor Feed SLA Monitoring** (`03_dq_governance_vendor_sla.svg`): Rigorous audit log of inbound daily vendor feed arrival against the 06:30 IST SLA cutoff, checksum integrity, and multi-dimensional PySpark DQ scorecard metrics.

---

## 2. Architecture & Data Model

```
+---------------------------------------------------------------------------------------+
|                                PostgreSQL Analytics Warehouse                          |
|                                       (Database: loanwatch)                           |
+-------------------------------------------+-------------------------------------------+
                                            |
         +----------------------------------+-----------------------------------+
         |                                  |                                   |
         v                                  v                                   v
+------------------+              +----------------------+             +---------------------+
|   loans_clean    |              | dq_scorecard_history |             | vendor_feed_sla_log |
| (2,256,390 rows) |              |  (Partitioned Audits)|             |  (Daily Transmissions) |
+--------+---------+              +----------+-----------+             +----------+----------+
         |                                   |                                    |
         +-----------------+                 |                                    |
                           |                 |                                    |
+--------------------------v-----------------v------------------------------------v-----+
|                                Power BI Star Schema Model                             |
|                                                                                       |
|   +-------------------+       +-----------------------+       +-------------------+   |
|   |     Dim_Date      |<----->|      loans_clean      |<----->|    Dim_Grade      |   |
|   |  (issue_month_dt) |  1:N  |     (Fact Table)      |  N:1  |  (Grade A to G)   |   |
|   +-------------------+       +-----------+-----------+       +-------------------+   |
|                                           |                                           |
|                               +-----------+-----------+                               |
|                               |                       |                               |
|                               v                       v                               |
|                       +---------------+       +---------------+                       |
|                       | Dim_Geography |       |  Dim_Purpose  |                       |
|                       |  (addr_state) |       |   (purpose)   |                       |
|                       +---------------+       +---------------+                       |
+---------------------------------------------------------------------------------------+
```

### Storage Mode Configuration
* **Composite / Dual Mode**:
  * **Aggregate Views (Import Mode)**: Pre-aggregated reporting views (`vw_delinquency_vintage`, `vw_exposure_portfolio`, `vw_chargeoff_trends`, `vw_top_concentrations`) are imported into Power BI memory on a scheduled morning refresh for sub-second executive slicer responsiveness.
  * **Transactional Detail (DirectQuery Mode)**: The raw `loans_clean` table (2.26 million rows) and quarantine logs are connected via DirectQuery to allow risk analysts to drill through to individual loan IDs without exceeding memory limits.

### Connection Parameters
* **Server**: `localhost:5432` (or AWS RDS / Azure Database for PostgreSQL in production)
* **Database**: `loanwatch`
* **Schema**: `public`
* **Authentication**: Database Credentials (service account: `pbi_readonly_svc`)

---

## 3. Dashboard Catalog

### Page 1: Executive Portfolio & Credit Risk Overview
**Vector Artifact**: [`01_executive_portfolio_risk.svg`](./01_executive_portfolio_risk.svg)

```
+-----------------------------------------------------------------------------------------------+
| LOANWATCH | Executive Portfolio & Credit Risk Overview              As of: 2026-11-10 19:45   |
+-----------------------+-----------------------+-----------------------+-----------------------+
|  Total Funded Vol     |   Current Active UPB  |  Weighted Avg Coupon  |   30+ DPD Delinq Rate |
|     $33.92B           |         $9.46B        |        13.38%         |         0.95%         |
|  2,256,390 Loans      |   27.9% of Originated |   Range: 5.31%-30.99% |    21,436 Loans       |
+-----------------------+-----------------------+-----------------------+-----------------------+
| Portfolio Balance Trend by Quarter (UPB vs Orig)  | Credit Rating Distribution (Exposure & WAC)|
| [Area/Line Chart: 2007-2018 Maturation]           | [Combo Bar: Grade A ($7.1B) to G ($0.4B)] |
+---------------------------------------------------+-------------------------------------------+
| Geographic Exposure Concentration (Top 5 States)  | Portfolio Segments (Purpose Matrix)       |
| CA: $4.80B | TX: $2.92B | NY: $2.76B              | Debt Consolidation: 59.4% ($20.1B)        |
| FL: $2.33B | IL: $1.40B                           | Credit Card Refinance: 23.1% ($7.8B)      |
+-----------------------------------------------------------------------------------------------+
```

* **Target Audience**: Chief Credit Officer, Head of Retail Lending, ALCO Committee.
* **Key Insights**:
  * Out of $33.92B total cumulative originations, $9.46B remains active outstanding principal balance (UPB), representing a 27.9% remaining balance ratio.
  * Prime Grade A loans command an average WAC of 7.2%, whereas subprime Grade G loans average 28.5%.
  * Geographic concentration is dominated by California ($4.80B), Texas ($2.92B), and New York ($2.76B), representing ~31% of aggregate portfolio exposure.

---

### Page 2: Vintage Performance, Delinquency & Charge-Off Analytics
**Vector Artifact**: [`02_vintage_delinquency_chargeoff.svg`](./02_vintage_delinquency_chargeoff.svg)

```
+-----------------------------------------------------------------------------------------------+
| LOANWATCH | Vintage Performance, Delinquency & Charge-Off          As of: 2026-11-10 19:45    |
+-----------------------+-----------------------+-----------------------+-----------------------+
|   Gross Charge-Off    |     Recovery Total    |    Net Credit Loss    |   Severe Delinq Proxy |
|        $4.42B         |         $371.4M       |         $4.05B        |        11.93%         |
|  268,559 Default/CO   |    8.4% Recovery Rate |  11.94% Lifetime NCL  |  Default + Charged Off|
+-----------------------+-----------------------+-----------------------+-----------------------+
| Cumulative Net Charge-Off by Vintage Cohort       | Severe Delinquency Rate by Credit Grade   |
| [Cohort curves: 2014, 2015, 2016, 2017 vintages]  | Grade A: 2.1%  ---> Grade G: 37.8%        |
+---------------------------------------------------+-------------------------------------------+
| Monthly Net Credit Loss & Recovery Waterfall      | Vintage Maturation Performance Matrix     |
| [Gross CO: $4.42B - Rec: $371.4M = Net: $4.05B]   | 2015 Cohort: $9.8B Orig, $1.4B CO (14.3%) |
+-----------------------------------------------------------------------------------------------+
```

* **Target Audience**: Head of Credit Risk Analytics, Allowance for Credit Loss (CECL/IFRS 9) Specialists.
* **Key Insights**:
  * Total lifetime cumulative charge-offs reached $4.42B across 268,559 loans.
  * Collections recovery efforts recouped $371.4M (8.40% recovery rate), yielding a lifetime Net Credit Loss of $4.05B (11.94% of originated principal).
  * Severe Delinquency Proxy (`Default` + `Charged Off`) scales monotonically by credit grade: Grade A (2.1%), Grade B (6.4%), Grade C (13.1%), Grade D (20.5%), Grade E (28.2%), Grade F (33.9%), Grade G (37.8%).

---

### Page 3: Data Quality Governance & Vendor Feed SLA Monitoring
**Vector Artifact**: [`03_dq_governance_vendor_sla.svg`](./03_dq_governance_vendor_sla.svg)

```
+-----------------------------------------------------------------------------------------------+
| LOANWATCH | Data Quality Governance & Vendor Feed SLA              As of: 2026-11-10 19:45    |
+-----------------------+-----------------------+-----------------------+-----------------------+
|    DQ Pass Rate       |    Records Ingested   |    Quarantine Rejects |   Feed SLA Compliance |
|        99.81%         |       2,256,390       |         4,311         |         83.3%         |
|  Threshold: >= 99.5%  |   2,260,701 Processed |   0.19% Reject Ratio  |   5/6 Timely Feeds    |
+-----------------------+-----------------------+-----------------------+-----------------------+
| Daily Vendor Inbound Feed Arrival vs 06:30 Cutoff | PySpark DQ Rule Scorecard (Dimension Audit)|
| [Timeline scatter: On-time vs Late vs Missing]    | Completeness: 100.0% | Validity: 99.8%|
+---------------------------------------------------+-------------------------------------------+
| Quarantine Reject Reason Breakdown                | Feed Transmission Integrity Ledger        |
| DTI Out of Bounds [0,100]: 3,921 (91.0%)          | feed_201803: SHA-256 Match, Exit 0        |
| Unmatched Grade/Subgrade: 312 (7.2%)              | feed_corrupt_trunc: Exit 11 (Checksum Fail)|
| Negative Term/Amount: 78 (1.8%)                   | feed_corrupt_breach: Exit 20 (>8% Breach) |
+-----------------------------------------------------------------------------------------------+
```

* **Target Audience**: Data Governance Officers, Chief Data Office (CDO), Vendor Operations Oversight.
* **Key Insights**:
  * **99.81% DQ Pass Rate**: 2,256,390 records successfully ingested; 4,311 records rejected into quarantine tables with deterministic reason codes.
  * **Primary Quarantine Driver**: Real-world LendingClub dataset exhibits non-standard DTI values outside $[0, 100]$ (e.g. 999.0 or negative entries), representing 91.0% (3,921 rows) of rejects. Under Citi governance standards, rules are never relaxed to hide vendor flaws; rather, records are quarantined for partner reconciliation.
  * **Vendor Feed SLA Tracking**: Demonstrates negative-testing coverage of late arrivals (07:18 IST vs 06:30 IST cutoff), checksum mismatches (Exit 11), manifest count discrepancies (Exit 12), malformed headers (Exit 13), and catastrophic payload corruption exceeding 8% breach (Exit 20).

---

## 4. DAX Measure Library Highlights

The complete DAX measure repository is maintained in [`reports/powerbi/measures.dax`](./measures.dax). Key measures include:

### 1. Weighted Average Coupon (WAC)
```dax
[Weighted Average Coupon (WAC)] = 
DIVIDE(
    SUMX('loans_clean', 'loans_clean'[int_rate] * 'loans_clean'[funded_amnt]),
    [Total Funded Exposure],
    0
)
```

### 2. Severe Delinquency Proxy Rate
```dax
[Severe Delinquency Loans Count] = 
CALCULATE(
    COUNTROWS('loans_clean'),
    'loans_clean'[loan_status] IN {"Default", "Charged Off"}
)

[Severe Delinquency Proxy Rate %] = 
DIVIDE([Severe Delinquency Loans Count], [Total Loans Clean], 0)
```

### 3. Net Credit Loss (NCL)
```dax
[Gross Charge-Off Principal] = 
CALCULATE(
    SUMX(
        'loans_clean',
        COALESCE('loans_clean'[recoveries], 0) + 'loans_clean'[total_rec_prncp] < 'loans_clean'[funded_amnt],
        'loans_clean'[funded_amnt] - 'loans_clean'[total_rec_prncp]
    ),
    'loans_clean'[loan_status] = "Charged Off"
)

[Total Recoveries] = 
SUM('loans_clean'[recoveries])

[Net Credit Loss ($B)] = 
DIVIDE([Gross Charge-Off Principal] - [Total Recoveries], 1000000000, 0)
```

### 4. Dynamic DQ Scorecard Health Status
```dax
[DQ Health Status] = 
SWITCH(
    TRUE(),
    [DQ Pass Rate %] >= 0.995, "HEALTHY (Pass >= 99.5%)",
    [DQ Pass Rate %] >= 0.980, "WARNING (Pass 98.0%-99.5%)",
    "CRITICAL BREACH (< 98.0%)"
)
```

---

## 5. Deployment & Refresh Instructions

1. **Power BI Desktop Setup**:
   * Open `reports/LoanWatch.pbix` in Power BI Desktop (May 2024 or later).
   * Go to **Home > Transform Data > Data Source Settings**.
   * Change Source to your local PostgreSQL instance: `localhost:5432` / Database: `loanwatch`.
   * Apply changes.

2. **Automated Enterprise Refresh**:
   * On Windows / On-Premises Data Gateway:
     * Configure an Enterprise Gateway connection to the PostgreSQL database `loanwatch`.
     * Schedule daily refresh at **07:30 IST** (allowing 1 hour after the 06:30 IST vendor SLA cutoff and pipeline ingestion).
   * On Linux / WSL CI/CD:
     * Run `bash scripts/ingest.sh` to trigger the daily ingest and update Postgres views.
     * Execute Power BI REST API refresh trigger via Python script using Azure AD service principal credentials.

3. **Regenerating Dashboard Vector Assets**:
   * If new feeds alter portfolio metrics, regenerate the crisp vector SVG documentation dashboards using:
     ```bash
     python scripts/generate_pbi_svgs.py
     ```
   * Outputs are saved directly to `reports/powerbi/*.svg` for inclusion in documentation and pull requests.
