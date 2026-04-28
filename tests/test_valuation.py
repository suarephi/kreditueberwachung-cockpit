"""Hedonic value plausibility."""
import numpy as np
from kreditueberwachung_mock.valuation import hedonic_market_value


def test_zurich_efh_per_sqm_in_band():
    rng = np.random.default_rng(42)
    samples = [
        hedonic_market_value(rng, "ZH", "EFH",
                             living_area=180, constr_year=2000, last_reno=2015,
                             micro_score=4.5, macro_score=4.5, geak="C",
                             today_year=2025)
        for _ in range(200)
    ]
    per_sqm = np.array([s / 180 for s in samples])
    assert 9_000 < np.median(per_sqm) < 18_000, np.median(per_sqm)


def test_jura_efh_cheaper_than_zurich():
    rng = np.random.default_rng(7)
    zh = np.median([
        hedonic_market_value(rng, "ZH", "EFH", 180, 2000, 0, 4.5, 4.5, "C", 2025)
        for _ in range(100)
    ]) / 180
    ju = np.median([
        hedonic_market_value(rng, "JU", "EFH", 180, 2000, 0, 3.0, 2.8, "C", 2025)
        for _ in range(100)
    ]) / 180
    assert zh > ju * 1.5, (zh, ju)
