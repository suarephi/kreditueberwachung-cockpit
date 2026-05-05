"""SLA-Matrix used by the credit-monitoring cockpit.

Mirrors `events.SLA_DAYS_BY_TYPE` (kept here as a hardcoded constant so the dashboard
can render the table even when the database is unreachable). Severity is a multiplier
applied to the type-specific default (see `SEV_MULT`).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

# (event_type, default_days, basis)
SLA_MATRIX: list[tuple[str, int, str]] = [
    ("sanctions_hit",               1,   "GwG Art. 9 / Embargogesetz"),
    ("payment_default",             5,   "FINMA-RS 2008/21 NPL"),
    ("pep_status_change",           5,   "FINMA-RS 2016/7"),
    ("death_indicator",             10,  "OR Erbrecht"),
    ("insurance_lapse",             14,  "Hypothekarvertrag Versicherungspflicht"),
    ("ownership_change_grundbuch",  14,  "OR / Hypothekarvertrag"),
    ("betreibung_recorded",         14,  "Intern Bonitätsprüfung"),
    ("rate_change_threshold",       14,  "Intern Kundeninformation"),
    ("duplicate_client_suspected",  14,  "GwG Identifikation"),
    ("payment_arrears",             30,  "OR Art. 102 / Mahnwesen"),
    ("covenant_breach_ltv",         30,  "Internes Kreditreglement"),
    ("covenant_breach_dsti",        30,  "SBVg-Selbstregulierung"),
    ("property_value_drop_>10%",    30,  "FINMA-Selbstregulierung"),
    ("income_drop",                 30,  "Intern Re-Tragbarkeit"),
    ("address_change_unverified",   30,  "GwG Identifikation"),
    ("divorce_indicator",           30,  "Intern Bonitätsupdate"),
    ("third_pillar_payout",         30,  "Intern Tragbarkeits-Recheck"),
    ("flood_risk_alert",            30,  "Intern Risikoabklärung"),
    ("renovation_reported",         30,  "Intern Doku/Neubewertung"),
    ("employer_change",             45,  "Intern Lohnausweis"),
    ("property_revaluation_done",   45,  "Intern Aktenaktualisierung"),
    ("affordability_recheck_due",   60,  "Intern Tragbarkeit jährlich"),
    ("geak_change",                 60,  "Intern ESG/Akten"),
    ("rate_reset_due",              60,  "Intern Konditionsangebot"),
    ("kyc_review_due",              90,  "GwG Art. 6 / VSB 20"),
    ("retirement_upcoming",         180, "Intern Tragbarkeitsplan"),
    ("manual_review_request",       30,  "RM-Antrag (Default)"),
]

SEV_MULT = {"info": 2.0, "low": 1.5, "medium": 1.0, "high": 0.75, "critical": 0.5}

TOOLTIP_SLA_VIOLATION = (
    "SLA-Verletzung = Bearbeitungsfrist überschritten. Frist hängt am Auslöser "
    "(regulatorisch oder intern) und wird durch Severity skaliert. Beispiele: "
    "Sanktionstreffer 1 Tag (GwG Art. 9), Zahlungsverzug 30 Tage (Mahnwesen), "
    "KYC-Review 90 Tage (GwG Art. 6). Critical halbiert die Frist, info verdoppelt sie."
)

TOOLTIP_OPEN_EVENTS = (
    "Offene Ereignisse = Posteingang der Kreditüberwachung. Events mit Status "
    "open / in_progress / escalated, in den letzten 90 Tagen erkannt."
)


def matrix_dataframe() -> pd.DataFrame:
    return pd.DataFrame(SLA_MATRIX, columns=["Event-Typ", "Standard-SLA (Tage)", "Basis"])


def render_reference(in_expander: bool = True) -> None:
    """Render the SLA reference table + severity-multiplier explanation."""
    body = lambda: _render_body()
    if in_expander:
        with st.expander("SLA-Referenz: Fristen pro Event-Typ", expanded=False):
            body()
    else:
        body()


def _render_body() -> None:
    st.markdown(
        "<div style='font-size:13px;color:var(--ink-3);line-height:1.55;margin-bottom:8px'>"
        "Tatsächliche Frist = <b>Standard-SLA × Severity-Modifikator</b>. "
        "Modifikator: <b>critical 0.5×</b>, <b>high 0.75×</b>, "
        "<b>medium 1.0×</b>, <b>low 1.5×</b>, <b>info 2.0×</b>."
        "</div>",
        unsafe_allow_html=True,
    )
    df = matrix_dataframe().sort_values("Standard-SLA (Tage)").reset_index(drop=True)
    st.dataframe(df, hide_index=True, use_container_width=True)
