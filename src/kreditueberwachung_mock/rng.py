"""Single source of seeded randomness."""
from __future__ import annotations
import hashlib
import numpy as np
from faker import Faker
from . import config


def root_rng() -> np.random.Generator:
    return np.random.default_rng(config.SEED)


def child_rng(label: str) -> np.random.Generator:
    """Deterministic child RNG keyed by a stage label."""
    digest = hashlib.sha256(f"{config.SEED}:{label}".encode()).digest()
    seed = int.from_bytes(digest[:8], "little") & 0x7FFFFFFF
    return np.random.default_rng(seed)


def fakers() -> dict[str, Faker]:
    """Per-language Faker instances. Seeded for reproducibility."""
    out: dict[str, Faker] = {}
    for lang, locale in (("de", "de_CH"), ("fr", "fr_CH"), ("it", "it_CH")):
        try:
            f = Faker(locale)
        except Exception:                                              # pragma: no cover
            f = Faker("de_DE" if lang == "de" else "fr_FR" if lang == "fr" else "it_IT")
        f.seed_instance(config.SEED + ord(lang[0]))
        out[lang] = f
    return out


def weighted_choice(rng: np.random.Generator, choices, weights):
    """Vectorised single pick from (choices, weights)."""
    p = np.asarray(weights, dtype=float)
    p = p / p.sum()
    idx = rng.choice(len(choices), p=p)
    return choices[idx]


def weighted_array(rng: np.random.Generator, choices, weights, n):
    p = np.asarray(weights, dtype=float)
    p = p / p.sum()
    idx = rng.choice(len(choices), size=n, p=p)
    return [choices[i] for i in idx]
