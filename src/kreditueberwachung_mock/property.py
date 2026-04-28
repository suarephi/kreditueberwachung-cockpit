"""Property and property-address generation."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from . import config, geography, reference, rng as rngmod


GEAK_CLASSES = list("ABCDEFG")
GEAK_W       = [0.04, 0.10, 0.18, 0.25, 0.22, 0.15, 0.06]
HEATING      = ["Wärmepumpe", "Gasheizung", "Ölheizung", "Fernwärme", "Pellets", "Solarthermie", "Stromheizung"]
HEATING_W    = [0.34, 0.22, 0.16, 0.13, 0.06, 0.07, 0.02]
SUB_TYPE = {
    "EFH":           ["Einfamilienhaus", "Doppelhaushälfte", "Reihenhaus", "Bungalow"],
    "ETW":           ["3.5-Zimmer Wohnung", "4.5-Zimmer Wohnung", "5.5-Zimmer Wohnung", "Loft", "Attika"],
    "MFH":           ["Mehrfamilienhaus", "Renditeobjekt", "Wohn-/Geschäftshaus"],
    "Ferienwohnung": ["Bergchalet", "Ferienwohnung Bergregion", "Ferienwohnung See"],
    "Gewerbe":       ["Bürogebäude", "Gewerbeliegenschaft", "Praxisräume"],
    "Bauland":       ["Bauland erschlossen", "Bauland unerschlossen"],
}


def generate_properties(loans_n: int, address_offset: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build `loans_n` properties + matching property addresses.

    Address IDs are assigned starting at `address_offset` (so they don't collide with client
    residential addresses).
    """
    rng = rngmod.child_rng("property")
    today = dt.date.today()

    # Sample PLZ for each property (location of the financed object).
    plz_rows = geography.sample_postal_codes(rng, loans_n).reset_index(drop=True)

    # Object-type mix.
    types  = [t for t, _ in config.OBJECT_TYPE_MIX]
    weights = [w for _, w in config.OBJECT_TYPE_MIX]
    object_types = rngmod.weighted_array(rng, types, weights, loans_n)

    sub_types = [SUB_TYPE[t][int(rng.integers(0, len(SUB_TYPE[t])))] for t in object_types]

    # Construction year: skewed toward 1960-2010.
    constr_year = np.clip(np.round(rng.normal(1985, 25, size=loans_n)).astype(int), 1850, today.year)
    # Renovation: ~50 % renovated within last 25 years.
    last_reno = np.where(
        rng.random(loans_n) < 0.50,
        np.clip(constr_year + rng.integers(15, 60, size=loans_n), constr_year + 5, today.year),
        np.zeros(loans_n, dtype=int),
    )
    # Living area depends on object type.
    base_area = {
        "EFH":           np.clip(rng.normal(165, 50, loans_n), 90, 450),
        "ETW":           np.clip(rng.normal(105, 30, loans_n), 45, 280),
        "MFH":           np.clip(rng.normal(550, 200, loans_n), 220, 1500),
        "Ferienwohnung": np.clip(rng.normal(85, 30, loans_n), 35, 220),
        "Gewerbe":       np.clip(rng.normal(420, 200, loans_n), 90, 1800),
        "Bauland":       np.clip(rng.normal(0.0, 1.0, loans_n), 0, 0),
    }
    living_area = np.array([base_area[t][i] for i, t in enumerate(object_types)]).round(1)
    plot_area = np.where(
        np.isin(object_types, ["EFH", "MFH", "Bauland", "Gewerbe"]),
        np.clip(rng.normal(700, 400, loans_n), 200, 5000),
        np.zeros(loans_n),
    ).round(0)

    rooms = np.where(
        np.isin(object_types, ["EFH", "ETW", "Ferienwohnung"]),
        np.clip(np.round(living_area / 25, 1), 1.5, 12.0),
        np.where(np.isin(object_types, ["MFH"]),
                 np.round(living_area / 22, 1),
                 np.zeros(loans_n)),
    )
    bathrooms = np.maximum(1, np.round(rooms / 3).astype(int))
    floors_total = np.clip(np.round(rng.normal(3, 1.5, loans_n)).astype(int), 1, 9)
    floor_unit = np.where(
        np.isin(object_types, ["ETW", "Ferienwohnung"]),
        np.clip(rng.integers(0, 6, loans_n), 0, 9),
        np.zeros(loans_n, dtype=int),
    )

    geak  = rngmod.weighted_array(rng, GEAK_CLASSES, GEAK_W, loans_n)
    heat  = rngmod.weighted_array(rng, HEATING, HEATING_W, loans_n)

    micro_loc = plz_rows["location_score_micro"].values \
                + rng.normal(0, 0.25, loans_n)
    macro_loc = plz_rows["canton_code"].map(
        reference.canton_lookup()).map(lambda d: d["location_score_macro"]).values \
                + rng.normal(0, 0.20, loans_n)

    flood_zone = np.where(rng.random(loans_n) < 0.04, "Z3", np.where(rng.random(loans_n) < 0.10, "Z2", "Z1"))
    seismic_zone = np.where(plz_rows["canton_code"].isin(["VS", "GR", "BS", "BL"]), "Z3a", "Z1")
    noise_ruk = np.where(plz_rows["urbanity"] == "urban",
                         np.where(rng.random(loans_n) < 0.40, "ES_III", "ES_II"),
                         "ES_II")
    usage = np.where(np.isin(object_types, ["MFH", "Gewerbe"]),
                     "rental",
                     np.where(np.isin(object_types, ["Ferienwohnung"]),
                              "holiday",
                              "owner_occupied"))

    purchase_dates = [
        (today - dt.timedelta(days=int(rng.integers(60, 365 * 25)))).isoformat()
        for _ in range(loans_n)
    ]

    addresses = pd.DataFrame({
        "address_id":      np.arange(address_offset, address_offset + loans_n),
        "street":          [geography.random_street(rng, "de") for _ in range(loans_n)],
        "house_number":    [str(int(rng.integers(1, 200))) for _ in range(loans_n)],
        "postal_code":     plz_rows["postal_code"].astype(str).values,
        "city":            plz_rows["city"].values,
        "canton":          plz_rows["canton_code"].values,
        "country":         "CH",
        "bfs_gemeinde_nr": plz_rows["bfs_gemeinde_nr"].values,
        "ms_region":       plz_rows["ms_region"].values,
        "address_type":    "property",
        "valid_from":      purchase_dates,
        "valid_to":        None,
    })

    properties = pd.DataFrame({
        "property_id":              np.arange(1, loans_n + 1),
        "object_type":              object_types,
        "sub_type":                 sub_types,
        "address_id":               addresses["address_id"].values,
        "egid":                     [int(rng.integers(10**8, 10**9)) for _ in range(loans_n)],
        "ewid":                     [int(rng.integers(1, 200)) for _ in range(loans_n)],
        "construction_year":        constr_year,
        "last_renovation_year":     last_reno,
        "living_area_sqm":          living_area,
        "plot_area_sqm":            plot_area,
        "rooms":                    rooms,
        "bathrooms":                bathrooms,
        "floors_total":             floors_total,
        "floor_unit":               floor_unit,
        "heating_type":             heat,
        "geak_class":               geak,
        "building_insurance_value": (living_area * np.where(np.isin(object_types, ["MFH"]), 4500, 3800)).round(0),
        "usage":                    usage,
        "micro_location_score":     micro_loc.round(2),
        "macro_location_score":     macro_loc.round(2),
        "flood_zone":               flood_zone,
        "noise_ruk":                noise_ruk,
        "seismic_zone":             seismic_zone,
        "purchase_price":           np.zeros(loans_n),         # set later by valuation step
        "purchase_date":            purchase_dates,
        "status":                   "active",
        "region_code":              plz_rows["canton_code"].values,
        "created_at":               [today.isoformat()] * loans_n,
    })

    return properties, addresses
