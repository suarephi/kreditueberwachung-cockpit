"""Scenario YAML loader."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import hashlib
import yaml
from .. import config


@dataclass
class IndexShock:
    shape:           str = "linear"                        # linear | frontload | u_shape
    cumulative_pct:  float = 0.0                           # e.g. -0.25
    by_region:       dict[str, float] = field(default_factory=lambda: {"default": 1.0})
    by_object_type:  dict[str, float] = field(default_factory=dict)


@dataclass
class RateShock:
    curve: str = "flat"                                    # flat | twist
    bp:    dict[str, int] = field(default_factory=dict)    # {SARON_3M: bp, FIX_5Y: bp, FIX_10Y: bp}


@dataclass
class MacroShock:
    unemployment_pct: float = 2.0
    gdp_yoy_pct:      float = 1.0
    income_shock_pct: float = 0.0


@dataclass
class ScenarioSpec:
    id:               str
    name:             str
    severity:         str
    horizon_quarters: int
    start_period:     str
    seed:             int
    narrative:        str = ""
    source:           str = "internal"
    index_shock:      IndexShock = field(default_factory=IndexShock)
    rate_shock:       RateShock = field(default_factory=RateShock)
    macro:            MacroShock = field(default_factory=MacroShock)
    yaml_hash:        str = ""


def _from_dict(d: dict[str, Any]) -> ScenarioSpec:
    return ScenarioSpec(
        id               = d["id"],
        name             = d["name"],
        severity         = d.get("severity", "moderate"),
        horizon_quarters = int(d.get("horizon_quarters", config.STRESS_HORIZON_Q)),
        start_period     = d.get("start_period", config.STRESS_START_PERIOD),
        seed             = int(d.get("seed", config.SEED + abs(hash(d["id"])) % 10_000)),
        narrative        = d.get("narrative", ""),
        source           = d.get("source", "internal"),
        index_shock = IndexShock(**(d.get("index_shock") or {})),
        rate_shock  = RateShock(**(d.get("rate_shock") or {})),
        macro       = MacroShock(**(d.get("macro") or {})),
    )


def load(scenario_id: str) -> ScenarioSpec:
    path = config.SCENARIOS_DIR / f"{scenario_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    raw = path.read_text(encoding="utf-8")
    spec = _from_dict(yaml.safe_load(raw))
    spec.yaml_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return spec


def list_all() -> list[str]:
    return sorted(p.stem for p in config.SCENARIOS_DIR.glob("*.yaml"))
