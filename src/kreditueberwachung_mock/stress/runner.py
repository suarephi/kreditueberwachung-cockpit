"""End-to-end stress runner.

run_scenario(scenario_id) → writes:
  - stress_scenario row
  - stress_index_overlay / stress_rate_overlay / stress_macro_overlay rows
  - stress_property_value (per scenario × property × period)
  - stress_loan_metrics  (per scenario × loan × period)
  - stress_event         (transitions)
  - stress_portfolio_kpi (per period)
"""
from __future__ import annotations
import datetime as dt
import sqlite3
import time
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .. import config
from . import catalog, shocks


@dataclass
class StressResult:
    scenario_id:        str
    n_loans:            int
    total_breaches:     int
    total_el_chf:       float
    runtime_s:          float


PRUDENCE_HAIRCUT = config.PRUDENCE_HAIRCUT


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _load_base_frames(con: sqlite3.Connection, sample_pct: float):
    fpre  = pd.read_sql_query("SELECT * FROM fpre_index_history", con)
    rates = pd.read_sql_query("SELECT * FROM rate_history", con)
    cur_val = pd.read_sql_query(
        "SELECT property_id, market_value, mortgage_lending_value FROM v_current_valuation",
        con,
    )
    props = pd.read_sql_query(
        "SELECT property_id, region_code, object_type FROM property",
        con,
    )
    loans = pd.read_sql_query("""
        SELECT l.loan_id, l.primary_client_id, l.household_id, l.property_id,
               l.original_amount, l.current_outstanding,
               l.first_mortgage_amount, l.second_mortgage_amount,
               l.ltv_pct, l.dsti_pct, l.origination_date, l.pillar3a_indirect_amortization
          FROM loan l
    """, con)
    if sample_pct < 1.0:
        loans = loans.sample(frac=sample_pct, random_state=config.SEED).reset_index(drop=True)
    # Household-summed income via client_household.
    incomes = pd.read_sql_query("""
        SELECT ch.household_id,
               SUM(i.gross_salary + i.bonus_avg_3y + i.rental_income + i.dividend_income +
                   i.pension_income + i.other_income + i.alimony_received - i.alimony_paid -
                   i.existing_debt_payments) AS total_income
          FROM client_household ch
          JOIN income i ON i.client_id = ch.client_id
         GROUP BY ch.household_id
    """, con)
    return fpre, rates, cur_val, props, loans, incomes


def _wipe_existing(con: sqlite3.Connection, scenario_id: str) -> None:
    cur = con.cursor()
    for t in ["stress_loan_metrics", "stress_property_value", "stress_event",
              "stress_index_overlay", "stress_rate_overlay", "stress_macro_overlay",
              "stress_portfolio_kpi", "stress_scenario"]:
        cur.execute(f"DELETE FROM {t} WHERE scenario_id = ?", (scenario_id,))
    con.commit()


def _logistic_pd(ltv, dsti, unemp_pct):
    logit = -6.0 + 8.0 * np.maximum(0, ltv - 0.67) + 12.0 * np.maximum(0, dsti - 0.33) + 0.25 * unemp_pct
    pd_ = 1 / (1 + np.exp(-logit))
    return np.clip(pd_, 0.0008, 0.35)


