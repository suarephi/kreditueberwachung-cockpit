#!/usr/bin/env python3
"""Sanity checks: row counts, FK orphans, KPI distributions, error-rate audit."""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kreditueberwachung_mock import config


def fetch(con, sql, params=()):
    return con.execute(sql, params).fetchall()


def main() -> int:
    if not config.DB_PATH.exists():
        print(f"Database not found: {config.DB_PATH}", file=sys.stderr)
        return 1
    con = sqlite3.connect(config.DB_PATH)
    print(f"Database: {config.DB_PATH}\n")

    print("--- Row counts ---")
    tables = ["client", "address", "household", "client_household", "property",
              "valuation", "loan", "tranche", "income", "affordability_assessment",
              "risk_metrics", "event", "loan_case", "document", "audit_log",
              "fpre_index_history", "rate_history",
              "stress_scenario", "stress_loan_metrics", "stress_event"]
    for t in tables:
        n = fetch(con, f"SELECT COUNT(*) FROM {t}")[0][0]
        print(f"  {t:30s} {n:>10,}")

    print("\n--- FK integrity (should be 0 orphans) ---")
    orphans = [
        ("loan.primary_client_id → client",
         "SELECT COUNT(*) FROM loan l LEFT JOIN client c ON c.client_id = l.primary_client_id "
         "WHERE c.client_id IS NULL"),
        ("loan.property_id → property",
         "SELECT COUNT(*) FROM loan l LEFT JOIN property p USING(property_id) "
         "WHERE p.property_id IS NULL"),
        ("tranche.loan_id → loan",
         "SELECT COUNT(*) FROM tranche t LEFT JOIN loan l USING(loan_id) "
         "WHERE l.loan_id IS NULL"),
        ("valuation.property_id → property",
         "SELECT COUNT(*) FROM valuation v LEFT JOIN property p USING(property_id) "
         "WHERE p.property_id IS NULL"),
    ]
    for name, sql in orphans:
        n = fetch(con, sql)[0][0]
        flag = "OK" if n == 0 else f"WARN ({n})"
        print(f"  {name:50s} {flag}")

    print("\n--- Loan KPIs ---")
    avg_ltv, avg_dsti, share80, share33 = fetch(con, """
        SELECT ROUND(AVG(ltv_pct),2), ROUND(AVG(dsti_pct),2),
               SUM(CASE WHEN ltv_pct>80 THEN 1 ELSE 0 END)*1.0/COUNT(*),
               SUM(CASE WHEN dsti_pct>33 THEN 1 ELSE 0 END)*1.0/COUNT(*)
          FROM loan
    """)[0]
    print(f"  Avg LTV  : {avg_ltv}%")
    print(f"  Avg DSTI : {avg_dsti}%")
    print(f"  LTV > 80%: {share80:.2%}")
    print(f"  DSTI>33% : {share33:.2%}")

    print("\n--- LTV bucket distribution ---")
    rows = fetch(con, """
        SELECT
          SUM(CASE WHEN ltv_pct<50 THEN 1 ELSE 0 END) lt50,
          SUM(CASE WHEN ltv_pct BETWEEN 50 AND 60 THEN 1 ELSE 0 END) b50_60,
          SUM(CASE WHEN ltv_pct BETWEEN 60 AND 75 THEN 1 ELSE 0 END) b60_75,
          SUM(CASE WHEN ltv_pct BETWEEN 75 AND 80 THEN 1 ELSE 0 END) b75_80,
          SUM(CASE WHEN ltv_pct BETWEEN 80 AND 90 THEN 1 ELSE 0 END) b80_90,
          SUM(CASE WHEN ltv_pct BETWEEN 90 AND 100 THEN 1 ELSE 0 END) b90_100,
          SUM(CASE WHEN ltv_pct>100 THEN 1 ELSE 0 END) gt100,
          COUNT(*) total
        FROM loan
    """)[0]
    labels = ["<50", "50-60", "60-75", "75-80", "80-90", "90-100", ">100"]
    for lbl, val in zip(labels, rows[:7]):
        print(f"  {lbl:>7}: {val:>7,}  ({val/rows[7]:.1%})")

    print("\n--- Event status mix ---")
    for status, n in fetch(con, "SELECT status, COUNT(*) FROM event GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {status:20s} {n:>10,}")

    print("\n--- Per-canton client count (top 10) ---")
    for canton, n in fetch(con, """
        SELECT a.canton, COUNT(*) FROM client c
        JOIN address a USING(address_id) GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """):
        print(f"  {canton:6s} {n:>8,}")

    print("\n--- Stress scenarios ---")
    rows = fetch(con, "SELECT scenario_id, severity FROM stress_scenario ORDER BY 1")
    if not rows:
        print("  (none run yet — try: python scripts/run_stress.py)")
    for sid, sev in rows:
        print(f"  {sid:30s} severity={sev}")

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
