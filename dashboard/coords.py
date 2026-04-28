"""Approximate lat/lon for the Swiss cities/PLZs in our reference data."""
from __future__ import annotations
import pandas as pd
from kreditueberwachung_mock import reference


CITY_LATLON: dict[str, tuple[float, float]] = {
    "Zürich":              (47.3769, 8.5417),
    "Winterthur":          (47.4995, 8.7305),
    "Uster":               (47.3469, 8.7203),
    "Zollikon":            (47.3403, 8.5783),
    "Erlenbach ZH":        (47.3094, 8.5917),
    "Horgen":              (47.2614, 8.5969),
    "Wädenswil":           (47.2278, 8.6717),
    "Urdorf":              (47.3850, 8.4250),
    "Affoltern am Albis":  (47.2774, 8.4513),
    "Kloten":              (47.4517, 8.5856),
    "Bern":                (46.9481, 7.4474),
    "Burgdorf":            (47.0613, 7.6158),
    "Thun":                (46.7558, 7.6261),
    "Interlaken":          (46.6863, 7.8632),
    "Biel/Bienne":         (47.1368, 7.2467),
    "Ostermundigen":       (46.9533, 7.4831),
    "Köniz":               (46.9241, 7.4148),
    "Luzern":              (47.0502, 8.3093),
    "Kriens":              (47.0307, 8.2828),
    "Sursee":              (47.1714, 8.1108),
    "Altdorf UR":          (46.8814, 8.6438),
    "Schwyz":              (47.0207, 8.6536),
    "Brunnen":             (46.9992, 8.6055),
    "Merlischachen":       (47.0824, 8.4109),
    "Freienbach":          (47.2068, 8.7600),
    "Sarnen":              (46.8959, 8.2456),
    "Stans":               (46.9580, 8.3667),
    "Engelberg":           (46.8201, 8.4014),
    "Glarus":              (47.0398, 9.0668),
    "Zug":                 (47.1660, 8.5155),
    "Cham":                (47.1843, 8.4602),
    "Baar":                (47.1958, 8.5293),
    "Fribourg":            (46.8033, 7.1530),
    "Bulle":               (46.6193, 7.0571),
    "Düdingen":            (46.8523, 7.1875),
    "Solothurn":           (47.2080, 7.5375),
    "Olten":               (47.3520, 7.9019),
    "Grenchen":            (47.1937, 7.3947),
    "Basel":               (47.5596, 7.5886),
    "Allschwil":           (47.5535, 7.5460),
    "Pratteln":            (47.5176, 7.6938),
    "Reinach BL":          (47.4955, 7.5911),
    "Liestal":             (47.4844, 7.7301),
    "Schaffhausen":        (47.6967, 8.6347),
    "Herisau":             (47.3858, 9.2780),
    "Heiden":              (47.4429, 9.5346),
    "Appenzell":           (47.3315, 9.4097),
    "St. Gallen":          (47.4245, 9.3767),
    "Gossau SG":           (47.4159, 9.2517),
    "Altstätten":          (47.3760, 9.5440),
    "Wil SG":              (47.4628, 9.0467),
    "Uznach":              (47.2249, 8.9786),
    "Jona":                (47.2278, 8.8400),
    "Rapperswil SG":       (47.2266, 8.8190),
    "Chur":                (46.8499, 9.5329),
    "Davos Platz":         (46.7991, 9.8400),
    "St. Moritz":          (46.4933, 9.8395),
    "Arosa":               (46.7833, 9.6830),
    "Aarau":               (47.3919, 8.0463),
    "Baden":               (47.4732, 8.3060),
    "Wettingen":           (47.4691, 8.3170),
    "Lenzburg":            (47.3884, 8.1758),
    "Brugg":               (47.4838, 8.2080),
    "Wohlen AG":           (47.3504, 8.2776),
    "Frauenfeld":          (47.5575, 8.8964),
    "Kreuzlingen":         (47.6489, 9.1781),
    "Romanshorn":          (47.5666, 9.3789),
    "Lugano":              (46.0046, 8.9510),
    "Bellinzona":          (46.1944, 9.0245),
    "Locarno":             (46.1696, 8.7943),
    "Mendrisio":           (45.8723, 8.9788),
    "Ascona":              (46.1556, 8.7710),
    "Lausanne":            (46.5197, 6.6323),
    "Morges":              (46.5099, 6.4948),
    "Rolle":               (46.4604, 6.3367),
    "Nyon":                (46.3833, 6.2358),
    "Vevey":               (46.4628, 6.8419),
    "Montreux":            (46.4314, 6.9128),
    "Yverdon-les-Bains":   (46.7785, 6.6411),
    "Sion":                (46.2276, 7.3589),
    "Martigny":            (46.1011, 7.0747),
    "Sierre":              (46.2917, 7.5359),
    "Zermatt":             (46.0207, 7.7491),
    "Crans-Montana":       (46.3110, 7.4810),
    "Verbier":             (46.0966, 7.2278),
    "Neuchâtel":           (46.9924, 6.9293),
    "La Chaux-de-Fonds":   (47.1000, 6.8267),
    "Le Locle":            (47.0560, 6.7493),
    "Genève":              (46.2044, 6.1432),
    "Petit-Lancy":         (46.1938, 6.1086),
    "Carouge GE":          (46.1814, 6.1404),
    "Versoix":             (46.2826, 6.1622),
    "Delémont":            (47.3654, 7.3432),
    "Porrentruy":          (47.4156, 7.0742),
}

CANTON_CENTROID = {
    "ZH": (47.40, 8.65),  "BE": (46.85, 7.55),  "LU": (47.05, 8.30),
    "UR": (46.78, 8.65),  "SZ": (47.00, 8.75),  "OW": (46.85, 8.25),
    "NW": (46.95, 8.40),  "GL": (46.95, 9.05),  "ZG": (47.16, 8.52),
    "FR": (46.70, 7.10),  "SO": (47.30, 7.65),  "BS": (47.56, 7.59),
    "BL": (47.45, 7.75),  "SH": (47.70, 8.55),  "AR": (47.35, 9.30),
    "AI": (47.32, 9.42),  "SG": (47.30, 9.35),  "GR": (46.65, 9.55),
    "AG": (47.40, 8.20),  "TG": (47.55, 9.05),  "TI": (46.30, 8.85),
    "VD": (46.60, 6.60),  "VS": (46.20, 7.55),  "NE": (47.00, 6.85),
    "GE": (46.20, 6.15),  "JU": (47.35, 7.15),
}


def plz_with_coords() -> pd.DataFrame:
    plz = reference.postal_codes().copy()
    plz["lat"] = plz["city"].map(lambda c: CITY_LATLON.get(c, (None, None))[0])
    plz["lon"] = plz["city"].map(lambda c: CITY_LATLON.get(c, (None, None))[1])
    return plz.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def cantons_with_centroid() -> pd.DataFrame:
    cantons = reference.cantons().copy()
    cantons["lat"] = cantons["canton_code"].map(lambda c: CANTON_CENTROID.get(c, (None, None))[0])
    cantons["lon"] = cantons["canton_code"].map(lambda c: CANTON_CENTROID.get(c, (None, None))[1])
    return cantons
