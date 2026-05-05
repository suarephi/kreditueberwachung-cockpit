"""Stresstest: Szenario-Auswahl, KPI-Verlauf, regionale Konzentration."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st         # noqa: E402

from dashboard import data, charts, style, i18n    # noqa: E402

st.set_page_config(page_title="Stresstest", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Stresstest")

LANG = i18n.current_lang()
style.page_head(i18n.t("ph_stress_crumb"), i18n.t("ph_stress_title"), i18n.t("ph_stress_sub"))

scenarios = data.stress_scenarios()
if scenarios.empty:
    st.warning(("Noch keine Stress-Szenarien gerechnet. "
                "`python scripts/run_stress.py --scenario all` ausführen.")
               if LANG == "de" else
               ("No stress scenarios computed yet. "
                "Run `python scripts/run_stress.py --scenario all`."))
    style.footer()
    st.stop()

cols = st.columns([3, 1, 1])
chosen = cols[0].selectbox(
    "Szenario" if LANG == "de" else "Scenario",
    options=scenarios["scenario_id"].tolist(),
    format_func=lambda s: scenarios.loc[scenarios["scenario_id"] == s, "name"].iloc[0],
)
sev     = scenarios.loc[scenarios["scenario_id"] == chosen, "severity"].iloc[0]
horizon = int(scenarios.loc[scenarios["scenario_id"] == chosen, "horizon_quarters"].iloc[0])

if LANG == "de":
    sev_label = {"baseline": "Basislinie", "mild": "Leicht", "moderate": "Mittel",
                 "severe": "Schwer", "extreme": "Extrem"}.get(sev, sev)
    cols[1].metric("Schweregrad", sev_label)
    cols[2].metric("Horizont",    f"{horizon} Q")
else:
    sev_label = {"baseline": "Baseline", "mild": "Mild", "moderate": "Moderate",
                 "severe": "Severe", "extreme": "Extreme"}.get(sev, sev)
    cols[1].metric("Severity", sev_label)
    cols[2].metric("Horizon",  f"{horizon} Q")

kpi = data.stress_kpi(chosen)
last = kpi.iloc[-1]

if LANG == "de":
    s_lbl = ("Engagement", "Erwarteter Verlust", "Belehnung > 80 %",
             "Tragbarkeit > 33 %", "NPL-Anteil")
else:
    s_lbl = ("Exposure", "Expected Loss", "LTV > 80 %",
             "DSTI > 33 %", "NPL share")
style.kpi_strip([
    {"label": s_lbl[0], "value": style.fmt_compact(last["total_exposure"])[0],
     "unit":  style.fmt_compact(last["total_exposure"])[1]},
    {"label": s_lbl[1], "value": style.fmt_compact(last["expected_loss_total"])[0],
     "unit":  style.fmt_compact(last["expected_loss_total"])[1]},
    {"label": s_lbl[2], "value": f"{last['share_ltv_gt80']*100:.1f}", "unit": "%"},
    {"label": s_lbl[3], "value": f"{last['share_dsti_gt33']*100:.1f}", "unit": "%"},
    {"label": s_lbl[4], "value": f"{last['npl_share']*100:.1f}",      "unit": "%"},
])

style.section_head((f"KPI-Verlauf · {chosen}" if LANG == "de"
                    else f"KPI evolution · {chosen}"))
fig_kpi = charts.stress_kpi_lines(kpi)
if fig_kpi is not None:
    st.plotly_chart(fig_kpi, use_container_width=True)

left, right = st.columns([3, 2], gap="medium")

with left:
    style.section_head("Regionale Konzentration · gestresster EV" if LANG == "de"
                       else "Regional concentration · stressed EL")
    per_canton = data.stress_per_canton(chosen)
    if not per_canton.empty:
        ref_cantons = data.query("SELECT canton_code, name_de AS canton_name FROM canton")
        per_canton  = per_canton.merge(ref_cantons, on="canton_code", how="left")
        fig_c = charts.ch_choropleth(
            per_canton.dropna(subset=["canton_code"]),
            metric_col="stressed_el", metric_label="Gestresster EV (CHF)",
        )
        st.plotly_chart(fig_c, use_container_width=True)

with right:
    style.section_head("Top 25 Belehnungssprünge" if LANG == "de" else "Top 25 LTV jumps")
    jumps = data.stress_top_jumps(chosen, limit=25)
    if not jumps.empty:
        st.dataframe(
            jumps.rename(columns={
                "loan_id": "Kredit-ID", "base_ltv": "LTV Basis",
                "stressed_ltv": "LTV gestresst", "jump": "Δ",
                "base_el": "EV Basis", "stressed_expected_loss": "EV gestresst",
            }).style.format({
                "LTV Basis": "{:.1f}", "LTV gestresst": "{:.1f}", "Δ": "{:+.1f}",
                "EV Basis": "{:,.0f}", "EV gestresst": "{:,.0f}",
            }).background_gradient(subset=["Δ"], cmap="Reds"),
            use_container_width=True, height=560, hide_index=True,
        )

style.section_head(i18n.t("dd_stress").format(scenario=chosen))
dd_a, dd_b = st.columns(2, gap="medium")

with dd_a:
    st.caption("Top 50 Belehnungssprünge mit Kunde + Objekt")
    detail = data.stress_top_jumps_detail(chosen, limit=50)
    if not detail.empty:
        st.dataframe(detail.rename(columns={
            "loan_id": "Kredit-ID",
            "first_name": "Vorname", "last_name": "Nachname",
            "canton": "Kanton", "object_type": "Objekt",
            "base_ltv": "LTV Basis", "stressed_ltv": "LTV gestresst",
            "jump": "Δ LTV",
            "base_el": "EV Basis", "stressed_expected_loss": "EV gestresst",
        }).style.format({
            "LTV Basis": "{:.1f}", "LTV gestresst": "{:.1f}", "Δ LTV": "{:+.1f}",
            "EV Basis": "{:,.0f}", "EV gestresst": "{:,.0f}",
        }).background_gradient(subset=["Δ LTV"], cmap="Reds"),
        hide_index=True, use_container_width=True, height=400)

with dd_b:
    canton_opts = sorted(per_canton["canton_code"].dropna().unique().tolist()) if not per_canton.empty else []
    sel = st.selectbox(i18n.t("dd_kanton_drill"), [""] + canton_opts, key="dd_stress_kanton")
    if sel:
        df = data.stress_loans_by_canton(chosen, sel, limit=50)
        st.caption(f"Top 50 Kredite in **{sel}** unter {chosen}")
        st.dataframe(df.rename(columns={
            "loan_id": "Kredit-ID",
            "first_name": "Vorname", "last_name": "Nachname",
            "object_type": "Objekt",
            "stressed_ltv": "LTV gestresst",
            "stressed_expected_loss": "EV gestresst",
            "covenant_breach_flag": "Covenant",
        }).style.format({
            "LTV gestresst": "{:.1f}", "EV gestresst": "{:,.0f}",
        }), hide_index=True, use_container_width=True, height=400)

style.section_head("Szenarienvergleich · letzte Periode" if LANG == "de"
                   else "Scenario comparison · last period")
comp = data.query("""
    SELECT s.scenario_id, s.name, s.severity,
           ROUND(CAST(SUM(m.stressed_expected_loss)/1e6 AS numeric), 2) AS el_mchf,
           ROUND(CAST(AVG(m.stressed_ltv)  AS numeric), 1) AS avg_stressed_ltv,
           ROUND(CAST(AVG(m.stressed_dsti) AS numeric), 1) AS avg_stressed_dsti,
           SUM(m.covenant_breach_flag)                 AS n_breaches
      FROM stress_scenario s
      JOIN stress_loan_metrics m USING(scenario_id)
     WHERE m.period = (SELECT MAX(period) FROM stress_loan_metrics WHERE scenario_id = s.scenario_id)
     GROUP BY 1, 2, 3 ORDER BY el_mchf DESC
""").rename(columns={
    "scenario_id": "Szenario-ID", "name": "Name", "severity": "Schweregrad",
    "el_mchf": "EV (Mio. CHF)",
    "avg_stressed_ltv":  "Ø LTV gestresst",
    "avg_stressed_dsti": "Ø DSTI gestresst",
    "n_breaches": "Covenant-Verletzungen",
})
st.dataframe(
    comp.style.background_gradient(subset=["EV (Mio. CHF)"], cmap="Reds"),
    use_container_width=True, hide_index=True,
)

style.footer()
