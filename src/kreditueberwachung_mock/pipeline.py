"""End-to-end orchestrator: build tables in memory, then bulk-insert to SQLite + dump CSVs."""
from __future__ import annotations
import contextlib
import sqlite3
import time
import pandas as pd
from . import config, reference, valuation
from . import people as people_mod
from . import property as property_mod
from . import loan as loan_mod
from . import affordability as aff_mod
from . import events as events_mod
from . import cases as cases_mod
from . import documents as docs_mod
from . import audit as audit_mod
from . import inconsistencies as inc_mod


SCHEMA_FILES = [
    "001_reference.sql",
    "002_core.sql",
    "003_credit.sql",
    "004_surveillance.sql",
    "005_views.sql",
    "006_stress.sql",
]


@contextlib.contextmanager
def _connect():
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.CSV_DIR.mkdir(parents=True, exist_ok=True)
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    con = sqlite3.connect(config.DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous = NORMAL")
    try:
        yield con
    finally:
        con.commit()
        con.close()


def _load_schema(con: sqlite3.Connection) -> None:
    for name in SCHEMA_FILES:
        sql = (config.SCHEMA_DIR / name).read_text(encoding="utf-8")
        con.executescript(sql)
    con.commit()


def _load_reference(con: sqlite3.Connection) -> None:
    cantons = reference.cantons()
    cantons.to_sql("canton", con, if_exists="append", index=False)
    plz = reference.postal_codes()
    plz.to_sql("postal_code", con, if_exists="append", index=False)
    noga = reference.noga()
    noga.to_sql("noga", con, if_exists="append", index=False)
    con.commit()


def _bulk_insert(con, table: str, df: pd.DataFrame, chunksize: int = 10_000) -> None:
    if df is None or df.empty:
        return
    df.to_sql(table, con, if_exists="append", index=False, chunksize=chunksize)


def _step(label: str):
    @contextlib.contextmanager
    def _wrap():
        start = time.time()
        print(f"[{label}] starting", flush=True)
        yield
        print(f"[{label}] done in {time.time() - start:.1f}s", flush=True)
    return _wrap()


def run() -> None:
    inc_mod.reset_log()
    n = config.N_CLIENTS

    with _connect() as con:
        with _step("schema"):
            _load_schema(con)
        with _step("reference"):
            _load_reference(con)

        with _step("clients"):
            clients_df, addr_clients = people_mod.generate_clients_and_addresses(n)
        with _step("households"):
            households, client_household = people_mod.generate_households(clients_df)

        # ~95 % of clients carry a loan; pick contiguous subset.
        n_loans = int(round(n * config.SHARE_WITH_LOAN))
        with _step("properties"):
            properties, addr_property = property_mod.generate_properties(
                n_loans, address_offset=n + 1
            )
        with _step("fpre_index"):
            fpre = valuation.build_fpre_index_history()
            rates = valuation.build_rate_history()

        with _step("valuations_initial"):
            val_initial = valuation.value_properties_initial(properties)
        with _step("valuations_history"):
            val_history = valuation.value_properties_history(properties, val_initial, fpre, n_extra=4)
            val_initial = valuation.mark_initial_as_current_if_no_history(val_initial, val_history)
        valuations_all = pd.concat([val_initial, val_history], ignore_index=True)
        valuations_all["valuation_id"] = range(1, len(valuations_all) + 1)

        with _step("loans_and_tranches"):
            loans, tranches = loan_mod.generate_loans(clients_df, households, val_initial, properties)

        with _step("incomes"):
            incomes = aff_mod.generate_incomes(clients_df)
        with _step("affordability_risk"):
            aff, rm, loans = aff_mod.generate_affordability_and_risk(
                loans, val_initial, incomes, households, client_household
            )

        with _step("events"):
            events = events_mod.generate_events(loans, rm)
        with _step("cases"):
            cases = cases_mod.generate_cases(loans, events)
        with _step("documents"):
            docs = docs_mod.generate_documents(clients_df, loans, properties)
        with _step("audit_log"):
            audit = audit_mod.generate_audit_log(clients_df)

        addresses_all = pd.concat([addr_clients, addr_property], ignore_index=True)

        with _step("inconsistencies"):
            tables = {
                "client":        clients_df,
                "address":       addresses_all,
                "income":        incomes,
                "household":     households,
                "loan":          loans,
                "tranche":       tranches,
                "valuation":     valuations_all,
                "property":      properties,
                "event":         events,
                "case":          cases,
                "document":      docs,
                "audit_log":     audit,
                "client_household": client_household,
            }
            inc_mod.apply_inconsistencies(tables)

        with _step("write fpre+rate ref"):
            fpre.to_sql("fpre_index_history", con, if_exists="append", index=False, chunksize=20_000)
            rates.to_sql("rate_history", con, if_exists="append", index=False, chunksize=20_000)

        with _step("bulk insert core"):
            _bulk_insert(con, "address",                addresses_all)
            _bulk_insert(con, "client",                 clients_df)
            _bulk_insert(con, "household",              households)
            _bulk_insert(con, "client_household",       client_household)
            _bulk_insert(con, "property",               properties)

        with _step("bulk insert credit"):
            _bulk_insert(con, "valuation",              valuations_all)
            _bulk_insert(con, "loan",                   loans)
            _bulk_insert(con, "tranche",                tranches)
            _bulk_insert(con, "income",                 incomes)
            _bulk_insert(con, "affordability_assessment", aff)
            _bulk_insert(con, "risk_metrics",           rm)

        with _step("bulk insert surveillance"):
            _bulk_insert(con, "event",                  events)
            _bulk_insert(con, "loan_case",              cases)
            _bulk_insert(con, "document",               docs)
            _bulk_insert(con, "audit_log",              audit)

        with _step("dump CSVs"):
            for name, df in {
                "client": clients_df, "address": addresses_all, "household": households,
                "client_household": client_household, "property": properties,
                "valuation": valuations_all, "loan": loans, "tranche": tranches,
                "income": incomes, "affordability_assessment": aff, "risk_metrics": rm,
                "event": events, "case": cases, "document": docs, "audit_log": audit,
                "fpre_index_history": fpre, "rate_history": rates,
            }.items():
                df.to_csv(config.CSV_DIR / f"{name}.csv", index=False)

        with _step("vacuum/analyze"):
            con.commit()
            con.execute("PRAGMA journal_mode = DELETE")
            con.execute("ANALYZE")
            con.execute("VACUUM")

        inc_mod.write_catalog(config.OUTPUT_DIR / "data_quality_issues.md")
        _write_stats(con)


def _write_stats(con: sqlite3.Connection) -> None:
    """Tiny stats.md with row counts and a few KPI snapshots."""
    cur = con.cursor()
    tables = [
        "canton", "postal_code", "noga", "fpre_index_history", "rate_history",
        "address", "client", "household", "client_household", "property",
        "valuation", "loan", "tranche", "income", "affordability_assessment",
        "risk_metrics", "event", "loan_case", "document", "audit_log",
    ]
    rows = []
    for t in tables:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        rows.append((t, n))
    kpi = cur.execute("""
        SELECT ROUND(AVG(ltv_pct),2), ROUND(AVG(dsti_pct),2),
               SUM(CASE WHEN ltv_pct>80 THEN 1 ELSE 0 END)*1.0/COUNT(*),
               SUM(CASE WHEN dsti_pct>33 THEN 1 ELSE 0 END)*1.0/COUNT(*)
          FROM loan
    """).fetchone()
    open_events = cur.execute("""
        SELECT status, COUNT(*) FROM event GROUP BY status ORDER BY 2 DESC
    """).fetchall()

    lines = ["# Stats — base dataset\n", "## Row counts\n"]
    lines += ["| Table | Rows |", "|---|---:|"]
    for t, n in rows:
        lines.append(f"| `{t}` | {n:,} |")
    lines += ["\n## Loan KPIs\n",
              f"- Avg LTV: **{kpi[0]} %**",
              f"- Avg DSTI: **{kpi[1]} %**",
              f"- Share LTV > 80 %: **{kpi[2]:.2%}**",
              f"- Share DSTI > 33 %: **{kpi[3]:.2%}**",
              "\n## Event-status mix\n",
              "| Status | Count |", "|---|---:|"]
    for s, n in open_events:
        lines.append(f"| `{s}` | {n:,} |")
    (config.OUTPUT_DIR / "stats.md").write_text("\n".join(lines), encoding="utf-8")
