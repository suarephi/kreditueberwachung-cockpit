"""PLZ / canton sampling and address generation."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import reference


def sample_postal_codes(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """Pick PLZ rows weighted by canton population then uniformly within canton."""
    plz_df = reference.postal_codes().copy()
    cantons = reference.cantons().set_index("canton_code")
    weight_per_plz = (
        plz_df["canton_code"].map(cantons["population_share"])
        / plz_df.groupby("canton_code")["postal_code"].transform("count")
    ).values
    weight_per_plz = weight_per_plz / weight_per_plz.sum()
    idx = rng.choice(len(plz_df), size=n, p=weight_per_plz, replace=True)
    return plz_df.iloc[idx].reset_index(drop=True)


def language_for_canton(rng: np.random.Generator, canton_code: str) -> str:
    row = reference.canton_lookup()[canton_code]
    p = np.array([row["language_share_de"], row["language_share_fr"], row["language_share_it"]])
    p = p / p.sum()
    return rng.choice(["de", "fr", "it"], p=p)


SWISS_STREET_NAMES = [
    "Bahnhofstrasse", "Hauptstrasse", "Dorfstrasse", "Kirchgasse", "Seestrasse",
    "Bergstrasse", "Rebweg", "Gartenweg", "Schulstrasse", "Lindenweg",
    "Eichenweg", "Zürcherstrasse", "Berner­strasse", "Genferstrasse",
    "Rue de la Gare", "Rue du Lac", "Avenue des Alpes", "Chemin du Bois",
    "Via San Gottardo", "Via Maistra", "Sonnenweg", "Mühleweg", "Rosengasse",
    "Brunnenstrasse", "Talweg", "Gartenstrasse", "Ringstrasse",
    "Quartierstrasse", "Bergweg", "Höheweg",
]


def random_street(rng: np.random.Generator, language: str) -> str:
    if language == "fr":
        candidates = [s for s in SWISS_STREET_NAMES if s.startswith(("Rue", "Avenue", "Chemin"))] \
                     or SWISS_STREET_NAMES
    elif language == "it":
        candidates = [s for s in SWISS_STREET_NAMES if s.startswith("Via")] or SWISS_STREET_NAMES
    else:
        candidates = [s for s in SWISS_STREET_NAMES if not s.startswith(("Rue","Avenue","Chemin","Via"))]
    return candidates[rng.integers(0, len(candidates))]
