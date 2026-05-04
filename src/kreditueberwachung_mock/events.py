"""Event-based surveillance: per-loan event timeline."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from . import config, rng as rngmod


# SLA per event type: (default_days, regulatory/internal basis). Severity is a multiplier
# (see SEV_MULT below). Real-world Swiss banking practice: the deadline is driven by the
# trigger (regulator or internal credit policy), severity only tightens or relaxes it.
SLA_DAYS_BY_TYPE: dict[str, tuple[int, str]] = {
    "sanctions_hit":               (1,   "GwG Art. 9 / Embargogesetz"),
    "payment_default":             (5,   "FINMA-RS 2008/21 NPL"),
    "pep_status_change":           (5,   "FINMA-RS 2016/7"),
    "death_indicator":             (10,  "OR Erbrecht"),
    "insurance_lapse":             (14,  "Hypothekarvertrag Versicherungspflicht"),
    "ownership_change_grundbuch":  (14,  "OR / Hypothekarvertrag"),
    "betreibung_recorded":         (14,  "Intern Bonitätsprüfung"),
    "rate_change_threshold":       (14,  "Intern Kundeninformation"),
    "duplicate_client_suspected":  (14,  "GwG Identifikation"),
    "payment_arrears":             (30,  "OR Art. 102 / Mahnwesen"),
    "covenant_breach_ltv":         (30,  "Internes Kreditreglement"),
    "covenant_breach_dsti":        (30,  "SBVg-Selbstregulierung"),
    "property_value_drop_>10%":    (30,  "FINMA-Selbstregulierung"),
    "income_drop":                 (30,  "Intern Re-Tragbarkeit"),
    "address_change_unverified":   (30,  "GwG Identifikation"),
    "divorce_indicator":           (30,  "Intern Bonitätsupdate"),
    "third_pillar_payout":         (30,  "Intern Tragbarkeits-Recheck"),
    "flood_risk_alert":            (30,  "Intern Risikoabklärung"),
    "renovation_reported":         (30,  "Intern Doku/Neubewertung"),
    "employer_change":             (45,  "Intern Lohnausweis"),
    "property_revaluation_done":   (45,  "Intern Aktenaktualisierung"),
    "affordability_recheck_due":   (60,  "Intern Tragbarkeit jährlich"),
    "geak_change":                 (60,  "Intern ESG/Akten"),
    "rate_reset_due":              (60,  "Intern Konditionsangebot"),
    "kyc_review_due":              (90,  "GwG Art. 6 / VSB 20"),
    "retirement_upcoming":         (180, "Intern Tragbarkeitsplan"),
    "manual_review_request":       (30,  "RM-Antrag (Default)"),
}
SEV_MULT = {"info": 2.0, "low": 1.5, "medium": 1.0, "high": 0.75, "critical": 0.5}


# (event_type, base_weight, severity_distribution)
EVENT_CATALOG = [
    ("rate_reset_due",             10.0, {"info": 0.6, "low": 0.3, "medium": 0.1}),
    ("rate_change_threshold",       3.0, {"low": 0.6, "medium": 0.3, "high": 0.1}),
    ("payment_arrears",             1.5, {"low": 0.5, "medium": 0.4, "high": 0.1}),
    ("payment_default",             0.3, {"high": 0.7, "critical": 0.3}),
    ("covenant_breach_ltv",         1.5, {"medium": 0.5, "high": 0.4, "critical": 0.1}),
    ("covenant_breach_dsti",        1.0, {"medium": 0.5, "high": 0.4, "critical": 0.1}),
    ("affordability_recheck_due",   3.0, {"info": 0.5, "low": 0.4, "medium": 0.1}),
    ("property_revaluation_done",   4.0, {"info": 0.7, "low": 0.3}),
    ("property_value_drop_>10%",    0.8, {"medium": 0.5, "high": 0.4, "critical": 0.1}),
    ("renovation_reported",         1.2, {"info": 0.7, "low": 0.3}),
    ("geak_change",                 0.4, {"info": 0.6, "low": 0.4}),
    ("flood_risk_alert",            0.3, {"low": 0.5, "medium": 0.3, "high": 0.2}),
    ("ownership_change_grundbuch",  0.4, {"low": 0.4, "medium": 0.4, "high": 0.2}),
    ("divorce_indicator",           0.3, {"medium": 0.6, "high": 0.4}),
    ("death_indicator",             0.05, {"high": 0.6, "critical": 0.4}),
    ("retirement_upcoming",         0.6, {"info": 0.5, "low": 0.4, "medium": 0.1}),
    ("employer_change",             1.5, {"info": 0.6, "low": 0.4}),
    ("income_drop",                 0.7, {"low": 0.4, "medium": 0.4, "high": 0.2}),
    ("sanctions_hit",               0.05, {"high": 0.4, "critical": 0.6}),
    ("pep_status_change",           0.05, {"medium": 0.5, "high": 0.5}),
    ("kyc_review_due",              2.5, {"info": 0.7, "low": 0.3}),
    ("address_change_unverified",   0.6, {"info": 0.5, "low": 0.5}),
    ("duplicate_client_suspected",  0.05, {"low": 0.6, "medium": 0.4}),
    ("betreibung_recorded",         0.15, {"medium": 0.5, "high": 0.5}),
    ("insurance_lapse",             0.4, {"low": 0.4, "medium": 0.4, "high": 0.2}),
    ("third_pillar_payout",         0.3, {"info": 0.7, "low": 0.3}),
    ("manual_review_request",       0.3, {"info": 0.5, "low": 0.5}),
]


def _pick_severity(rng: np.random.Generator, dist: dict[str, float]) -> str:
    keys = list(dist.keys())
    p = np.array(list(dist.values()))
    p = p / p.sum()
    return keys[int(rng.choice(len(keys), p=p))]


def generate_events(loans: pd.DataFrame, risk_metrics: pd.DataFrame) -> pd.DataFrame:
    rng = rngmod.child_rng("events")
    today = dt.date.today()

    rm_lookup = risk_metrics.set_index("loan_id")[
        ["watchlist_flag", "npl_flag", "covenant_breach_flag", "days_past_due"]
    ].to_dict("index")

    rows = []
    next_id = 1
    for ln in loans.itertuples(index=False):
        rm = rm_lookup.get(int(ln.loan_id), {})
        risk_multiplier = 1.0
        if rm.get("watchlist_flag"):
            risk_multiplier *= 2.5
        if rm.get("npl_flag"):
            risk_multiplier *= 4.0
        if rm.get("covenant_breach_flag"):
            risk_multiplier *= 1.8

        n_events = max(0, int(rng.poisson(config.EVENTS_PER_LOAN_MEAN * risk_multiplier)))
        n_events = min(n_events, 30)
        if n_events == 0:
            continue

        weights = np.array([w for _, w, _ in EVENT_CATALOG])
        weights = weights / weights.sum()
        event_idx = rng.choice(len(EVENT_CATALOG), size=n_events, p=weights)

        origination = dt.date.fromisoformat(ln.origination_date)
        for ei in event_idx:
            etype, _, sev_dist = EVENT_CATALOG[ei]
            sev = _pick_severity(rng, sev_dist)

            life_days = max(61, (today - origination).days)
            occurred = origination + dt.timedelta(days=int(rng.integers(60, life_days)))
            detected = occurred + dt.timedelta(days=int(rng.integers(0, 14)))
            base_days, sla_basis = SLA_DAYS_BY_TYPE.get(etype, (30, "RM-Antrag (Default)"))
            sla_days = max(1, int(round(base_days * SEV_MULT[sev])))
            sla = detected + dt.timedelta(days=sla_days)

            r = rng.random()
            if r < 0.78:
                status = "closed_resolved"
                resolved = detected + dt.timedelta(days=int(rng.integers(1, 60)))
            elif r < 0.86:
                status = "in_progress"
                resolved = None
            elif r < 0.93:
                status = "waived"
                resolved = detected + dt.timedelta(days=int(rng.integers(0, 30)))
            elif r < 0.97:
                status = "escalated"
                resolved = None
            else:
                status = "open"
                resolved = None

            rows.append({
                "event_id":       next_id,
                "loan_id":        int(ln.loan_id),
                "client_id":      int(ln.primary_client_id),
                "property_id":    int(ln.property_id),
                "event_type":     etype,
                "event_subtype":  None,
                "severity":       sev,
                "source":         np.random.choice(["system", "external_data", "relationship_manager", "customer"],
                                                    p=[0.55, 0.20, 0.20, 0.05]),
                "detected_at":    detected.isoformat(),
                "occurred_at":    occurred.isoformat(),
                "title":          etype.replace("_", " ").capitalize(),
                "description":    f"Auto-generated event of type {etype}",
                "status":         status,
                "assigned_to":    f"OFFICER-{int(rng.integers(1, 60))}",
                "resolved_at":    resolved.isoformat() if resolved else None,
                "sla_due_date":   sla.isoformat(),
                "sla_basis":      sla_basis,
                "linked_case_id": None,
            })
            next_id += 1
    return pd.DataFrame(rows)
