"""End-to-end orchestrator: build tables in memory, then bulk-insert to SQLite + dump CSVs."""
from __future__ import annotations
import contextlib
import sqlite3
import time
import pandas as pd
import numpy as np
from . import config, reference, valuation, rng as rngmod
from . import people as people_mod
from . import property as property_mod
from . import loan as loan_mod
from . import affordability as aff_mod
from . import events as events_mod
from . import cases as cases_mod
from . import documents as docs_mod
from . import audit as audit_mod
from . import inconsistencies as inc_mod
from . import securities as securities_mod
from . import transactions as tx_mod
from . import events as events_mod
from . import dunning as dunning_mod


# Property fields that only make sense for buildings, never for raw land.
BAULAND_NULL_COLS = (
    "construction_year", "last_renovation_year", "living_area_sqm", "rooms",
    "bathrooms", "heating_type", "heating_year", "geak_class",
    "building_insurance_value",
)


def _fill_rental_income(properties: pd.DataFrame, val_initial: pd.DataFrame) -> None:
    """Populate property.annual_rental_income_chf for income-producing real estate.

    For Gewerbe/owner_occupied the figure stands in for an EBITDA proxy used by the
    affordability cashflow basis (the bank looks at the company, not the salary).
    """
    rng = rngmod.child_rng("rental_income")
    mv = val_initial.set_index("property_id")["market_value"]
    out = np.full(len(properties), np.nan)
    for i, row in enumerate(properties.itertuples(index=False)):
        ot = row.object_type
        m = float(mv.get(int(row.property_id), np.nan))
        if not np.isfinite(m):
            continue
        if ot == "MFH":
            yld = float(rng.uniform(0.040, 0.055))
            vac = float(rng.uniform(0.02, 0.05))
            out[i] = round(m * yld * (1 - vac), 0)
        elif ot == "Gewerbe":
            cu = getattr(row, "commercial_use", None)
            if cu == "owner_occupied":
                out[i] = round(m * float(rng.uniform(0.08, 0.15)), 0)
            else:
                yld = float(rng.uniform(0.050, 0.070))
                vac = float(rng.uniform(0.05, 0.12))
                out[i] = round(m * yld * (1 - vac), 0)
    properties["annual_rental_income_chf"] = out


