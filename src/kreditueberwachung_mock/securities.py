"""Wertschriftendepots: 5 Anlagestrategien × ~30 reale CH/EU-ISINs.

Generates `portfolio` and `position` rows for a configurable share of clients.
Allocation per strategy:
  konservativ:  100% bonds (≥80% IG-bonds, rest cash/money-market)
  vorsichtig:    30% equity / 70% bonds
  mittel:        50% equity / 50% bonds
  wachstum:      75% equity / 25% bonds
  aktien:       100% equity (with a small 2-5% cash buffer)

Higher segment → higher chance of a depot, larger volume.
"""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd

from . import config, rng as rngmod


# ISIN universe — real instruments, plausible Swiss-bank shelf.
INSTRUMENTS: list[dict] = [
    # CH government / Pfandbriefe
    {"isin": "CH0224396285", "name": "EIDG 4% 2049",                         "ac": "bond",       "ccy": "CHF", "px": 132.40},
    {"isin": "CH0344963361", "name": "EIDG 0.5% 2030",                       "ac": "bond",       "ccy": "CHF", "px":  99.10},
    {"isin": "CH0526540133", "name": "EIDG 0% 2031",                         "ac": "bond",       "ccy": "CHF", "px":  96.20},
    {"isin": "CH0419041339", "name": "Pfandbriefzentrale 0.25% 2034",        "ac": "bond",       "ccy": "CHF", "px":  93.80},
    {"isin": "CH0224397044", "name": "Kantonalbank ZH 1% 2032",              "ac": "bond",       "ccy": "CHF", "px": 100.50},
    # Bond ETFs
    {"isin": "CH0102530786", "name": "UBS ETF SBI Domestic Government 1-3",  "ac": "etf_bond",   "ccy": "CHF", "px": 102.40},
    {"isin": "CH0226976816", "name": "iShares Swiss Domestic Government 7-15","ac": "etf_bond",  "ccy": "CHF", "px":  98.10},
    {"isin": "IE00B4WXJJ64", "name": "iShares Core Global Aggregate CHF Hgd","ac": "etf_bond",   "ccy": "CHF", "px":   4.85},
    {"isin": "IE00B3F81R35", "name": "iShares Core Euro Corporate Bond",     "ac": "etf_bond",   "ccy": "EUR", "px": 132.20},
    # Equity ETFs
    {"isin": "CH0008899764", "name": "UBS ETF SMI",                          "ac": "etf_equity", "ccy": "CHF", "px":  98.20},
    {"isin": "CH0237935652", "name": "UBS ETF SLI",                          "ac": "etf_equity", "ccy": "CHF", "px": 110.40},
    {"isin": "IE00B4L5Y983", "name": "iShares Core MSCI World",              "ac": "etf_equity", "ccy": "CHF", "px":  92.60},
    {"isin": "IE00B5BMR087", "name": "iShares Core S&P 500",                 "ac": "etf_equity", "ccy": "CHF", "px": 510.30},
    {"isin": "IE00BKM4GZ66", "name": "iShares Core MSCI EM IMI",             "ac": "etf_equity", "ccy": "CHF", "px":  31.90},
    {"isin": "CH0030849654", "name": "UBS ETF MSCI Switzerland 20/35",       "ac": "etf_equity", "ccy": "CHF", "px":  84.50},
    # CH equity blue chips
    {"isin": "CH0012005267", "name": "Novartis",                             "ac": "equity",     "ccy": "CHF", "px":  94.50},
    {"isin": "CH0012032048", "name": "Roche GS",                             "ac": "equity",     "ccy": "CHF", "px": 268.40},
    {"isin": "CH0038863350", "name": "Nestlé",                               "ac": "equity",     "ccy": "CHF", "px":  88.80},
    {"isin": "CH0244767585", "name": "UBS Group",                            "ac": "equity",     "ccy": "CHF", "px":  29.40},
    {"isin": "CH0014852781", "name": "Zurich Insurance",                     "ac": "equity",     "ccy": "CHF", "px": 545.00},
    {"isin": "CH0011075394", "name": "Swiss Re",                             "ac": "equity",     "ccy": "CHF", "px": 124.20},
    {"isin": "CH0102484968", "name": "Cembra Money Bank",                    "ac": "equity",     "ccy": "CHF", "px":  82.50},
    {"isin": "CH0024899483", "name": "Geberit",                              "ac": "equity",     "ccy": "CHF", "px": 564.00},
    {"isin": "CH0023405456", "name": "Sika",                                 "ac": "equity",     "ccy": "CHF", "px": 235.00},
    {"isin": "CH0012221716", "name": "ABB",                                  "ac": "equity",     "ccy": "CHF", "px":  52.40},
    # International blue chips
    {"isin": "US0378331005", "name": "Apple",                                "ac": "equity",     "ccy": "USD", "px": 195.40},
    {"isin": "US5949181045", "name": "Microsoft",                            "ac": "equity",     "ccy": "USD", "px": 415.00},
    {"isin": "US02079K3059", "name": "Alphabet A",                           "ac": "equity",     "ccy": "USD", "px": 175.00},
    {"isin": "NL0010273215", "name": "ASML",                                 "ac": "equity",     "ccy": "EUR", "px": 905.00},
    # Cash / money market
    {"isin": "CH0331454167", "name": "CSAM Money Market Fund CHF",           "ac": "cash",       "ccy": "CHF", "px": 100.00},
]

