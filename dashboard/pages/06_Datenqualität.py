"""Datenqualität: eingebaute Inkonsistenzen + Live-Anomalien."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402

from dashboard import data, style, i18n    # noqa: E402

st.set_page_config(page_title="Datenqualität", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Datenqualität")

LANG = i18n.current_lang()
style.page_head(i18n.t("ph_dq_crumb"),
                "Eingebaute Inkonsistenzen" if LANG == "de" else "Intentional inconsistencies",
                "Beabsichtigte menschliche Fehler im Datensatz · Live-Zählung." if LANG == "de"
                else "Intentional human errors in the dataset · live count.")

dq = data.dq_summary()
if LANG == "de":
    kpi_lbl = ("Geburtsdatum dot-format", "E-Mail-Anomalien", "PLZ ↔ Kanton",
               "Kanton als Vollname", "Festnetz NULL-Ersatz")
else:
    kpi_lbl = ("Birth date dot-format", "Email anomalies", "Postal code ↔ canton",
               "Canton as full name", "Landline NULL surrogate")
style.kpi_strip([
    {"label": kpi_lbl[0], "value": style.fmt_int(dq["birth_date_dotformat"])},
    {"label": kpi_lbl[1], "value": style.fmt_int(dq["email_anomalies"])},
    {"label": kpi_lbl[2], "value": style.fmt_int(dq["plz_canton_mismatch"])},
    {"label": kpi_lbl[3], "value": style.fmt_int(dq["canton_full_name"])},
    {"label": kpi_lbl[4], "value": style.fmt_int(dq["null_surrogate"])},
])

style.section_head("Regel inspizieren" if LANG == "de" else "Inspect rule")
if LANG == "de":
    rule_options = [
        ("Geburtsdatum · Punkt-Format",    "birth_date_dotformat"),
        ("E-Mail-Anomalien",                "email_anomalies"),
        ("PLZ ↔ Kanton-Abweichung",         "plz_canton_mismatch"),
        ("Kanton als Vollname",             "canton_full_name"),
        ("Festnetz · NULL-Ersatz",          "null_surrogate"),
    ]
    rule_lbl = "Regel"
else:
    rule_options = [
        ("Birth date · dot format",         "birth_date_dotformat"),
        ("Email anomalies",                 "email_anomalies"),
        ("Postal code ↔ canton mismatch",   "plz_canton_mismatch"),
        ("Canton as full name",             "canton_full_name"),
        ("Landline · NULL surrogate",       "null_surrogate"),
    ]
    rule_lbl = "Rule"
rule = st.selectbox(rule_lbl, options=rule_options, format_func=lambda x: x[0])
st.dataframe(data.dq_examples(rule[1], limit=200),
             use_container_width=True, height=460, hide_index=True)

style.section_head("Katalogdatei" if LANG == "de" else "Catalog file")
cat_path = Path(__file__).resolve().parents[2] / "output" / "data_quality_issues.md"
if cat_path.exists():
    st.markdown(cat_path.read_text(encoding="utf-8"))
else:
    st.info("Generator ausführen, um den Katalog zu erzeugen." if LANG == "de"
            else "Run the generator to create the catalog.")

style.footer()