def _accounts_to_events_and_affordability(
    material_changes: pd.DataFrame,
    events: pd.DataFrame,
    affordability: pd.DataFrame,
    loans: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Treat the account-tx material changes as monitoring signals: append the
    corresponding event records (income_drop, employer_change, divorce_indicator,
    third_pillar_payout) and re-run the tragbarkeit calculation with the
    post-change income. If the new DSTI breaches the threshold, also append a
    covenant_breach_dsti event.

    Only households whose original income_basis is the salary one ('Lohnausweis
    Haushalt') get an affordability re-check. MFH/Gewerbe loans use rental
    cashflow and are unaffected by salary anomalies."""
    import datetime as dt
    if material_changes is None or material_changes.empty:
        return events, affordability

    DSTI_THRESHOLD = config.DSTI_THRESHOLD_PCT
    EVENT_FOR = {
        "salary_loss":     ("income_drop",          None),     # severity below
        "employer_change": ("employer_change",      "low"),
        "divorce":         ("divorce_indicator",    "medium"),
        "3a_payout":       ("third_pillar_payout",  "low"),
    }
    loans_by_client = loans.groupby("primary_client_id").first()
    aff_by_loan = affordability.set_index("loan_id")
    next_event_id = (int(events["event_id"].max()) + 1) if not events.empty else 1
    next_aff_id = (int(affordability["assessment_id"].max()) + 1) if not affordability.empty else 1
    new_events: list[dict] = []
    new_aff: list[dict] = []

    for _, mc in material_changes.iterrows():
        cid = int(mc["client_id"])
        if cid not in loans_by_client.index:
            continue
        loan = loans_by_client.loc[cid]
        loan_id = int(loan["loan_id"])
        change_type = mc["change_type"]
        change_date = mc["change_date"]
        change_dt = dt.date.fromisoformat(change_date)

        spec = EVENT_FOR.get(change_type)
        if spec:
            etype, sev_override = spec
            if etype == "income_drop":
                sev = "high" if int(mc["gap_months"]) >= 3 else "medium"
            else:
                sev = sev_override
            base_days, basis = events_mod.SLA_DAYS_BY_TYPE.get(etype, (30, "RM-Antrag (Default)"))
            sla_days = max(1, int(round(base_days * events_mod.SEV_MULT[sev])))
            detected = change_dt + dt.timedelta(days=5)
            new_events.append({
                "event_id":       next_event_id,
                "loan_id":        loan_id,
                "client_id":      cid,
                "property_id":    int(loan["property_id"]),
                "event_type":     etype,
                "event_subtype":  None,
                "severity":       sev,
                "source":         "system",
                "detected_at":    detected.isoformat(),
                "occurred_at":    change_date,
                "title":          etype.replace("_", " ").capitalize() + " (Tx-Anomalie)",
                "description":    f"Auto-erkannt aus Kontobewegungen: {change_type}",
                "status":         "open",
                "assigned_to":    f"OFFICER-{(loan_id % 60) + 1}",
                "resolved_at":    None,
                "sla_due_date":   (detected + dt.timedelta(days=sla_days)).isoformat(),
                "sla_basis":      basis,
                "linked_case_id": None,
            })
            next_event_id += 1

        if change_type in ("salary_loss", "employer_change") and loan_id in aff_by_loan.index:
            aff_row = aff_by_loan.loc[loan_id]
            if isinstance(aff_row, pd.DataFrame):
                aff_row = aff_row.iloc[0]
            if str(aff_row.get("income_basis", "")) != "Lohnausweis Haushalt":
                continue
            old_income = float(aff_row["household_income_used"])
            factor = float(mc["salary_factor_after"])
            # Salary_loss with multi-month gap: weight in the zero months.
            gap = int(mc["gap_months"])
            effective_factor = factor
            if change_type == "salary_loss" and gap > 0:
                # Annualised income after gap = factor * salary; if a long gap
                # is recent the trailing-12m view is ~factor; if older just factor.
                effective_factor = factor
            new_income = max(old_income * effective_factor, 30_000.0)
            cost = float(aff_row["total_cost_yearly"])
            new_dsti = (cost / new_income) * 100.0
            pf = "fail" if new_dsti > DSTI_THRESHOLD else "pass"
            new_aff.append({
                "assessment_id":         next_aff_id,
                "loan_id":               loan_id,
                "assessment_date":       (change_dt + dt.timedelta(days=30)).isoformat(),
                "imputed_interest_rate": float(aff_row["imputed_interest_rate"]),
                "maintenance_rate":      float(aff_row["maintenance_rate"]),
                "amortization_required": float(aff_row["amortization_required"]),
                "total_cost_yearly":     round(cost, 0),
                "household_income_used": round(new_income, 0),
                "income_basis":          "Lohnausweis Haushalt (Recheck nach Tx-Anomalie)",
                "dsti_calculated":       round(new_dsti, 2),
                "dsti_threshold":        DSTI_THRESHOLD,
                "pass_fail":             pf,
                "exception_approval_id": None,
            })
            next_aff_id += 1
            if pf == "fail":
                base_days, basis = events_mod.SLA_DAYS_BY_TYPE.get(
                    "covenant_breach_dsti", (30, "SBVg-Selbstregulierung"))
                sla_days = max(1, int(round(base_days * events_mod.SEV_MULT["high"])))
                detected = change_dt + dt.timedelta(days=10)
                new_events.append({
                    "event_id":       next_event_id,
                    "loan_id":        loan_id,
                    "client_id":      cid,
                    "property_id":    int(loan["property_id"]),
                    "event_type":     "covenant_breach_dsti",
                    "event_subtype":  None,
                    "severity":       "high",
                    "source":         "system",
                    "detected_at":    detected.isoformat(),
                    "occurred_at":    change_date,
                    "title":          "Tragbarkeit nach Lohnausfall überschritten",
                    "description":    f"DSTI nach Tx-Anomalie ({change_type}): {new_dsti:.1f}% > {DSTI_THRESHOLD}%",
                    "status":         "open",
                    "assigned_to":    f"OFFICER-{(loan_id % 60) + 1}",
                    "resolved_at":    None,
                    "sla_due_date":   (detected + dt.timedelta(days=sla_days)).isoformat(),
                    "sla_basis":      basis,
                    "linked_case_id": None,
                })
                next_event_id += 1

    if new_events:
        events = pd.concat([events, pd.DataFrame(new_events)], ignore_index=True)
    if new_aff:
        affordability = pd.concat([affordability, pd.DataFrame(new_aff)], ignore_index=True)
    return events, affordability


def _apply_ifrs9_staging(rm: pd.DataFrame, events: pd.DataFrame,
                          dunning: pd.DataFrame) -> pd.DataFrame:
    """Compute IFRS 9 stage (1/2/3) and lifetime ECL per loan.

    Stage 3 (credit-impaired):
      - npl_flag = 1
      - days_past_due > 90
      - forbearance_flag = 1
      - dunning step ≥ 3 (Bonitätsentscheid or Verwertung)

    Stage 2 (Significant Increase in Credit Risk):
      - watchlist_flag = 1
      - days_past_due > 30
      - covenant_breach_flag = 1
      - any open income_drop / employer_change / covenant_breach_dsti event
      - dunning step 1 or 2

    Stage 1 (performing):
      - everything else.

    Lifetime EL:
      Stage 1: 12-mo ECL (= existing expected_loss)
      Stage 2: 1 - (1 - pd_1y)^7 lifetime PD over 7-year residual life × LGD × EAD
      Stage 3: 1.0 × LGD × EAD
    """
    if rm is None or rm.empty:
        return rm

    # Open events that count as SICR triggers
    sicr_event_loans: set[int] = set()
    if events is not None and not events.empty:
        mask = events["event_type"].isin([
            "income_drop", "employer_change", "covenant_breach_dsti",
            "covenant_breach_ltv", "property_value_drop_>10%", "betreibung_recorded",
        ]) & events["status"].isin(["open", "in_progress", "escalated"])
        sicr_event_loans = set(events.loc[mask, "loan_id"].astype(int).tolist())

    # Dunning levels: collect highest open step per loan
    dunning_max_step: dict[int, int] = {}
    if dunning is not None and not dunning.empty:
        active = dunning[dunning["status"].isin(["open", "escalated"])]
        for loan_id, grp in active.groupby("loan_id"):
            dunning_max_step[int(loan_id)] = int(grp["step"].max())

    stages: list[int] = []
    reasons: list[str] = []
    lifetime_el: list[float] = []
    for _, r in rm.iterrows():
        loan_id = int(r["loan_id"])
        pd_1y = float(r["pd_1y"])
        lgd = float(r["lgd"])
        ead = float(r["ead"])
        max_step = dunning_max_step.get(loan_id, 0)

        # Stage 3 first
        stage3_reasons = []
        if int(r.get("npl_flag", 0)) == 1:
            stage3_reasons.append("NPL-Flag")
        if int(r.get("days_past_due", 0)) > 90:
            stage3_reasons.append("> 90 Tage überfällig")
        if int(r.get("forbearance_flag", 0)) == 1:
            stage3_reasons.append("Forbearance")
        if max_step >= 3:
            stage3_reasons.append(f"Mahnstufe {max_step}")
        if stage3_reasons:
            stages.append(3)
            reasons.append(", ".join(stage3_reasons))
            lifetime_el.append(round(lgd * ead, 0))
            continue

        # Stage 2 (SICR) next
        stage2_reasons = []
        if int(r.get("watchlist_flag", 0)) == 1:
            stage2_reasons.append("Beobachtungsliste")
        if int(r.get("days_past_due", 0)) > 30:
            stage2_reasons.append("> 30 Tage überfällig")
        if int(r.get("covenant_breach_flag", 0)) == 1:
            stage2_reasons.append("Covenant-Verletzung")
        if loan_id in sicr_event_loans:
            stage2_reasons.append("SICR-Event")
        if max_step in (1, 2):
            stage2_reasons.append(f"Mahnstufe {max_step}")
        if stage2_reasons:
            stages.append(2)
            reasons.append(", ".join(stage2_reasons))
            # Lifetime PD = 1 - (1 - pd_1y)^7 (7-year residual approximation)
            lifetime_pd = 1.0 - (1.0 - pd_1y) ** 7
            lifetime_el.append(round(lifetime_pd * lgd * ead, 0))
            continue

        # Stage 1
        stages.append(1)
        reasons.append("")
        lifetime_el.append(round(float(r.get("expected_loss", pd_1y * lgd * ead)), 0))

    rm = rm.copy()
    rm["ifrs9_stage"] = stages
    rm["ifrs9_sicr_reason"] = reasons
    rm["lifetime_el"] = lifetime_el
    return rm


def _null_bauland_fields(properties: pd.DataFrame) -> None:
    """Erase building-only attributes for Bauland rows so the dossier doesn't pretend
    a piece of land has rooms, heating, or a construction year."""
    bauland_mask = properties["object_type"] == "Bauland"
    if not bauland_mask.any():
        return
    for col in BAULAND_NULL_COLS:
        if col not in properties.columns:
            continue
        properties[col] = properties[col].astype(object)
        properties.loc[bauland_mask, col] = None


SCHEMA_FILES = [
    "001_reference.sql",
    "002_core.sql",
    "003_credit.sql",
    "004_surveillance.sql",
    "005_views.sql",
    "006_stress.sql",
    "007_securities.sql",
    "008_accounts.sql",
    "009_dunning.sql",
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

        with _step("rental_income_fill"):
            _fill_rental_income(properties, val_initial)

        with _step("loans_and_tranches"):
            loans, tranches = loan_mod.generate_loans(clients_df, households, val_initial, properties)

        with _step("incomes"):
            incomes = aff_mod.generate_incomes(clients_df)
        with _step("affordability_risk"):
            aff, rm, loans = aff_mod.generate_affordability_and_risk(
                loans, val_initial, incomes, households, client_household, properties
            )

        with _step("events"):
            events = events_mod.generate_events(loans, rm)
        with _step("cases"):
            cases = cases_mod.generate_cases(loans, events)
        with _step("documents"):
            docs = docs_mod.generate_documents(clients_df, loans, properties)
        with _step("audit_log"):
            audit = audit_mod.generate_audit_log(clients_df)
        with _step("securities"):
            portfolios, positions = securities_mod.generate_portfolios(clients_df)
        with _step("accounts_and_tx"):
            accounts, account_tx, material_changes = tx_mod.generate_accounts_and_tx(
                clients_df, incomes, loans, properties
            )

        with _step("tx_to_events_affordability"):
            events, aff = _accounts_to_events_and_affordability(
                material_changes, events, aff, loans
            )

        with _step("dunning"):
            dunning = dunning_mod.generate_dunning_steps(loans, events, rm)

        with _step("ifrs9_staging"):
            rm = _apply_ifrs9_staging(rm, events, dunning)

        addresses_all = pd.concat([addr_clients, addr_property], ignore_index=True)

        with _step("bauland_cleanup"):
            _null_bauland_fields(properties)

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

        with _step("bulk insert securities"):
            _bulk_insert(con, "portfolio",              portfolios)
            _bulk_insert(con, "position",               positions)

        with _step("bulk insert accounts"):
            _bulk_insert(con, "account",                accounts)
            _bulk_insert(con, "account_tx",             account_tx, chunksize=20_000)

        with _step("bulk insert dunning"):
            _bulk_insert(con, "dunning_step",           dunning)

        with _step("dump CSVs"):
            for name, df in {
                "client": clients_df, "address": addresses_all, "household": households,
                "client_household": client_household, "property": properties,
                "valuation": valuations_all, "loan": loans, "tranche": tranches,
                "income": incomes, "affordability_assessment": aff, "risk_metrics": rm,
                "event": events, "case": cases, "document": docs, "audit_log": audit,
                "fpre_index_history": fpre, "rate_history": rates,
                "portfolio": portfolios, "position": positions,
                "account": accounts, "account_tx": account_tx,
                "dunning_step": dunning,
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
        "portfolio", "position", "account", "account_tx", "dunning_step",
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
