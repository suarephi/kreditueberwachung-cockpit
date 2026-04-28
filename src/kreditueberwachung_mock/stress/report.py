"""Auto-generate output/stress_test.md."""
from __future__ import annotations
import sqlite3
import pandas as pd
from .. import config


REPORT_PATH = config.OUTPUT_DIR / "stress_test.md"


def write_report() -> None:
    con = sqlite3.connect(config.DB_PATH)
    try:
        scenarios = pd.read_sql_query("SELECT * FROM stress_scenario", con)
        if scenarios.empty:
            REPORT_PATH.write_text("No stress scenarios have been run.", encoding="utf-8")
            return
        kpis = pd.read_sql_query("""
            SELECT s.scenario_id, s.name, s.severity, k.period,
                   ROUND(k.total_exposure/1e6, 1)        AS exposure_mchf,
                   ROUND(k.expected_loss_total/1e6, 2)   AS el_mchf,
                   ROUND(k.weighted_avg_ltv, 2)          AS avg_ltv,
                   ROUND(k.share_ltv_gt80*100, 2)        AS pct_ltv_gt80,
                   ROUND(k.share_dsti_gt33*100, 2)       AS pct_dsti_gt33,
                   ROUND(k.npl_share*100, 2)             AS pct_npl
              FROM stress_scenario s
              JOIN stress_portfolio_kpi k USING(scenario_id)
        """, con)
        breaches = pd.read_sql_query("""
            SELECT scenario_id, event_type, COUNT(*) AS n
              FROM stress_event
             GROUP BY 1, 2
             ORDER BY 1, 3 DESC
        """, con)
    finally:
        con.close()

    lines = ["# Stress test report\n"]
    lines += ["## Scenario catalog\n",
              "| ID | Severity | Horizon Q | Source |",
              "|---|---|---:|---|"]
    for _, r in scenarios.iterrows():
        lines.append(f"| `{r['scenario_id']}` | {r['severity']} | {r['horizon_quarters']} | {r['source']} |")

    lines += ["", "## KPIs by scenario × period\n",
              "| Scenario | Period | Exposure (MCHF) | EL (MCHF) | Ø LTV | %LTV>80 | %DSTI>33 | %NPL |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in kpis.iterrows():
        lines.append(f"| {r['scenario_id']} | {r['period']} | {r['exposure_mchf']} "
                     f"| {r['el_mchf']} | {r['avg_ltv']} | {r['pct_ltv_gt80']} "
                     f"| {r['pct_dsti_gt33']} | {r['pct_npl']} |")

    if not breaches.empty:
        lines += ["", "## Stress events by scenario\n",
                  "| Scenario | Event type | Count |", "|---|---|---:|"]
        for _, r in breaches.iterrows():
            lines.append(f"| {r['scenario_id']} | {r['event_type']} | {r['n']:,} |")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
