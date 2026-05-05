"""Risikofälle: Watchlist, NPL, höchste erwartete Verluste."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import plotly.express as px     # noqa: E402

from dashboard import data, charts, style, sla_reference, i18n    # noqa: E402

st.set_page_config(page_title="Risikofälle", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Risikofälle")

LANG = i18n.current_lang()
style.page_head(i18n.t("ph_risk_crumb"), i18n.t("ph_risk_title"), i18n.t("ph_risk_sub"))

kpis = data.portfolio_kpis()
aff = data.affordability_breakdown()
fail = int(aff[aff['pass_fail'] == 'fail']['n'].sum())      if not aff.empty else 0
exc  = int(aff[aff['pass_fail'] == 'exception']['n'].sum()) if not aff.empty else 0

el_n, el_unit = style.fmt_compact(kpis.get("total_el") or 0)
if LANG == "de":
    risk_kpi_lbl = ("Beobachtungsliste", "NPL", "Forbearance",
                    "Erwarteter Verlust", "Tragb. Fail / Ausnahme")
else:
    risk_kpi_lbl = ("Watchlist", "NPL", "Forbearance",
                    "Expected Loss", "Affordability fail / exception")
style.kpi_strip([
    {"label": risk_kpi_lbl[0], "value": style.fmt_int(kpis.get("n_watchlist") or 0)},
    {"label": risk_kpi_lbl[1], "value": style.fmt_int(kpis.get("n_npl") or 0)},
    {"label": risk_kpi_lbl[2], "value": style.fmt_int(kpis.get("n_forbearance") or 0)},
    {"label": risk_kpi_lbl[3], "value": el_n, "unit": el_unit},
    {"label": risk_kpi_lbl[4],
     "value": f"{style.fmt_int(fail)} / {style.fmt_int(exc)}"},
])

style.section_head("Beobachtungsliste · Top 200 nach erwartetem Verlust" if LANG == "de"
                   else "Watchlist · Top 200 by expected loss")
wl = data.watchlist(limit=200)
left, right = st.columns([3, 2], gap="medium")

with left:
    if wl.empty:
        st.info("Keine Beobachtungsfälle." if LANG == "de" else "No watchlist cases.")
    else:
        if LANG == "de":
            ren = {
                "loan_id": "Kredit-ID", "last_name": "Nachname", "first_name": "Vorname",
                "canton": "Kanton", "city": "Ort", "object_type": "Objekt",
                "current_outstanding": "Saldo", "ltv_pct": "Belehnung",
                "dsti_pct": "Tragbarkeit", "expected_loss": "EV",
                "pd_1y": "PD 1J", "rating_internal": "Rating",
                "npl_flag": "NPL", "forbearance_flag": "Forb.", "days_past_due": "DPD",
            }
            saldo_c, lehn_c, trag_c, ev_c, pd_c = "Saldo", "Belehnung", "Tragbarkeit", "EV", "PD 1J"
        else:
            ren = {
                "loan_id": "Loan ID", "last_name": "Last Name", "first_name": "First Name",
                "canton": "Canton", "city": "City", "object_type": "Object",
                "current_outstanding": "Balance", "ltv_pct": "LTV",
                "dsti_pct": "DSTI", "expected_loss": "EL",
                "pd_1y": "PD 1Y", "rating_internal": "Rating",
                "npl_flag": "NPL", "forbearance_flag": "Forb.", "days_past_due": "DPD",
            }
            saldo_c, lehn_c, trag_c, ev_c, pd_c = "Balance", "LTV", "DSTI", "EL", "PD 1Y"
        wl_de = wl.rename(columns=ren)
        st.dataframe(
            wl_de.style.format({
                saldo_c: "{:,.0f}", lehn_c: "{:.1f}",
                trag_c: "{:.1f}", ev_c: "{:,.0f}", pd_c: "{:.4f}",
            }).background_gradient(subset=[ev_c], cmap="Reds"),
            use_container_width=True, height=520, hide_index=True,
        )

with right:
    title_lhs = "Belehnung vs. Tragbarkeit" if LANG == "de" else "LTV vs. DSTI"
    title_sub = ("Top 1 000 nach EV · Farbe = PD 1J" if LANG == "de"
                 else "Top 1,000 by EL · color = PD 1Y")
    st.markdown(
        f"""<div class="ku-cardhead" style="margin:0 0 4px"><div>
        <div class="ku-cardtitle">{title_lhs}</div>
        <div class="ku-cardsub">{title_sub}</div></div></div>""",
        unsafe_allow_html=True,
    )
    if not wl.empty:
        st.plotly_chart(charts.ltv_dsti_scatter(wl.head(1000)), use_container_width=True)

    style.section_head("Tragbarkeitsergebnis" if LANG == "de" else "Affordability result")
    if not aff.empty:
        aff_de = aff.copy()
        if LANG == "de":
            aff_de["label"] = aff_de["pass_fail"].map(
                {"pass": "Bestanden", "exception": "Ausnahme", "fail": "Nicht bestanden"})
        else:
            aff_de["label"] = aff_de["pass_fail"].map(
                {"pass": "Pass", "exception": "Exception", "fail": "Fail"})
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

style.section_head(i18n.t("dd_loans_kpi"))
dd_a, dd_b = st.columns(2, gap="medium")
with dd_a:
    flag = st.selectbox(i18n.t("dd_pick_flag"), ["", "watchlist", "npl", "forbearance"], key="dd_flag")
    if flag:
        df = data.loans_by_risk_flag(flag, limit=50)
        st.caption((f"Top 50 Kredite mit **{flag}**-Flag, sortiert nach EV" if LANG == "de"
                    else f"Top 50 loans with **{flag}** flag, sorted by EL"))
        st.dataframe(i18n.rename(df, "loan").rename(columns={
            "first_name": i18n.col("first_name", "client", LANG),
            "last_name": i18n.col("last_name", "client", LANG),
            "canton": i18n.col("canton", "address", LANG),
            "object_type": i18n.col("object_type", "property", LANG),
            "expected_loss": i18n.col("expected_loss", "risk_metrics", LANG),
            "pd_1y": i18n.col("pd_1y", "risk_metrics", LANG),
            "days_past_due": i18n.col("days_past_due", "risk_metrics", LANG),
        }), hide_index=True, use_container_width=True, height=380)

with dd_b:
    pf = st.selectbox(i18n.t("dd_pick_pf"), ["", "fail", "exception", "pass"], key="dd_pf")
    if pf:
        df = data.loans_by_affordability(pf, limit=50)
        st.caption((f"Top 50 Kredite mit Tragbarkeit **{pf}**, sortiert nach DSTI"
                    if LANG == "de"
                    else f"Top 50 loans with affordability **{pf}**, sorted by DSTI"))
        st.dataframe(i18n.rename(df, "loan").rename(columns={
            "first_name": i18n.col("first_name", "client", LANG),
            "last_name": i18n.col("last_name", "client", LANG),
            "canton": i18n.col("canton", "address", LANG),
            "object_type": i18n.col("object_type", "property", LANG),
            "dsti_calculated": i18n.col("dsti_calculated", "affordability_assessment", LANG),
            "dsti_threshold": i18n.col("dsti_threshold", "affordability_assessment", LANG),
            "income_basis": i18n.col("income_basis", "affordability_assessment", LANG),
        }), hide_index=True, use_container_width=True, height=380)

style.section_head("SLA-Matrix · Bearbeitungsfristen pro Auslöser" if LANG == "de"
                   else "SLA matrix · deadlines per trigger")
sla_reference.render_reference(in_expander=False)

style.footer()
