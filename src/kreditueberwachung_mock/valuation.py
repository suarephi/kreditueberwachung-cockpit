"""Fahrländer-style hedonic valuation + index time series + per-property history."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from . import config, reference, rng as rngmod


# ---------------------------------------------------------------------------
# FPRE-like index time series
# ---------------------------------------------------------------------------
def build_fpre_index_history() -> pd.DataFrame:
    """Quarterly index per (region_code=canton, object_type) starting INDEX_BASE_YEAR Q1 = 100.

    Trajectory: linear growth toward INDEX_GROWTH_TO_2022 by 2022-Q4, then INDEX_CORRECTION_2022_2024
    over 2023–2024, then 0 % 2025.
    """
    rng = rngmod.child_rng("fpre_index")
    cantons = reference.cantons()["canton_code"].tolist()
    object_types = [t for t, _ in config.OBJECT_TYPE_MIX]

    rows = []
    periods = []
    for y in range(config.INDEX_BASE_YEAR, config.INDEX_LAST_YEAR + 1):
        for q in range(1, 5):
            periods.append((y, q, f"{y}-Q{q}"))

    n = len(periods)
    # Build national trajectory.
    growth_q = np.zeros(n)
    pivot_2022_idx = next(i for i, (y, q, _) in enumerate(periods) if y == 2022 and q == 4)
    pivot_2024_idx = next(i for i, (y, q, _) in enumerate(periods) if y == 2024 and q == 4)
    # Up phase.
    growth_q[: pivot_2022_idx + 1] = np.linspace(0, config.INDEX_GROWTH_TO_2022, pivot_2022_idx + 1)
    # Mild correction.
    growth_q[pivot_2022_idx + 1 : pivot_2024_idx + 1] = np.linspace(
        config.INDEX_GROWTH_TO_2022,
        config.INDEX_GROWTH_TO_2022 + config.INDEX_CORRECTION_2022_2024,
        pivot_2024_idx - pivot_2022_idx,
    )
    # Flat 2025 with mild noise.
    growth_q[pivot_2024_idx + 1 :] = (
        config.INDEX_GROWTH_TO_2022 + config.INDEX_CORRECTION_2022_2024
        + np.linspace(0, 0.005, n - pivot_2024_idx - 1)
    )

    for canton in cantons:
        canton_factor = 1.0 + (reference.canton_lookup()[canton]["location_score_macro"] - 3.5) * 0.10
        for obj in object_types:
            obj_factor = {"EFH": 1.0, "ETW": 1.05, "MFH": 0.85, "Ferienwohnung": 1.20,
                          "Gewerbe": 0.7, "Bauland": 1.30}[obj]
            noise = rng.normal(0, 0.005, size=n).cumsum()
            traj = (1.0 + growth_q * canton_factor * obj_factor + noise) * 100.0
            for i, (_, _, period) in enumerate(periods):
                rows.append({
                    "region_code": canton,
                    "object_type": obj,
                    "period":      period,
                    "index_value": float(traj[i]),
                })

    df = pd.DataFrame(rows)
    df = df.sort_values(["region_code", "object_type", "period"]).reset_index(drop=True)
    df["yoy_change"] = df.groupby(["region_code", "object_type"])["index_value"].pct_change(4)
    return df


def build_rate_history() -> pd.DataFrame:
    """Daily reference-rate history (sparse: monthly is fine for our purposes, stored per-month-end)."""
    rows = []
    points = sorted(config.SARON_PATH)
    start = dt.date(points[0][0], 1, 1)
    end   = dt.date(config.INDEX_LAST_YEAR, 12, 31)
    days = (end - start).days
    saron = []
    cur_y, cur_v = points[0]
    for d in range(0, days, 30):
        date = start + dt.timedelta(days=d)
        for (yy, vv) in points:
            if date.year >= yy:
                cur_v = vv
        saron.append((date.isoformat(), cur_v))

    for date_iso, v in saron:
        rows.append({"rate_date": date_iso, "rate_name": "SARON_3M",   "rate_pct": v})
        rows.append({"rate_date": date_iso, "rate_name": "SARON_COMP", "rate_pct": v + 0.05})
        rows.append({"rate_date": date_iso, "rate_name": "FIX_5Y",     "rate_pct": v + config.FIX_5Y_BASE_SPREAD})
        rows.append({"rate_date": date_iso, "rate_name": "FIX_10Y",    "rate_pct": v + config.FIX_10Y_BASE_SPREAD})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Hedonic valuation
# ---------------------------------------------------------------------------
def _per_sqm_base(canton_code: str, object_type: str) -> float:
    c = reference.canton_lookup()[canton_code]
    if object_type == "EFH":
        return c["base_chf_per_sqm_efh"]
    if object_type == "ETW":
        return c["base_chf_per_sqm_etw"]
    if object_type == "MFH":
        return c["base_chf_per_sqm_mfh"]
    if object_type == "Ferienwohnung":
        return c["base_chf_per_sqm_etw"] * 1.20
    if object_type == "Gewerbe":
        return c["base_chf_per_sqm_mfh"] * 0.85
    return c["base_chf_per_sqm_efh"]


def _age_factor(constr_year: int, last_reno: int, today_year: int) -> float:
    age = max(0, today_year - constr_year)
    last = constr_year if last_reno == 0 else last_reno
    eff_age = max(0, today_year - last)
    return -0.0035 * age + 0.0025 * (age - eff_age) - 0.001 * eff_age


def _geak_factor(geak: str) -> float:
    return {"A": 0.05, "B": 0.03, "C": 0.01, "D": 0.0, "E": -0.02, "F": -0.05, "G": -0.08}[geak]


def hedonic_market_value(
    rng: np.random.Generator,
    canton_code: str,
    object_type: str,
    living_area: float,
    constr_year: int,
    last_reno: int,
    micro_score: float,
    macro_score: float,
    geak: str,
    today_year: int,
    plot_area: float = 0.0,
) -> float:
    base = _per_sqm_base(canton_code, object_type)
    if object_type == "Bauland":
        # Bauland priced per sqm of plot, much lower than improved.
        return float(plot_area * base * 0.20 * (1 + rng.normal(0, 0.10)))
    age_f = _age_factor(constr_year, last_reno, today_year)
    micro_f = (micro_score - 3.5) * 0.05
    macro_f = (macro_score - 3.5) * 0.05
    geak_f = _geak_factor(geak)
    noise  = rng.normal(0, 0.07)
    val = base * living_area * (1 + age_f) * (1 + micro_f) * (1 + macro_f) * (1 + geak_f) * (1 + noise)
    return max(150_000.0, float(val))


def clamp_price_to_range(val: float) -> float:
    return float(np.clip(val, config.PRICE_MIN, config.PRICE_MAX))


def value_properties_initial(properties: pd.DataFrame) -> pd.DataFrame:
    """Compute first valuation per property + set property.purchase_price.

    Returns a DataFrame of valuations (with valuation_id starting at 1).
    """
    rng = rngmod.child_rng("valuation_initial")
    today = dt.date.today()
    today_year = today.year

    market_values = np.zeros(len(properties))
    for i, row in enumerate(properties.itertuples(index=False)):
        market_values[i] = clamp_price_to_range(hedonic_market_value(
            rng,
            row.region_code,
            row.object_type,
            row.living_area_sqm,
            int(row.construction_year),
            int(row.last_renovation_year),
            row.micro_location_score,
            row.macro_location_score,
            row.geak_class,
            today_year,
            row.plot_area_sqm,
        ))

    haircuts = np.array([config.PRUDENCE_HAIRCUT.get(t, 0.05) for t in properties["object_type"]])
    mlv = market_values * (1.0 - haircuts)

    properties["purchase_price"] = market_values.round(0)

    valuations = pd.DataFrame({
        "valuation_id":           np.arange(1, len(properties) + 1),
        "property_id":            properties["property_id"].values,
        "valuation_date":         properties["purchase_date"].values,
        "valuation_method":       "FPRE_AVM",
        "market_value":           market_values.round(0),
        "mortgage_lending_value": mlv.round(0),
        "confidence_band_low":    (market_values * 0.93).round(0),
        "confidence_band_high":   (market_values * 1.07).round(0),
        "micro_score":            properties["micro_location_score"].values,
        "macro_score":            properties["macro_location_score"].values,
        "is_current":             0,
        "valuator_id":            "FPRE-SYS",
        "valuator_name":          "FPRE Hedonic Engine v3",
        "notes":                  None,
    })
    return valuations


def value_properties_history(
    properties: pd.DataFrame,
    initial: pd.DataFrame,
    fpre_index: pd.DataFrame,
    n_extra: int = 4,
) -> pd.DataFrame:
    """Add `n_extra` follow-up valuations per property using the index history.

    Last one is flagged is_current=1.
    """
    rng = rngmod.child_rng("valuation_history")
    today = dt.date.today()

    idx_lookup = fpre_index.set_index(["region_code", "object_type", "period"])["index_value"].to_dict()

    rows = []
    next_val_id = int(initial["valuation_id"].max()) + 1
    for i, prop in enumerate(properties.itertuples(index=False)):
        purchase_date = dt.date.fromisoformat(prop.purchase_date)
        purchase_period = f"{purchase_date.year}-Q{(purchase_date.month - 1)//3 + 1}"
        base_idx = idx_lookup.get((prop.region_code, prop.object_type, purchase_period))
        if base_idx is None:
            continue
        purchase_mv = float(initial.iloc[i]["market_value"])
        # Generate n_extra evenly spaced quarterly revaluations after purchase.
        delta_days = (today - purchase_date).days
        if delta_days < 365:
            stops = []
        else:
            stops = list(np.linspace(180, delta_days, n_extra).astype(int))
        for k, off in enumerate(stops):
            d = purchase_date + dt.timedelta(days=int(off))
            period = f"{d.year}-Q{(d.month - 1)//3 + 1}"
            cur_idx = idx_lookup.get((prop.region_code, prop.object_type, period), base_idx)
            mv = purchase_mv * (cur_idx / base_idx) * (1 + rng.normal(0, 0.02))
            mv = clamp_price_to_range(mv)
            mlv = mv * (1.0 - config.PRUDENCE_HAIRCUT.get(prop.object_type, 0.05))
            rows.append({
                "valuation_id":           next_val_id,
                "property_id":            int(prop.property_id),
                "valuation_date":         d.isoformat(),
                "valuation_method":       "FPRE_AVM" if rng.random() < 0.85 else "internal_AVM",
                "market_value":           round(mv, 0),
                "mortgage_lending_value": round(mlv, 0),
                "confidence_band_low":    round(mv * 0.93, 0),
                "confidence_band_high":   round(mv * 1.07, 0),
                "micro_score":            prop.micro_location_score,
                "macro_score":            prop.macro_location_score,
                "is_current":             1 if k == len(stops) - 1 else 0,
                "valuator_id":            "FPRE-SYS",
                "valuator_name":          "FPRE Hedonic Engine v3",
                "notes":                  None,
            })
            next_val_id += 1
    history = pd.DataFrame(rows)
    if history.empty:
        # No properties old enough for a revaluation: tag the initial valuations as current.
        return history
    return history


def mark_initial_as_current_if_no_history(
    initial: pd.DataFrame, history: pd.DataFrame
) -> pd.DataFrame:
    """For properties with no history rows, mark their initial valuation as current."""
    if history.empty:
        initial["is_current"] = 1
        return initial
    has_history = set(history["property_id"].unique())
    initial.loc[~initial["property_id"].isin(has_history), "is_current"] = 1
    return initial
