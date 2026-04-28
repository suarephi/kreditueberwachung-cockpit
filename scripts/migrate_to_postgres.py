#!/usr/bin/env python3
"""Migrate the demo SQLite DB into a Postgres database (e.g. Supabase).

Usage:
    DATABASE_URL='postgresql://...'  \
    SOURCE_SQLITE=output_demo/kreditueberwachung.db \
        python scripts/migrate_to_postgres.py

Steps:
    1. Read schema_pg/01_schema.sql and execute it (drops + recreates everything).
    2. For each table, copy rows from SQLite → Postgres in batches.
    3. ANALYZE.
"""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path
import sqlite3

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PG = ROOT / "schema_pg" / "01_schema.sql"

# Tables in dependency order (referenced first).
TABLES = [
    # reference
    "canton", "postal_code", "noga",
    "fpre_index_history", "rate_history",
    # core
    "address", "client", "household", "client_household", "property",
    # credit
    "valuation", "loan", "tranche", "income",
    "affordability_assessment", "risk_metrics",
    # surveillance
    "event", "loan_case", "document", "audit_log",
    # stress
    "stress_scenario", "stress_index_overlay", "stress_rate_overlay",
    "stress_macro_overlay", "stress_property_value",
    "stress_loan_metrics", "stress_event", "stress_portfolio_kpi",
]

CHUNKSIZE = 5000


def main() -> int:
    pg_url = os.environ.get("DATABASE_URL")
    if not pg_url:
        print("ERROR: set DATABASE_URL to your Postgres connection string.",
              file=sys.stderr)
        return 1
    if pg_url.startswith("postgres://"):
        pg_url = "postgresql+psycopg2://" + pg_url[len("postgres://"):]
    elif pg_url.startswith("postgresql://"):
        pg_url = "postgresql+psycopg2://" + pg_url[len("postgresql://"):]

    src_path = Path(os.environ.get("SOURCE_SQLITE",
                                    str(ROOT / "output_demo" / "kreditueberwachung.db")))
    if not src_path.exists():
        print(f"ERROR: source SQLite not found at {src_path}.", file=sys.stderr)
        print("Generate it first: KU_OUTPUT_DIR=output_demo KU_N_CLIENTS=10000 "
              "python scripts/generate.py", file=sys.stderr)
        return 1

    print(f"Source: {src_path}  ({src_path.stat().st_size / 1e6:.1f} MB)")
    print(f"Target: {pg_url.split('@')[-1]}")
    print()

    pg = create_engine(pg_url, pool_pre_ping=True, future=True)
    sqlite_conn = sqlite3.connect(str(src_path))

    # 1. Recreate schema
    schema_sql = SCHEMA_PG.read_text(encoding="utf-8")
    print("[1/3] Recreating schema…")
    t0 = time.time()
    with pg.begin() as conn:
        # SQLAlchemy doesn't like multi-statement strings via text(); use raw
        # connection's underlying driver.
        raw = conn.connection
        cur = raw.cursor()
        cur.execute(schema_sql)
        cur.close()
    print(f"      done in {time.time() - t0:.1f}s")

    # 2. Copy data per table
    print("[2/3] Copying data…")
    for t in TABLES:
        try:
            n_src = sqlite_conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except sqlite3.OperationalError:
            print(f"      • {t:30s}  (skipped: not in source)")
            continue
        if n_src == 0:
            print(f"      • {t:30s}  (empty)")
            continue
        t0 = time.time()
        copied = 0
        for chunk in pd.read_sql_query(f"SELECT * FROM {t}", sqlite_conn,
                                        chunksize=CHUNKSIZE):
            chunk.to_sql(t, pg, if_exists="append", index=False, method="multi",
                         chunksize=CHUNKSIZE)
            copied += len(chunk)
        print(f"      • {t:30s}  {copied:>8,} rows  ({time.time() - t0:5.1f}s)")

    # 3. ANALYZE
    print("[3/3] ANALYZE…")
    with pg.begin() as conn:
        conn.exec_driver_sql("ANALYZE")
    print("Done.")
    sqlite_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
