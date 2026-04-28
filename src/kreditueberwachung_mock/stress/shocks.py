"""Build the index/rate/macro overlay tables for a scenario."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from .. import config, reference
from .catalog import ScenarioSpec


def _periods(start: str, n: int) -> list[str]:
    y, q = int(start.split("-Q")[0]), int(start.split("-Q")[1])
    out = []
    for _ in range(n):
        out.append(f"{y}-Q{q}")
        q += 1
        if q > 4:
            q = 1
            y += 1
    return out


def _shape_array(shape: str, n: int, total: float) -> np.ndarray:
    """Cumulative shock per quarter, ending at `total` after n quarters."""
    if shape == "frontload":
        # 60 % in first 4 quarters, then taper.
        base = np.linspace(0.0, 1.0, n) ** 0.5
    elif shape == "u_shape":
        x = np.linspace(0, 1, n)
        base = -np.cos(np.pi * x) / 2 + 0.5    # 0..1, slow start, recovery taper
    else:
        base = np.linspace(0.0, 1.0, n)
    return base * total


def build_overlays(spec: ScenarioSpec, fpre: pd.DataFrame, rates: pd.DataFrame):
    """Return three DataFrames: index_overlay, rate_overlay, macro_overlay."""
    periods = _periods(spec.start_period, spec.horizon_quarters)
    cantons = reference.cantons()["canton_code"].tolist()
    object_types = [t for t, _ in config.OBJECT_TYPE_MIX]

    # --- INDEX OVERLAY ---
    cum = _shape_array(spec.index_shock.shape, spec.horizon_quarters, spec.index_shock.cumulative_pct)
    region_factor = spec.index_shock.by_region or {"default": 1.0}
    obj_factor = spec.index_shock.by_object_type or {}

    rows_idx = []
    base_index_lookup = fpre.set_index(["region_code", "object_type", "period"])["index_value"].to_dict()
    base_period = sorted(fpre["period"].unique())[-1]
    for canton in cantons:
        rfac = region_factor.get(canton, region_factor.get("default", 1.0))
        for obj in object_types:
            ofac = obj_factor.get(obj, 1.0)
            base_idx = base_index_lookup.get((canton, obj, base_period), 100.0)
            for k, p in enumerate(periods):
                shock = cum[k] * rfac * ofac
                rows_idx.append({
                    "scenario_id":         spec.id,
                    "region_code":         canton,
                    "object_type":         obj,
                    "period":              p,
                    "shock_pct":           round(shock, 6),
                    "shocked_index_value": round(base_idx * (1 + shock), 4),
                })
    index_overlay = pd.DataFrame(rows_idx)

    # --- RATE OVERLAY ---
    bp_map = spec.rate_shock.bp or {}
    rows_rate = []
    rate_names = ["SARON_3M", "FIX_5Y", "FIX_10Y"]
    last_rates = (
        rates.sort_values("rate_date")
             .groupby("rate_name").tail(1)
             .set_index("rate_name")["rate_pct"]
             .to_dict()
    )
    for k, p in enumerate(periods):
        ramp = (k + 1) / spec.horizon_quarters
        for rn in rate_names:
            bp = bp_map.get(rn, 0)
            shocked = last_rates.get(rn, 1.0) + (bp / 100.0) * ramp
            rows_rate.append({
                "scenario_id":      spec.id,
                "period":           p,
                "rate_name":        rn,
                "shock_bp":         int(bp * ramp),
                "shocked_rate_pct": round(shocked, 4),
            })
    rate_overlay = pd.DataFrame(rows_rate)

    # --- MACRO OVERLAY ---
    rows_macro = []
    for k, p in enumerate(periods):
        rows_macro.append({
            "scenario_id":      spec.id,
            "period":           p,
            "unemployment_pct": spec.macro.unemployment_pct,
            "gdp_yoy_pct":      spec.macro.gdp_yoy_pct,
            "income_shock_pct": spec.macro.income_shock_pct,
        })
    macro_overlay = pd.DataFrame(rows_macro)

    return index_overlay, rate_overlay, macro_overlay
