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
import io
import os
import sys
import time
from pathlib import Path
import sqlite3

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, DBAPIError

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
    # securities
    "portfolio", "position",
    # accounts (large)
    "account", "account_tx",
    # stress
    "stress_scenario", "stress_index_overlay", "stress_rate_overlay",
    "stress_macro_overlay", "stress_property_value",
    "stress_loan_metrics", "stress_event", "stress_portfolio_kpi",
]

READ_CHUNK = 50_000   # rows fetched from SQLite per outer loop
COPY_CHUNK = 25_000   # rows per COPY statement (one server roundtrip each)
MAX_RETRIES = 4       # for transient SSL / timeout errors


def _normalise_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Cast float64 columns whose non-null values are all integer-equivalent
    to pandas' nullable Int64. Required because SQLite REAL columns whose
    values are integers (or NULL) get loaded as float64 by pandas, and to_csv
    then writes '2002.0', which Postgres rejects for INTEGER columns. The
    cast is also harmless for DOUBLE PRECISION targets."""
    for col in df.select_dtypes(include="float64").columns:
        s = df[col]
        nn = s.dropna()
        if nn.empty:
            continue
        if (nn % 1 == 0).all():
            df[col] = s.astype("Int64")
    return df


def _copy_chunk(raw_conn, table: str, df: pd.DataFrame) -> None:
    """COPY one DataFrame chunk into Postgres via psycopg2 copy_expert.

    Uses CSV format with empty string = NULL. Quoting handled by pandas to_csv
    so values containing commas, quotes, or newlines round-trip correctly.
    """
    if df.empty:
        return
    df = _normalise_dtypes(df)
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)
    cols = ",".join(f'"{c}"' for c in df.columns)
    sql = (f"COPY {table} ({cols}) FROM STDIN WITH "
           "(FORMAT CSV, NULL '', QUOTE '\"', ESCAPE '\"')")
    cur = raw_conn.cursor()
    cur.copy_expert(sql, buf)
    cur.close()


def _copy_table_with_retry(pg_engine, sqlite_conn: sqlite3.Connection, table: str,
                            n_rows: int) -> tuple[int, float]:
    """Copy one table. Per-chunk transactions + retry for transient SSL drops."""
    t0 = time.time()
    copied = 0
    chunk_iter = pd.read_sql_query(f"SELECT * FROM {table}", sqlite_conn,
                                    chunksize=COPY_CHUNK)
    for chunk in chunk_iter:
        for attempt in range(MAX_RETRIES):
            try:
                with pg_engine.begin() as conn:
                    raw = conn.connection
                    # Disable any server-side statement timeout for this session.
                    cur = raw.cursor()
                    cur.execute("SET statement_timeout = 0")
                    cur.close()
                    _copy_chunk(raw, table, chunk)
                copied += len(chunk)
                break
            except (OperationalError, DBAPIError) as e:
                msg = str(e)[:160]
                if attempt + 1 == MAX_RETRIES:
                    raise
                wait = 2 ** attempt
                print(f"        retry {attempt + 1}/{MAX_RETRIES - 1} after "
                      f"{wait}s: {msg}", file=sys.stderr)
                time.sleep(wait)
                # Force fresh connection on next attempt.
                pg_engine.dispose()
    return copied, time.time() - t0


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

    # TCP keepalives keep the SSL session alive during long COPYs over Supabase
    # session pooler (which silently drops idle sockets).
    pg = create_engine(
        pg_url,
        pool_pre_ping=True,
        future=True,
        connect_args={
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "sslmode": "require",
        },
    )
    sqlite_conn = sqlite3.connect(str(src_path))

    # 1. Recreate schema
    schema_sql = SCHEMA_PG.read_text(encoding="utf-8")
    print("[1/3] Recreating schema…", flush=True)
    t0 = time.time()
    with pg.begin() as conn:
        raw = conn.connection
        cur = raw.cursor()
        cur.execute(schema_sql)
        cur.close()
    print(f"      done in {time.time() - t0:.1f}s", flush=True)

    # 2. Copy data per table — COPY FROM STDIN, per-chunk commit, retry on SSL drops
    print("[2/3] Copying data via COPY…", flush=True)
    for t in TABLES:
        try:
            n_src = sqlite_conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except sqlite3.OperationalError:
            print(f"      • {t:30s}  (skipped: not in source)", flush=True)
            continue
        if n_src == 0:
            print(f"      • {t:30s}  (empty)", flush=True)
            continue
        copied, dur = _copy_table_with_retry(pg, sqlite_conn, t, n_src)
        rate = copied / dur if dur > 0 else 0
        print(f"      • {t:30s}  {copied:>9,} rows  "
              f"({dur:6.1f}s · {rate:>7,.0f} r/s)", flush=True)

    # 3. ANALYZE
    print("[3/3] ANALYZE…", flush=True)
    with pg.begin() as conn:
        conn.exec_driver_sql("ANALYZE")
    print("Done.", flush=True)
    sqlite_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
