"""Kreditdossier: Suche und Drill-Down zu einem einzelnen Kredit."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402

from dashboard import data, charts, style    # noqa: E402

st.set_page_config(page_title="Kreditdossier", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Kreditdossier")

style.page_head("Kreditdossier",
                "Suche und Drill-Down",
                "Kunde oder Kredit suchen und ins vollständige Überwachungsdossier eintauchen.")

# ---------- Search ----------
search_col1, search_col2 = st.columns([2, 1])
search_term  = search_col1.text_input("Suche nach Kunden-ID, Nachname oder Vorname",
                                      placeholder="z. B. Müller · 12345")
loan_id_input = search_col2.number_input("oder direkt zur Kredit-ID",
                                          min_value=0, value=0, step=1)

selected_loan_id: int | None = None
if loan_id_input:
    selected_loan_id = int(loan_id_input)
elif search_term:
    matches = data.search_clients(search_term, limit=25)
    if matches.empty:
        st.warning("Keine Kundentreffer.")
    else:
        st.write(f"**{len(matches)}** Kunden gefunden:")
        st.dataframe(matches.rename(columns={
            "client_id": "Kunden-ID", "first_name": "Vorname", "last_name": "Nachname",
            "birth_date": "Geburtsdatum", "segment": "Segment",
        }), use_container_width=True, height=200, hide_index=True)
        chosen = st.number_input("Kunden-ID auswählen", min_value=0, value=0, step=1)
        if chosen:
            loans = data.query("SELECT loan_id FROM loan WHERE primary_client_id = :c",
                               {"c": int(chosen)})
            if not loans.empty:
                lid = st.selectbox("Kredite", options=loans["loan_id"].tolist())
                if lid:
                    selected_loan_id = int(lid)

if selected_loan_id is None:
    st.info("Oben suchen oder eine Kredit-ID eingeben.")
    style.footer()
    st.stop()

dossier = data.loan_full(selected_loan_id)
if dossier.get("loan", None) is None or dossier["loan"].empty:
    st.error(f"Kredit-ID {selected_loan_id} nicht gefunden.")
    style.footer()
    st.stop()

loan   = dossier["loan"].iloc[0]
client = dossier["client"].iloc[0] if not dossier["client"].empty else None
prop   = dossier["property"].iloc[0] if not dossier["property"].empty else None
risk   = dossier["risk"].iloc[0] if not dossier["risk"].empty else None

# ---- Header card ----
title = (f"{client.get('salutation') or ''} {client.get('first_name') or ''} "
         f"{client.get('last_name') or ''}").strip() if client is not None else f"Kredit {selected_loan_id}"
sub_lines = []
if client is not None:
    sub_lines.append(f"Kunde {client.get('client_id')} · {client.get('language_correspondence')} · "
                     f"{client.get('segment')} · KYC {client.get('kyc_level')}")
if prop is not None:
    sub_lines.append(
        f"<b>{prop.get('object_type')}</b> · {prop.get('living_area_sqm'):.0f} m² · "
        f"{prop.get('street')} {prop.get('house_number')}, "
        f"{prop.get('postal_code')} {prop.get('city')} ({prop.get('canton')})"
    )

st.markdown(
    f"""
<div class="ku-card" style="margin:18px 0">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:24px">
    <div>
      <div class="ku-cardtitle" style="font-size:22px">{title}</div>
      <div class="ku-cardsub" style="margin-top:6px">{'<br>'.join(sub_lines)}</div>
    </div>
    <div>{style.tag_canton(f'KRD-{selected_loan_id:06d}')}</div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

# ---- KPI strip ----
kpi_items = [
    {"label": "Saldo",       "value": style.fmt_compact(loan["current_outstanding"])[0],
     "unit": style.fmt_compact(loan["current_outstanding"])[1]},
    {"label": "Belehnung",   "value": f"{loan['ltv_pct']:.1f}", "unit": "%"},
    {"label": "Tragbarkeit", "value": f"{loan['dsti_pct']:.1f}", "unit": "%"},
    {"label": "Tranchen",    "value": str(len(dossier["tranches"]))},
]
if risk is not None:
    kpi_items.append({"label": "Internes Rating", "value": str(int(risk["rating_internal"])),
                      "delta_html": f'<span style="color:var(--ink-3);font-size:11px">PD {risk["pd_1y"]:.4f}</span>'})

style.kpi_strip(kpi_items)

payload = {k: v.to_dict(orient="records") for k, v in dossier.items() if v is not None}
st.download_button(
    label=f"Dossier als JSON · loan_{selected_loan_id}.json",
    data=json.dumps(payload, default=str, indent=2).encode("utf-8"),
    file_name=f"dossier_loan_{selected_loan_id}.json",
    mime="application/json",
)

# ---- Tabs ----
tabs = st.tabs(["Kredit & Tranchen", "Objekt & Bewertungen", "Tragbarkeit",
                "Risikokennzahlen", "Ereignisse", "Fälle", "Dokumente",
                "Haushaltseinkommen"])

with tabs[0]:
    st.markdown("**Kredit**")
    st.dataframe(dossier["loan"].T.rename(columns={0: "Wert"}),
                 use_container_width=True, height=380)
    st.markdown(f"**Tranchenstruktur** · {len(dossier['tranches'])} Tranchen")
    if dossier["tranches"].empty:
        st.info("Keine Tranchen.")
    else:
        a, b = st.columns([1, 2])
        with a:
            fig_pie = charts.tranche_pie(dossier["tranches"])
            if fig_pie: st.plotly_chart(fig_pie, use_container_width=True)
        with b:
            fig_lad = charts.tranche_ladder_bar(dossier["tranches"])
            if fig_lad: st.plotly_chart(fig_lad, use_container_width=True)
        st.dataframe(dossier["tranches"], use_container_width=True, hide_index=True)

with tabs[1]:
    if prop is not None:
        st.markdown("**Objekt**")
        st.dataframe(dossier["property"].T.rename(columns={0: "Wert"}),
                     use_container_width=True, height=300)
    st.markdown("**Bewertungshistorie**")
    if not dossier["valuations"].empty:
        st.plotly_chart(charts.valuation_history(dossier["valuations"]),
                        use_container_width=True)
        st.dataframe(dossier["valuations"], use_container_width=True, hide_index=True)

with tabs[2]:
    st.dataframe(dossier["affordability"], use_container_width=True, hide_index=True)
with tabs[3]:
    st.dataframe(dossier["risk"], use_container_width=True, hide_index=True)
with tabs[4]:
    if not dossier["events"].empty:
        st.dataframe(dossier["events"], use_container_width=True, height=520, hide_index=True)
with tabs[5]:
    if not dossier["cases"].empty:
        st.dataframe(dossier["cases"], use_container_width=True, height=520, hide_index=True)
with tabs[6]:
    if not dossier["documents"].empty:
        st.dataframe(dossier["documents"], use_container_width=True, height=520, hide_index=True)
with tabs[7]:
    st.markdown("**Haushaltsmitglieder**")
    st.dataframe(dossier["members"], use_container_width=True, hide_index=True)
    st.markdown("**Haushaltseinkommen**")
    st.dataframe(dossier["incomes"], use_container_width=True, hide_index=True)

style.footer()
