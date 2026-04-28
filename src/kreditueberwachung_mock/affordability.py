"""Income, affordability assessment, risk_metrics."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from . import config, loan as loan_mod, rng as rngmod


def _segment_income_distribution(segment: str, rng: np.random.Generator, n: int) -> np.ndarray:
    """Annual gross household income (CHF) by client segment."""
    if segment == "private_banking":
        return rng.lognormal(mean=12.5, sigma=0.45, size=n).clip(180_000, 2_500_000)
    if segment == "affluent":
        return rng.lognormal(mean=11.95, sigma=0.30, size=n).clip(140_000, 600_000)
    if segment == "business":
        return rng.lognormal(mean=11.95, sigma=0.45, size=n).clip(100_000, 1_000_000)
    return rng.lognormal(mean=11.55, sigma=0.30, size=n).clip(70_000, 250_000)   # retail


def generate_incomes(clients: pd.DataFrame) -> pd.DataFrame:
    rng = rngmod.child_rng("income")
    n = len(clients)
    today_year = dt.date.today().year

    gross = np.zeros(n)
    for seg in clients["segment"].unique():
        mask = clients["segment"] == seg
        gross[mask.values] = _segment_income_distribution(seg, rng, mask.sum())

    bonus = np.where(clients["segment"].isin(["affluent", "private_banking", "business"]).values,
                     gross * rng.uniform(0.03, 0.18, n),
                     gross * rng.uniform(0.0, 0.05, n))
    rental = np.where(rng.random(n) < 0.06, rng.uniform(8_000, 60_000, n), 0.0)
    dividend = np.where(rng.random(n) < 0.10, rng.uniform(2_000, 30_000, n), 0.0)
    pension = np.where(rng.random(n) < 0.05, rng.uniform(20_000, 80_000, n), 0.0)
    other  = np.where(rng.random(n) < 0.04, rng.uniform(2_000, 25_000, n), 0.0)
    alimony_recv = np.where(rng.random(n) < 0.03, rng.uniform(6_000, 36_000, n), 0.0)
    alimony_paid = np.where(rng.random(n) < 0.03, rng.uniform(6_000, 36_000, n), 0.0)
    debt_payments = np.where(rng.random(n) < 0.08, rng.uniform(2_400, 36_000, n), 0.0)

    df = pd.DataFrame({
        "income_id":              np.arange(1, n + 1),
        "client_id":              clients["client_id"].values,
        "reporting_year":         today_year - 1,
        "gross_salary":           gross.round(0),
        "bonus_avg_3y":           bonus.round(0),
        "variable_income":        (bonus * 0.10).round(0),
        "rental_income":          rental.round(0),
        "dividend_income":        dividend.round(0),
        "pension_income":         pension.round(0),
        "other_income":           other.round(0),
        "alimony_received":       alimony_recv.round(0),
        "alimony_paid":           alimony_paid.round(0),
        "existing_debt_payments": debt_payments.round(0),
        "documented_via":         np.where(rng.random(n) < 0.65, "Lohnausweis",
                                            np.where(rng.random(n) < 0.7, "Steuererklärung", "Selbstdeklaration")),
        "currency":               "CHF",
        "confidence":             np.where(rng.random(n) < 0.85, "verified", "declared"),
    })
    return df


def total_household_income(income_row: pd.Series) -> float:
    return float(
        income_row["gross_salary"] + income_row["bonus_avg_3y"] +
        income_row["rental_income"] + income_row["dividend_income"] +
        income_row["pension_income"] + income_row["other_income"] +
        income_row["alimony_received"] - income_row["alimony_paid"] -
        income_row["existing_debt_payments"]
    )


def generate_affordability_and_risk(
    loans: pd.DataFrame,
    valuations_initial: pd.DataFrame,
    income_df: pd.DataFrame,
    households: pd.DataFrame,
    client_household: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (affordability_df, risk_metrics_df, loans_df_with_dsti)."""
    rng = rngmod.child_rng("affordability")
    today = dt.date.today()

    # Map household → list of client_ids → summed household income.
    inc_by_client = income_df.set_index("client_id")[["gross_salary", "bonus_avg_3y",
                                                       "rental_income", "dividend_income",
                                                       "pension_income", "other_income",
                                                       "alimony_received", "alimony_paid",
                                                       "existing_debt_payments"]]
    members = client_household.groupby("household_id")["client_id"].apply(list).to_dict()

    rows_aff, rows_rm = [], []
    dsti_arr = np.zeros(len(loans))
    for i, row in enumerate(loans.itertuples(index=False)):
        member_ids = members.get(int(row.household_id), [])
        if not member_ids:
            continue
        member_inc = inc_by_client.loc[member_ids].sum(axis=0)
        gross_total = float(
            member_inc["gross_salary"] + member_inc["bonus_avg_3y"] + member_inc["rental_income"]
            + member_inc["dividend_income"] + member_inc["pension_income"] + member_inc["other_income"]
            + member_inc["alimony_received"] - member_inc["alimony_paid"]
            - member_inc["existing_debt_payments"]
        )
        gross_total = max(gross_total, 30_000.0)
        market_value = float(valuations_initial.iloc[i]["market_value"])

        imputed_interest = row.original_amount * (config.IMPUTED_INTEREST_PCT / 100.0)
        maintenance      = market_value * (config.MAINTENANCE_PCT / 100.0)
        amort_required   = loan_mod.required_amortization(
            row.original_amount, market_value, row.second_mortgage_amount
        )
        total_cost       = imputed_interest + maintenance + amort_required
        dsti             = (total_cost / gross_total) * 100.0
        threshold        = config.DSTI_THRESHOLD_PCT
        if dsti <= threshold:
            pf = "pass"
            exc = None
        else:
            if rng.random() < config.EXCEPTION_APPROVAL_RATE / max(1e-3, dsti / threshold - 1):
                pf = "exception"
                exc = f"EXC-{int(rng.integers(10**5, 10**6 - 1))}"
            else:
                pf = "fail"
                exc = None
        dsti_arr[i] = dsti

        rows_aff.append({
            "assessment_id":         len(rows_aff) + 1,
            "loan_id":               int(row.loan_id),
            "assessment_date":       (today - dt.timedelta(days=int(rng.integers(0, 365)))).isoformat(),
            "imputed_interest_rate": config.IMPUTED_INTEREST_PCT,
            "maintenance_rate":      config.MAINTENANCE_PCT,
            "amortization_required": round(amort_required, 0),
            "total_cost_yearly":     round(total_cost, 0),
            "household_income_used": round(gross_total, 0),
            "dsti_calculated":       round(dsti, 2),
            "dsti_threshold":        threshold,
            "pass_fail":             pf,
            "exception_approval_id": exc,
        })

        # Risk metrics: simple PD bump from LTV/DSTI.
        ltv = row.ltv_pct / 100.0
        dsti_frac = dsti / 100.0
        logit = -6.0 + 8.0 * max(0, ltv - 0.67) + 12.0 * max(0, dsti_frac - 0.33)
        pd_1y = 1 / (1 + np.exp(-logit))
        pd_1y = float(np.clip(pd_1y, 0.0008, 0.30))
        mlv = market_value * (1.0 - config.PRUDENCE_HAIRCUT.get("EFH", 0.05))
        lgd = float(np.clip(1 - 0.85 * mlv / max(row.current_outstanding, 1.0), 0.05, 0.6))
        ead = row.current_outstanding * 1.02
        el  = pd_1y * lgd * ead
        rating = int(np.clip(round(1 + 9 * pd_1y / 0.10), 1, 10))
        watchlist = int(pd_1y > 0.04 or row.ltv_pct > 90)
        npl       = int(rng.random() < pd_1y * 0.20)
        forb      = int(rng.random() < 0.005)
        dpd       = int(rng.poisson(0.5)) if rng.random() < 0.05 else 0
        cov_breach = int(row.ltv_pct > 80 or dsti > threshold)

        rows_rm.append({
            "metric_id":            len(rows_rm) + 1,
            "loan_id":              int(row.loan_id),
            "as_of_date":           today.isoformat(),
            "pd_1y":                round(pd_1y, 5),
            "lgd":                  round(lgd, 4),
            "ead":                  round(ead, 0),
            "expected_loss":        round(el, 0),
            "rating_internal":      rating,
            "watchlist_flag":       watchlist,
            "npl_flag":             npl,
            "forbearance_flag":     forb,
            "days_past_due":        dpd,
            "covenant_breach_flag": cov_breach,
        })

    loans = loans.copy()
    loans["dsti_pct"] = np.round(dsti_arr, 2)
    return pd.DataFrame(rows_aff), pd.DataFrame(rows_rm), loans
