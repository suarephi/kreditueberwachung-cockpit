"""Risikofälle: Watchlist, NPL, höchste erwartete Verluste."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import plotly.express as px     # noqa: E402

from dashboard import data, charts, style, sla_reference    # noqa: E402

st.set_page_config(page_title="Risikofälle", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Risikofälle")

style.page_head("Risikofälle",
                "Risikobehaftete Kredite",
                "Beobachtungsliste, NPL, Forbearance, höchste erwartete Verluste.")

# ---- KPI strip ----
kpis = data.portfolio_kpis()
aff = data.affordability_breakdown()
fail = int(aff[aff['pass_fail'] == 'fail']['n'].sum())      if not aff.empty else 0
exc  = int(aff[aff['pass_fail'] == 'exception']['n'].sum()) if not aff.empty else 0

el_n, el_unit = style.fmt_compact(kpis.get("total_el") or 0)
style.kpi_strip([
    {"label": "Beobachtungsliste", "value": style.fmt_int(kpis.get("n_watchlist") or 0)},
    {"label": "NPL",               "value": style.fmt_int(kpis.get("n_npl") or 0)},
    {"label": "Forbearance",       "value": style.fmt_int(kpis.get("n_forbearance") or 0)},
    {"label": "Erwarteter Verlust","value": el_n, "unit": el_unit},
    {"label": "Tragb. Fail / Ausnahme",
     "value": f"{style.fmt_int(fail)} / {style.fmt_int(exc)}"},
])

style.section_head("Beobachtungsliste · Top 200 nach erwartetem Verlust")
wl = data.watchlist(limit=200)
left, right = st.columns([3, 2], gap="medium")

with left:
    if wl.empty:
        st.info("Keine Beobachtungsfälle.")
    else:
        wl_de = wl.rename(columns={
            "loan_id": "Kredit-ID", "last_name": "Nachname", "first_name": "Vorname",
            "canton": "Kanton", "city": "Ort", "object_type": "Objekt",
            "current_outstanding": "Saldo", "ltv_pct": "Belehnung",
            "dsti_pct": "Tragbarkeit", "expected_loss": "EV",
            "pd_1y": "PD 1J", "rating_internal": "Rating",
            "npl_flag": "NPL", "forbearance_flag": "Forb.", "days_past_due": "DPD",
        })
        st.dataframe(
            wl_de.style.format({
                "Saldo": "{:,.0f}", "Belehnung": "{:.1f}",
                "Tragbarkeit": "{:.1f}", "EV": "{:,.0f}", "PD 1J": "{:.4f}",
            }).background_gradient(subset=["EV"], cmap="Reds"),
            use_container_width=True, height=520, hide_index=True,
        )

with right:
    st.markdown(
        f"""<div class="ku-cardhead" style="margin:0 0 4px"><div>
        <div class="ku-cardtitle">Belehnung vs. Tragbarkeit</div>
        <div class="ku-cardsub">Top 1 000 nach EV · Farbe = PD 1J</div></div></div>""",
        unsafe_allow_html=True,
    )
    if not wl.empty:
        st.plotly_chart(charts.ltv_dsti_scatter(wl.head(1000)), use_container_width=True)

    style.section_head("Tragbarkeitsergebnis")
    if not aff.empty:
        aff_de = aff.copy()
        aff_de["label"] = aff_de["pass_fail"].map(
            {"pass": "Bestanden", "exception": "Ausnahme", "fail": "Nicht bestanden"})
        fig = px.pie(aff_de, names="label", values="n", hole=0.55,
                     color="pass_fail",
                     color_discrete_map={"pass": style.SEV_GREEN,
                                         "exception": style.SEV_AMBER,
                                         "fail": style.SEV_RED})
        fig.update_traces(textinfo="label+percent",
                          textfont=dict(color="#FFFFFF", size=12),
                          marker=dict(line=dict(color="#FFFFFF", width=2)))
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

style.section_head("Drill-down · Kredite hinter den KPIs")
dd_a, dd_b = st.columns(2, gap="medium")
with dd_a:
    flag = st.selectbox("Risiko-Flag", ["", "watchlist", "npl", "forbearance"], key="dd_flag")
    if flag:
        df = data.loans_by_risk_flag(flag, limit=50)
        st.caption(f"Top 50 Kredite mit **{flag}**-Flag, sortiert nach EV")
        st.dataframe(df.rename(columns={
            "loan_id": "Kredit-ID", "client_id": "Kunden-ID",
            "first_name": "Vorname", "last_name": "Nachname",
            "canton": "Kanton", "object_type": "Objekt",
            "current_outstanding": "Saldo", "ltv_pct": "LTV", "dsti_pct": "DSTI",
            "expected_loss": "EV", "pd_1y": "PD 1J", "days_past_due": "DPD",
        }), hide_index=True, use_container_width=True, height=380)

with dd_b:
    pf = st.selectbox("Tragbarkeitsergebnis", ["", "fail", "exception", "pass"], key="dd_pf")
    if pf:
        df = data.loans_by_affordability(pf, limit=50)
        st.caption(f"Top 50 Kredite mit Tragbarkeit **{pf}**, sortiert nach DSTI")
        st.dataframe(df.rename(columns={
            "loan_id": "Kredit-ID", "client_id": "Kunden-ID",
            "first_name": "Vorname", "last_name": "Nachname",
            "canton": "Kanton", "object_type": "Objekt",
            "dsti_calculated": "DSTI", "dsti_threshold": "Schwelle",
            "income_basis": "Cashflow-Basis",
            "current_outstanding": "Saldo", "ltv_pct": "LTV",
        }), hide_index=True, use_container_width=True, height=380)

style.section_head("SLA-Matrix · Bearbeitungsfristen pro Auslöser")
sla_reference.render_reference(in_expander=False)

style.footer()
