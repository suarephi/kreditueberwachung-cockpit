"""Load reference CSVs into pandas DataFrames."""
from __future__ import annotations
from functools import lru_cache
import pandas as pd
from . import config


@lru_cache(maxsize=1)
def cantons() -> pd.DataFrame:
    df = pd.read_csv(config.REFERENCE_DIR / "ch_cantons.csv")
    df["population_share"] = df["population_share"] / df["population_share"].sum()
    return df


@lru_cache(maxsize=1)
def postal_codes() -> pd.DataFrame:
    df = pd.read_csv(config.REFERENCE_DIR / "ch_plz.csv", dtype={"postal_code": str})
    return df


@lru_cache(maxsize=1)
def noga() -> pd.DataFrame:
    return pd.read_csv(config.REFERENCE_DIR / "noga.csv")


def canton_lookup() -> dict[str, dict]:
    return cantons().set_index("canton_code").to_dict(orient="index")


def plz_lookup() -> dict[str, dict]:
    return postal_codes().set_index("postal_code").to_dict(orient="index")