# Strategy → list of (instrument-pool-filter, target-weight-range)
STRATEGIES: dict[str, dict] = {
    "konservativ": {
        "benchmark": "SBI Domestic Govt + 1m CHF Cash",
        "ac_targets": {"bond": 0.55, "etf_bond": 0.30, "cash": 0.15},
    },
    "vorsichtig": {
        "benchmark": "30% MSCI World CHF Hgd / 70% Global Agg CHF Hgd",
        "ac_targets": {"bond": 0.20, "etf_bond": 0.50, "etf_equity": 0.20, "equity": 0.05, "cash": 0.05},
    },
    "mittel": {
        "benchmark": "50% MSCI World / 50% Global Agg CHF Hgd",
        "ac_targets": {"etf_bond": 0.40, "bond": 0.10, "etf_equity": 0.30, "equity": 0.17, "cash": 0.03},
    },
    "wachstum": {
        "benchmark": "75% MSCI World / 25% Global Agg CHF Hgd",
        "ac_targets": {"etf_bond": 0.20, "bond": 0.05, "etf_equity": 0.45, "equity": 0.27, "cash": 0.03},
    },
    "aktien": {
        "benchmark": "100% MSCI World",
        "ac_targets": {"etf_equity": 0.55, "equity": 0.42, "cash": 0.03},
    },
}

STRATEGY_DIST = [
    ("konservativ", 0.35),
    ("vorsichtig",  0.25),
    ("mittel",      0.20),
    ("wachstum",    0.12),
    ("aktien",      0.08),
]

# Segment → relative depot likelihood (multipliers applied to PORTFOLIO_FRAC)
SEGMENT_WEIGHT = {
    "private_banking": 4.0,
    "affluent":        2.0,
    "business":        1.5,
    "retail":          0.6,
}

# Segment → log-normal volume parameters in CHF (mean/sigma of log)
SEGMENT_VOLUME = {
    "private_banking": (14.4, 0.65),  # ~CHF 1.8M median
    "affluent":        (13.0, 0.55),  # ~CHF 440k median
    "business":        (13.2, 0.60),
    "retail":          (12.0, 0.55),  # ~CHF 165k median
}

# Strategy → typical positions count range (low, high)
STRATEGY_POSITIONS = {
    "konservativ": (8, 14),
    "vorsichtig":  (10, 16),
    "mittel":      (12, 20),
    "wachstum":    (12, 22),
    "aktien":      (10, 24),
}


def _pick_strategy(rng: np.random.Generator) -> str:
    keys = [k for k, _ in STRATEGY_DIST]
    p = np.array([w for _, w in STRATEGY_DIST])
    p = p / p.sum()
    return keys[int(rng.choice(len(keys), p=p))]


def _select_instruments(rng: np.random.Generator, strategy: str) -> list[dict]:
    targets = STRATEGIES[strategy]["ac_targets"]
    lo, hi = STRATEGY_POSITIONS[strategy]
    n_target = int(rng.integers(lo, hi + 1))
    by_class = {ac: [i for i in INSTRUMENTS if i["ac"] == ac] for ac in targets}
    chosen: list[dict] = []
    # Allocate position count proportional to target weight (min 1 per used class).
    weights = np.array(list(targets.values()))
    weights = weights / weights.sum()
    raw_counts = np.maximum(1, np.round(weights * n_target).astype(int))
    classes = list(targets.keys())
    # Normalise so total ≈ n_target (cap at pool size per class).
    for ac, cnt in zip(classes, raw_counts):
        pool = by_class.get(ac, [])
        if not pool:
            continue
        take = min(int(cnt), len(pool))
        idx = rng.choice(len(pool), size=take, replace=False)
        for ix in idx:
            chosen.append(pool[int(ix)])
    return chosen