def run_scenario(scenario_id: str, sample_pct: float | None = None) -> StressResult:
    if sample_pct is None:
        sample_pct = config.STRESS_SAMPLE_PCT
    spec = catalog.load(scenario_id)
    rng = np.random.default_rng(spec.seed)

    started = time.time()
    con = _connect()
    try:
        _wipe_existing(con, spec.id)
        cur = con.cursor()
        cur.execute("""
            INSERT INTO stress_scenario(scenario_id, name, description, severity, horizon_quarters,
                                         start_period, narrative, source, seed, yaml_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (spec.id, spec.name, spec.narrative, spec.severity, spec.horizon_quarters,
              spec.start_period, spec.narrative, spec.source, spec.seed, spec.yaml_hash,
              dt.datetime.utcnow().isoformat()))

        fpre, rates, cur_val, props, loans, incomes = _load_base_frames(con, sample_pct)

        idx_ov, rate_ov, macro_ov = shocks.build_overlays(spec, fpre, rates)
        idx_ov.to_sql("stress_index_overlay",  con, if_exists="append", index=False, chunksize=20_000)
        rate_ov.to_sql("stress_rate_overlay",  con, if_exists="append", index=False, chunksize=20_000)
        macro_ov.to_sql("stress_macro_overlay", con, if_exists="append", index=False, chunksize=20_000)

        # --- Per-property × period stressed value ---
        # Shocks apply by (region_code, object_type, period). Build a wide period-shock array.
        periods = sorted(idx_ov["period"].unique())
        H = len(periods)
        shock_lookup = idx_ov.set_index(["region_code", "object_type", "period"])["shock_pct"].to_dict()

        # Vectorize per property.
        prop = props.merge(cur_val, on="property_id", how="inner")
        n_p = len(prop)
        shock_mat = np.zeros((n_p, H))
        for pi in range(H):
            p = periods[pi]
            shock_mat[:, pi] = [
                shock_lookup.get((r, o, p), 0.0)
                for r, o in zip(prop["region_code"], prop["object_type"])
            ]
        haircut = np.array([PRUDENCE_HAIRCUT.get(o, 0.05) for o in prop["object_type"]])[:, None]
        stressed_mv  = prop["market_value"].values[:, None] * (1 + shock_mat)
        stressed_mlv = stressed_mv * (1 - haircut)

        # Optionally write per-property × period (heavy: scenarios × properties × H rows).
        if not config.STRESS_PROPERTY_SNAPSHOT_ONLY:
            prop_rows = []
            pid_arr = prop["property_id"].values
            for k, p in enumerate(periods):
                prop_rows.append(pd.DataFrame({
                    "scenario_id":           spec.id,
                    "property_id":           pid_arr,
                    "period":                p,
                    "stressed_market_value": stressed_mv[:, k].round(0),
                    "stressed_mlv":          stressed_mlv[:, k].round(0),
                }))
            pd.concat(prop_rows, ignore_index=True).to_sql(
                "stress_property_value", con, if_exists="append", index=False, chunksize=20_000
            )

        # --- Per-loan × period metrics ---
        # Map loan_id → property index.
        prop_idx_by_pid = {pid: i for i, pid in enumerate(prop["property_id"].values)}
        loan_pidx = np.array([prop_idx_by_pid.get(p, -1) for p in loans["property_id"]])
        valid = loan_pidx >= 0
        loans = loans[valid].reset_index(drop=True)
        loan_pidx = loan_pidx[valid]

        inc_lookup = incomes.set_index("household_id")["total_income"].to_dict()
        inc_arr = np.array([max(40_000.0, inc_lookup.get(int(h), 100_000.0)) for h in loans["household_id"]])

        income_shock = spec.macro.income_shock_pct
        unemp_pct    = spec.macro.unemployment_pct
        shocked_income = inc_arr * (1.0 + income_shock)

        # Outstanding & amortization (linear).
        outstanding_now = loans["current_outstanding"].values
        annual_amort_required = np.maximum(0.0,
            (outstanding_now - prop["market_value"].values[loan_pidx] * 0.65) / config.AMORT_HORIZON_YEARS)
        # Direct amortizers reduce balance over time; indirect 3a amortizers don't.
        indirect = loans["pillar3a_indirect_amortization"].values.astype(bool)
        per_q_amort = np.where(indirect, 0.0, annual_amort_required / 4.0)

        # Stressed values per loan × period.
        stressed_mv_loan  = stressed_mv[loan_pidx]
        stressed_mlv_loan = stressed_mlv[loan_pidx]

        outstanding_q = outstanding_now[:, None] - per_q_amort[:, None] * np.arange(1, H + 1)
        outstanding_q = np.maximum(outstanding_q, 0.0)

        ltv_q = outstanding_q / np.maximum(stressed_mv_loan, 1.0)

        # Stress DSTI uses actual shocked rate (effective banking rate ≈ shocked SARON + 100 bp spread).
        applied_rate = np.zeros(H)
        for k, p in enumerate(periods):
            row = rate_ov[(rate_ov["period"] == p) & (rate_ov["rate_name"] == "SARON_3M")]
            applied_rate[k] = float(row["shocked_rate_pct"].iloc[0]) + 1.0
        interest_cost   = outstanding_q * (applied_rate / 100.0)[None, :]
        maintenance     = stressed_mv_loan * (config.MAINTENANCE_PCT / 100.0)
        amort_req_q     = annual_amort_required[:, None]
        total_cost      = interest_cost + maintenance + amort_req_q
        dsti_q          = total_cost / shocked_income[:, None]

        pd_q  = _logistic_pd(ltv_q, dsti_q, unemp_pct)
        lgd_q = np.clip(1 - 0.85 * stressed_mlv_loan / np.maximum(outstanding_q, 1.0), 0.05, 0.6)
        ead_q = outstanding_q * 1.02
        el_q  = pd_q * lgd_q * ead_q

        breach_q = ((ltv_q > 0.80) | (dsti_q > 0.33)).astype(int)
        addl_coll = np.maximum(0.0, outstanding_q - 0.80 * stressed_mlv_loan)

        # --- Persist stress_loan_metrics ---
        loan_rows = []
        loan_id_arr = loans["loan_id"].values
        for k, p in enumerate(periods):
            loan_rows.append(pd.DataFrame({
                "scenario_id":                  spec.id,
                "loan_id":                      loan_id_arr,
                "period":                       p,
                "stressed_outstanding":         outstanding_q[:, k].round(0),
                "stressed_ltv":                 (ltv_q[:, k] * 100).round(2),
                "stressed_dsti":                (dsti_q[:, k] * 100).round(2),
                "stressed_pd_1y":               pd_q[:, k].round(5),
                "stressed_lgd":                 lgd_q[:, k].round(4),
                "stressed_ead":                 ead_q[:, k].round(0),
                "stressed_expected_loss":       el_q[:, k].round(0),
                "covenant_breach_flag":         breach_q[:, k],
                "additional_collateral_required": addl_coll[:, k].round(0),
                "exposure_at_default_chf":      ead_q[:, k].round(0),
            }))
        pd.concat(loan_rows, ignore_index=True).to_sql(
            "stress_loan_metrics", con, if_exists="append", index=False, chunksize=20_000
        )

        # --- Stress events (transitions) ---
        prev_breach = np.zeros(len(loans), dtype=int)
        prev_pd_high = np.zeros(len(loans), dtype=int)
        ev_rows = []
        for k, p in enumerate(periods):
            new_breach = (breach_q[:, k] == 1) & (prev_breach == 0)
            for i in np.where(new_breach)[0]:
                kind = "ltv_trigger_breach" if ltv_q[i, k] > 0.80 else "dsti_trigger_breach"
                ev_rows.append({
                    "scenario_id": spec.id, "loan_id": int(loan_id_arr[i]), "period": p,
                    "event_type": kind, "severity": "high",
                    "narrative": f"{kind} (LTV={ltv_q[i,k]*100:.1f}%, DSTI={dsti_q[i,k]*100:.1f}%)",
                })
            new_margin = (addl_coll[:, k] > 0) & (addl_coll[:, k - 1 if k > 0 else 0] == 0)
            for i in np.where(new_margin)[0]:
                if not new_breach[i]:
                    continue
                ev_rows.append({
                    "scenario_id": spec.id, "loan_id": int(loan_id_arr[i]), "period": p,
                    "event_type": "margin_call_required", "severity": "high",
                    "narrative": f"additional_collateral={addl_coll[i,k]:,.0f} CHF",
                })
            new_watch = (pd_q[:, k] > 0.05) & (prev_pd_high == 0)
            for i in np.where(new_watch)[0]:
                ev_rows.append({
                    "scenario_id": spec.id, "loan_id": int(loan_id_arr[i]), "period": p,
                    "event_type": "watchlist_promotion", "severity": "medium",
                    "narrative": f"PD_1Y={pd_q[i,k]:.4f}",
                })
            prev_breach   = breach_q[:, k]
            prev_pd_high  = (pd_q[:, k] > 0.05).astype(int)
        if ev_rows:
            pd.DataFrame(ev_rows).to_sql("stress_event", con, if_exists="append", index=False, chunksize=20_000)

        # --- Portfolio KPIs per period ---
        kpi_rows = []
        total_outstanding = outstanding_q.sum(axis=0)
        for k, p in enumerate(periods):
            kpi_rows.append({
                "scenario_id":         spec.id,
                "period":              p,
                "total_exposure":      float(outstanding_q[:, k].sum()),
                "weighted_avg_ltv":    float((ltv_q[:, k] * outstanding_q[:, k]).sum()
                                              / max(total_outstanding[k], 1.0) * 100.0),
                "share_ltv_gt80":      float(((ltv_q[:, k] > 0.80).sum()) / max(len(loans), 1)),
                "share_dsti_gt33":     float(((dsti_q[:, k] > 0.33).sum()) / max(len(loans), 1)),
                "expected_loss_total": float(el_q[:, k].sum()),
                "npl_share":           float(((pd_q[:, k] > 0.10).sum()) / max(len(loans), 1)),
                "capital_impact_chf":  float(el_q[:, k].sum() * 1.5),
            })
        pd.DataFrame(kpi_rows).to_sql("stress_portfolio_kpi", con, if_exists="append", index=False, chunksize=2000)

        con.commit()
        return StressResult(
            scenario_id    = spec.id,
            n_loans        = int(len(loans)),
            total_breaches = int(breach_q.max(axis=1).sum()),
            total_el_chf   = float(el_q.sum()),
            runtime_s      = time.time() - started,
        )
    finally:
        con.close()


def run_all() -> list[StressResult]:
    out = []
    for sid in catalog.list_all():
        out.append(run_scenario(sid))
    return out
