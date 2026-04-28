"""Loan + tranche generation."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from . import config, rng as rngmod


PRODUCT_LINE = ["eigenheim", "renditeobjekt", "baufinanzierung", "ferienobjekt"]


def _sample_ltv(rng: np.random.Generator) -> float:
    weights = np.array([w for w, _, _ in config.LTV_MIX])
    weights = weights / weights.sum()
    bucket = rng.choice(len(config.LTV_MIX), p=weights)
    _, lo, hi = config.LTV_MIX[bucket]
    return float(rng.uniform(lo, hi))


def required_amortization(loan_amount: float, market_value: float, second_amount: float) -> float:
    """Annual amortization required to bring 1st mortgage from current LTV to AMORT_TARGET_LTV
    over AMORT_HORIZON_YEARS. Plus 2nd mortgage fully amortized over the same horizon."""
    target_first = market_value * (config.AMORT_TARGET_LTV / 100.0)
    excess_first = max(0.0, (loan_amount - second_amount) - target_first)
    annual_first = excess_first / config.AMORT_HORIZON_YEARS
    annual_second = second_amount / config.AMORT_HORIZON_YEARS
    return annual_first + annual_second


def amortization_schedule(loan_amount: float, market_value: float, second_amount: float, years: int) -> list[float]:
    """Per-year remaining balance over `years` (direct amort)."""
    annual = required_amortization(loan_amount, market_value, second_amount)
    out = []
    bal = loan_amount
    for _ in range(years):
        bal = max(0.0, bal - annual)
        out.append(bal)
    return out


def _saron_rate_at(year: int) -> float:
    points = sorted(config.SARON_PATH)
    cur = points[0][1]
    for (yy, vv) in points:
        if year >= yy:
            cur = vv
    return cur


def generate_loans(
    clients: pd.DataFrame,
    households: pd.DataFrame,
    valuations_initial: pd.DataFrame,
    properties: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build loans + tranches.

    Convention: properties[i] / valuations_initial[i] / loan i+1 are aligned by row index.
    """
    rng = rngmod.child_rng("loan")
    today = dt.date.today()
    n = len(properties)

    market_values = valuations_initial["market_value"].values

    # LTV per loan, then loan amount.
    ltv = np.array([_sample_ltv(rng) for _ in range(n)])
    raw_loan = market_values * (ltv / 100.0)
    loan_amount = np.clip(raw_loan, config.LOAN_MIN, config.LOAN_MAX)
    # Recompute LTV after clamp.
    ltv_actual = (loan_amount / market_values) * 100.0

    first_amount = np.where(
        ltv_actual <= 67.0,
        loan_amount,
        market_values * 0.67,
    )
    second_amount = loan_amount - first_amount
    second_amount = np.where(second_amount < 0, 0, second_amount)

    # Origination date: 0..15 years ago, biased recent.
    age_days = np.clip(rng.exponential(scale=365 * 5, size=n).astype(int), 30, 365 * 15)
    origination_dates = [today - dt.timedelta(days=int(d)) for d in age_days]

    # Direct amort to date.
    annual_amort = np.array([
        required_amortization(loan_amount[i], market_values[i], second_amount[i])
        for i in range(n)
    ])
    years_held = np.array([(today - od).days / 365.25 for od in origination_dates])
    has_direct = rng.random(n) < 0.55           # split direct vs indirect (3a)
    amort_to_date = np.where(has_direct, annual_amort * np.minimum(years_held, config.AMORT_HORIZON_YEARS), 0.0)
    current_outstanding = np.maximum(loan_amount - amort_to_date, market_values * 0.30)

    # Pillar 3a indirect amortization pledge for indirect amort loans (~CHF 7k/y per holder × years).
    pillar3a_pledge = np.where(~has_direct, np.clip(7_000 * years_held, 0, 250_000), 0.0)
    pillar2_pledge = np.where(rng.random(n) < 0.07, rng.uniform(20_000, 150_000, n), 0.0)

    product_line = np.where(
        properties["object_type"].values == "MFH", "renditeobjekt",
        np.where(properties["object_type"].values == "Ferienwohnung", "ferienobjekt",
                 np.where(properties["construction_year"].values >= today.year - 2, "baufinanzierung",
                          "eigenheim"))
    )

    loans = pd.DataFrame({
        "loan_id":                          np.arange(1, n + 1),
        "primary_client_id":                clients["client_id"].iloc[:n].values,
        "household_id":                     households["household_id"].iloc[:n].values,
        "property_id":                      properties["property_id"].values,
        "origination_date":                 [d.isoformat() for d in origination_dates],
        "first_drawdown_date":              [d.isoformat() for d in origination_dates],
        "original_amount":                  loan_amount.round(0),
        "current_outstanding":              current_outstanding.round(0),
        "first_mortgage_amount":            first_amount.round(0),
        "second_mortgage_amount":           second_amount.round(0),
        "ltv_pct":                          ltv_actual.round(2),
        "dsti_pct":                         0.0,                         # set in affordability step
        "pillar2_pledge":                   pillar2_pledge.round(0),
        "pillar3a_pledge":                  pillar3a_pledge.round(0),
        "pillar3a_indirect_amortization":   (~has_direct).astype(int),
        "status":                           "active",
        "product_line":                     product_line,
        "currency":                         "CHF",
        "notes":                            None,
    })

    # Build tranches with realistic Swiss-style rate laddering.
    # Larger loans → more tranches (rate-risk diversification).
    tranches = []
    next_tranche_id = 1
    for i in range(n):
        outstanding = float(current_outstanding[i])
        r = rng.random()
        if outstanding < 300_000:
            # Small loans: usually 1 tranche.
            splits = [(outstanding, "saron" if r < 0.35 else "fix")]
        elif outstanding < 800_000:
            # 60 % two-tranche split, 25 % single fix, 15 % single SARON.
            if r < 0.60:
                splits = [(outstanding * 0.55, "saron"), (outstanding * 0.45, "fix")]
            elif r < 0.85:
                splits = [(outstanding, "fix")]
            else:
                splits = [(outstanding, "saron")]
        elif outstanding < 1_500_000:
            # 50 % three-tranche ladder, 35 % two-tranche, 15 % single.
            if r < 0.50:
                splits = [(outstanding * 0.30, "saron"),
                          (outstanding * 0.35, "fix"),
                          (outstanding * 0.35, "fix")]
            elif r < 0.85:
                w = rng.uniform(0.40, 0.60)
                splits = [(outstanding * w, "saron"), (outstanding * (1 - w), "fix")]
            else:
                splits = [(outstanding, "fix")]
        elif outstanding < 2_500_000:
            # 50 % three-tranche, 35 % four-tranche, 15 % two-tranche.
            if r < 0.50:
                splits = [(outstanding * 0.25, "saron"),
                          (outstanding * 0.35, "fix"),
                          (outstanding * 0.40, "fix")]
            elif r < 0.85:
                splits = [(outstanding * 0.20, "saron"),
                          (outstanding * 0.25, "fix"),
                          (outstanding * 0.25, "fix"),
                          (outstanding * 0.30, "fix")]
            else:
                w = rng.uniform(0.45, 0.60)
                splits = [(outstanding * w, "fix"), (outstanding * (1 - w), "fix")]
        else:
            # Very large (>2.5M): private-banking style, 3-4 tranches.
            if r < 0.55:
                splits = [(outstanding * 0.20, "saron"),
                          (outstanding * 0.20, "fix"),
                          (outstanding * 0.30, "fix"),
                          (outstanding * 0.30, "fix")]
            elif r < 0.90:
                splits = [(outstanding * 0.25, "saron"),
                          (outstanding * 0.35, "fix"),
                          (outstanding * 0.40, "fix")]
            else:
                splits = [(outstanding * 0.50, "fix"),
                          (outstanding * 0.50, "fix")]

        oy = origination_dates[i].year
        for amt, ttype in splits:
            if ttype == "saron":
                rate = max(0.05, _saron_rate_at(today.year) + 0.85)
                ref  = "SARON_3M"
                margin = 85
                fix = today.replace(day=1)
                reset = (fix.replace(day=1) + dt.timedelta(days=92)).isoformat()
                maturity = (today + dt.timedelta(days=365 * 1)).isoformat()
                amort_t = "indirect" if loans.loc[i, "pillar3a_indirect_amortization"] else "direct"
            else:
                # Fix tranche; pick 5y or 10y product.
                if rng.random() < 0.6:
                    spread = config.FIX_5Y_BASE_SPREAD
                    term_years = 5
                else:
                    spread = config.FIX_10Y_BASE_SPREAD
                    term_years = 10
                rate = max(0.40, _saron_rate_at(oy) + spread)
                ref = f"FIX_{term_years}Y"
                margin = int(spread * 100)
                fix = origination_dates[i]
                reset = (fix + dt.timedelta(days=365 * term_years)).isoformat()
                maturity = reset
                amort_t = "indirect" if loans.loc[i, "pillar3a_indirect_amortization"] else "direct"
            tranches.append({
                "tranche_id":                next_tranche_id,
                "loan_id":                   int(loans.loc[i, "loan_id"]),
                "tranche_type":              ttype,
                "amount":                    round(amt, 0),
                "interest_rate_pct":         round(rate, 3),
                "reference_rate":            ref,
                "margin_bp":                 margin,
                "rate_fixing_date":          fix.isoformat() if isinstance(fix, dt.date) else fix,
                "rate_reset_date":           reset,
                "maturity_date":             maturity,
                "amortization_type":         amort_t,
                "amortization_amount_yearly": round(annual_amort[i] * (amt / outstanding) if outstanding else 0, 0),
                "status":                    "active",
            })
            next_tranche_id += 1

    tranches_df = pd.DataFrame(tranches)
    return loans, tranches_df
