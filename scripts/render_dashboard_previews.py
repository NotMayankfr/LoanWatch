#!/usr/bin/env python3
"""
Generates portfolio risk, vintage loss, and vendor SLA charts with matplotlib
from the PostgreSQL views into reports/figures/.
"""

import sys
import warnings
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, message=".*pandas only supports SQLAlchemy.*")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.load_postgres import get_conn


def render_charts() -> None:
    fig_dir = PROJECT_ROOT / "reports" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "axes.edgecolor": "#CBD5E0",
            "axes.grid": True,
            "grid.alpha": 0.3,
        }
    )

    conn = get_conn()
    try:
        grade_df = pd.read_sql_query(
            """
            SELECT
                grade,
                COUNT(*) AS loans,
                ROUND(SUM(funded_amnt) / 1e9, 3) AS funded_bn,
                ROUND(SUM(out_prncp) / 1e9, 3) AS upb_bn,
                ROUND(
                    SUM(CASE WHEN loan_status IN ('Late (31-120 days)', 'Default') THEN 1 ELSE 0 END)::NUMERIC
                    * 100.0 / NULLIF(COUNT(*), 0), 2
                ) AS delinq_30p_pct,
                ROUND(
                    SUM(CASE WHEN loan_status IN ('Default', 'Charged Off') THEN 1 ELSE 0 END)::NUMERIC
                    * 100.0 / NULLIF(COUNT(*), 0), 2
                ) AS severe_delinq_pct
            FROM loans_clean
            GROUP BY grade
            ORDER BY grade;
            """,
            conn,
        )

        loss_df = pd.read_sql_query(
            """
            SELECT issue_ym, originated_funded_amnt / 1e6 AS funded_mm,
                   net_loss_rate_pct, rolling_3m_net_loss_rate_pct
            FROM vw_chargeoff_loss_trend
            WHERE issue_ym BETWEEN '2014-01' AND '2018-12'
            ORDER BY issue_ym;
            """,
            conn,
        )

        state_df = pd.read_sql_query(
            """
            SELECT addr_state, ROUND(SUM(funded_exposure) / 1e9, 3) AS funded_bn
            FROM vw_exposure_by_purpose_state
            GROUP BY addr_state
            ORDER BY funded_bn DESC
            LIMIT 12;
            """,
            conn,
        )

        sla_df = pd.read_sql_query(
            """
            SELECT batch_date, sla_status, pipeline_status, actual_rows, clean_rows, rejected_rows, exit_code
            FROM vendor_feed_sla_log
            ORDER BY batch_date;
            """,
            conn,
        )
    finally:
        conn.close()

    # Figure 1: Exposure & Delinquency by Credit Grade + Top States
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=160)
    x = range(len(grade_df))
    ax1.bar(x, grade_df["funded_bn"], width=0.55, color="#1B365D", label="Funded Principal ($B)")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(grade_df["grade"])
    ax1.set_xlabel("Credit Grade")
    ax1.set_ylabel("Funded Exposure ($ Billions)", color="#1B365D")
    ax1.set_title("Portfolio Funded Exposure & Delinquency Rates by Grade", fontweight="bold")

    ax1b = ax1.twinx()
    ax1b.plot(
        list(x),
        grade_df["severe_delinq_pct"],
        color="#C53030",
        marker="o",
        linewidth=2.2,
        label="Severe Delinquency Proxy (%)",
    )
    ax1b.plot(
        list(x),
        grade_df["delinq_30p_pct"],
        color="#DD6B20",
        marker="s",
        linewidth=2.0,
        linestyle="--",
        label="30+ DPD Rate (%)",
    )
    ax1b.set_ylabel("Delinquency / Default Rate (%)", color="#C53030")
    ax1b.grid(False)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1b.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8.5)

    ax2.barh(
        state_df["addr_state"][::-1],
        state_df["funded_bn"][::-1],
        color="#2B6CB0",
        height=0.65,
    )
    ax2.set_xlabel("Funded Exposure ($ Billions)")
    ax2.set_title("Top 12 US States by Funded Concentration", fontweight="bold")
    fig.tight_layout()
    fig.savefig(fig_dir / "01_portfolio_exposure_and_delinquency.png")
    plt.close(fig)

    # Figure 2: Vintage Net Credit Loss Trend (with 3M Rolling Average)
    fig, ax = plt.subplots(figsize=(13, 5.0), dpi=160)
    idx = range(len(loss_df))
    ax.bar(idx, loss_df["funded_mm"], color="#CBD5E0", alpha=0.65, label="Originated Funded ($M)")
    ax.set_ylabel("Monthly Origination Volume ($ Millions)", color="#4A5568")
    step = max(1, len(loss_df) // 12)
    ax.set_xticks(list(idx)[::step])
    ax.set_xticklabels(loss_df["issue_ym"].iloc[::step], rotation=35, ha="right")

    ax_loss = ax.twinx()
    ax_loss.plot(
        list(idx),
        loss_df["net_loss_rate_pct"],
        color="#A0AEC0",
        linewidth=1.2,
        linestyle=":",
        label="Monthly Net Credit Loss (%)",
    )
    ax_loss.plot(
        list(idx),
        loss_df["rolling_3m_net_loss_rate_pct"],
        color="#9B2C2C",
        linewidth=2.4,
        label="3M Rolling Net Credit Loss (%)",
    )
    ax_loss.set_ylabel("Net Credit Loss Rate (%)", color="#9B2C2C")
    ax_loss.grid(False)
    ax.set_title("Vintage Origination Volume & 3-Month Rolling Net Credit Loss Trend (2014–2018)", fontweight="bold")
    l1, lb1 = ax.get_legend_handles_labels()
    l2, lb2 = ax_loss.get_legend_handles_labels()
    ax.legend(l1 + l2, lb1 + lb2, loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(fig_dir / "02_vintage_chargeoff_and_loss_trend.png")
    plt.close(fig)

    # Figure 3: Vendor Feed SLA & Gatekeeper Outcomes
    fig, ax = plt.subplots(figsize=(12.5, 4.8), dpi=160)
    colors = []
    for _, r in sla_df.iterrows():
        if r["exit_code"] != 0:
            colors.append("#C53030")
        elif r["sla_status"] == "LATE":
            colors.append("#DD6B20")
        else:
            colors.append("#2F855A")

    x_sla = range(len(sla_df))
    heights = [max(int(v), 5000) for v in sla_df["actual_rows"]]
    bars = ax.bar(x_sla, heights, color=colors, width=0.6)
    ax.set_xticks(list(x_sla))
    ax.set_xticklabels(sla_df["batch_date"], rotation=30, ha="right")
    ax.set_ylabel("Feed Row Count (Log/Visual Scale Floor for Missing)")
    ax.set_title("Vendor Feed Gatekeeper & SLA Audit Outcomes (Green=On-Time Pass, Orange=Late Pass, Red=Rejected)", fontweight="bold")
    for bar, (_, r) in zip(bars, sla_df.iterrows()):
        lbl = f"Exit {r['exit_code']}\n{r['pipeline_status'].replace('REJECTED_', '')}"
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + max(heights) * 0.02,
            lbl,
            ha="center",
            va="bottom",
            fontsize=7.5,
            fontweight="bold",
        )
    ax.set_ylim(0, max(heights) * 1.22)
    fig.tight_layout()
    fig.savefig(fig_dir / "03_dq_scorecard_and_vendor_sla.png")
    plt.close(fig)
    print(f"[render_dashboard_previews] Saved 3 charts to {fig_dir}")


if __name__ == "__main__":
    render_charts()
