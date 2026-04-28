"""GeoJSON loading & canton-name normalisation for high-fidelity choropleths."""
from __future__ import annotations
import json
from functools import lru_cache
import streamlit as st
from kreditueberwachung_mock import config


GEOJSON_PATH = config.REFERENCE_DIR / "ch_cantons.geojson"


# Mapping from canton 2-letter code → German name as it appears in the GeoJSON `NAME` field.
CODE_TO_GEO_NAME = {
    "ZH": "Zürich",       "BE": "Bern",            "LU": "Luzern",
    "UR": "Uri",          "SZ": "Schwyz",          "OW": "Obwalden",
    "NW": "Nidwalden",    "GL": "Glarus",          "ZG": "Zug",
    "FR": "Freiburg",     "SO": "Solothurn",       "BS": "Basel-Stadt",
    "BL": "Basel-Landschaft", "SH": "Schaffhausen", "AR": "Appenzell Ausserrhoden",
    "AI": "Appenzell Innerrhoden", "SG": "St. Gallen", "GR": "Graubünden",
    "AG": "Aargau",       "TG": "Thurgau",         "TI": "Ticino",
    "VD": "Vaud",         "VS": "Valais",          "NE": "Neuchâtel",
    "GE": "Genève",       "JU": "Jura",
}
GEO_NAME_TO_CODE = {v: k for k, v in CODE_TO_GEO_NAME.items()}


@st.cache_resource(show_spinner="Loading Swiss canton boundaries…")
def cantons_geojson() -> dict:
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        gj = json.load(f)
    # Add a clean canton_code field so plotly can match by canton_code.
    for feat in gj.get("features", []):
        name = feat.get("properties", {}).get("NAME", "")
        feat["properties"]["canton_code"] = GEO_NAME_TO_CODE.get(name, "")
    return gj