def generate_portfolios(clients: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build portfolio + position DataFrames. Returns ([] , []) if PORTFOLIO_FRAC == 0."""
    if config.PORTFOLIO_FRAC <= 0:
        return pd.DataFrame(), pd.DataFrame()

    rng = rngmod.child_rng("securities")
    today = dt.date.today()

    # Probability of having a depot per row (clipped to 1.0).
    seg = clients["segment"].fillna("retail").values
    base = config.PORTFOLIO_FRAC
    p_depot = np.clip(np.array([base * SEGMENT_WEIGHT.get(s, 1.0) for s in seg]), 0, 0.95)
    has_depot = rng.random(len(clients)) < p_depot
    depot_clients = clients.loc[has_depot, ["client_id", "segment"]].reset_index(drop=True)
    if depot_clients.empty:
        return pd.DataFrame(), pd.DataFrame()

    portfolio_rows = []
    position_rows = []
    next_pid = 1
    next_posid = 1
    for _, c in depot_clients.iterrows():
        seg_c = c["segment"] if c["segment"] in SEGMENT_VOLUME else "retail"
        strategy = _pick_strategy(rng)
        meta = STRATEGIES[strategy]
        mu, sigma = SEGMENT_VOLUME[seg_c]
        total = float(np.clip(rng.lognormal(mean=mu, sigma=sigma), 20_000, 12_000_000))

        instruments = _select_instruments(rng, strategy)
        # Random weights respecting strategy ac_targets, then jitter.
        ac_targets = meta["ac_targets"]
        weights_per_pos = []
        for inst in instruments:
            base_w = ac_targets.get(inst["ac"], 0.05)
            weights_per_pos.append(base_w * float(rng.uniform(0.6, 1.4)))
        wsum = sum(weights_per_pos)
        weights_per_pos = [w / wsum for w in weights_per_pos]

        # Cash residual: keep an explicit cash position so totals reconcile.
        cash_share = ac_targets.get("cash", 0.02)
        cash_value = total * cash_share
        invested_value = total - cash_value

        positions_for_pf = []
        for inst, w in zip(instruments, weights_per_pos):
            if inst["ac"] == "cash":
                continue  # explicit cash row appended below
            mv = invested_value * w
            qty = mv / max(inst["px"], 0.01)
            avg_cost = inst["px"] * float(rng.uniform(0.85, 1.05))
            unreal = (inst["px"] - avg_cost) * qty
            positions_for_pf.append({
                "isin": inst["isin"], "name": inst["name"], "ac": inst["ac"],
                "ccy": inst["ccy"], "qty": qty, "px": inst["px"],
                "avg_cost": avg_cost, "mv": mv, "unreal": unreal,
            })
        # Append cash
        positions_for_pf.append({
            "isin": "CH0331454167", "name": "CSAM Money Market Fund CHF",
            "ac": "cash", "ccy": "CHF", "qty": cash_value / 100.0, "px": 100.0,
            "avg_cost": 100.0, "mv": cash_value, "unreal": 0.0,
        })
        actual_total = sum(p["mv"] for p in positions_for_pf)

        ytd = float(rng.normal({"konservativ": 1.5, "vorsichtig": 3.0, "mittel": 4.5,
                                 "wachstum": 6.0, "aktien": 7.5}[strategy], 2.0))
        one_yr = float(rng.normal({"konservativ": 2.5, "vorsichtig": 5.0, "mittel": 7.5,
                                    "wachstum": 11.0, "aktien": 14.0}[strategy], 4.0))
        inception = today - dt.timedelta(days=int(rng.integers(180, 365 * 12)))
        portfolio_rows.append({
            "portfolio_id": next_pid,
            "client_id": int(c["client_id"]),
            "strategy": strategy,
            "benchmark": meta["benchmark"],
            "inception_date": inception.isoformat(),
            "total_value_chf": round(actual_total, 2),
            "cash_chf": round(cash_value, 2),
            "ytd_return_pct": round(ytd, 3),
            "one_year_return_pct": round(one_yr, 3),
            "custodian": str(rng.choice(["Internal", "PostFinance", "CSAM", "VP Bank"])),
            "fee_model": str(rng.choice(["flat", "tiered", "transactional"], p=[0.6, 0.3, 0.1])),
            "last_review_date": (today - dt.timedelta(days=int(rng.integers(0, 365)))).isoformat(),
        })
        for p in positions_for_pf:
            position_rows.append({
                "position_id": next_posid,
                "portfolio_id": next_pid,
                "isin": p["isin"], "name": p["name"], "asset_class": p["ac"],
                "currency": p["ccy"],
                "quantity": round(p["qty"], 4),
                "avg_cost_chf": round(p["avg_cost"], 4),
                "market_price_chf": round(p["px"], 4),
                "market_value_chf": round(p["mv"], 2),
                "unrealized_pnl_chf": round(p["unreal"], 2),
                "weight_pct": round(100.0 * p["mv"] / max(actual_total, 1e-6), 3),
                "last_price_date": today.isoformat(),
            })
            next_posid += 1
        next_pid += 1

    return pd.DataFrame(portfolio_rows), pd.DataFrame(position_rows)
