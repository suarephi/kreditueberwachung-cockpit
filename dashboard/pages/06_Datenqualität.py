"""Datenqualität: eingebaute Inkonsistenzen + Live-Anomalien."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402

from dashboard import data, style    # noqa: E402

st.set_page_config(page_title="Datenqualität", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Datenqualität")

style.page_head("Datenqualität",
                "Eingebaute Inkonsistenzen",
                "Beabsichtigte menschliche Fehler im Datensatz · Live-Zählung.")

dq = data.dq_summary()
style.kpi_strip([
    {"label": "Geburtsdatum dot-format",   "value": style.fmt_int(dq["birth_date_dotformat"])},
    {"label": "E-Mail-Anomalien",          "value": style.fmt_int(dq["email_anomalies"])},
    {"label": "PLZ ↔ Kanton",              "value": style.fmt_int(dq["plz_canton_mismatch"])},
    {"label": "Kanton als Vollname",       "value": style.fmt_int(dq["canton_full_name"])},
    {"label": "Festnetz NULL-Ersatz",      "value": style.fmt_int(dq["null_surrogate"])},
])

style.section_head("Regel inspizieren")
rule = st.selectbox(
    "Regel",
    options=[
        ("Geburtsdatum · Punkt-Format",    "birth_date_dotformat"),
        ("E-Mail-Anomalien",                "email_anomalies"),
        ("PLZ ↔ Kanton-Abweichung",         "plz_canton_mismatch"),
        ("Kanton als Vollname",             "canton_full_name"),
        ("Festnetz · NULL-Ersatz",          "null_surrogate"),
    ],
    format_func=lambda x: x[0],
)
st.dataframe(data.dq_examples(rule[1], limit=200),
             use_container_width=True, height=460, hide_index=True)

style.section_head("Katalogdatei")
cat_path = Path(__file__).resolve().parents[2] / "output" / "data_quality_issues.md"
if cat_path.exists():
    st.markdown(cat_path.read_text(encoding="utf-8"))
else:
    st.info("Generator ausführen, um den Katalog zu erzeugen.")

style.footer()
