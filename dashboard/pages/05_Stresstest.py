"""Stresstest: Szenario-Auswahl, KPI-Verlauf, regionale Konzentration."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st         # noqa: E402

from dashboard import data, charts, style    # noqa: E402

st.set_page_config(page_title="Stresstest", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Stresstest")

style.page_head("Stresstest",
                "Immobilienpreisindex-Overlay",
                "8 Szenarien · 12-Quartals-Horizont · neutral-slate-Färbung pro gestresster EV.")

scenarios = data.stress_scenarios()
if scenarios.empty:
    st.warning("Noch keine Stress-Szenarien gerechnet. "
               "`python scripts/run_stress.py --scenario all` ausführen.")
    style.footer()
    st.stop()

cols = st.columns([3, 1, 1])
chosen = cols[0].selectbox(
    "Szenario", options=scenarios["scenario_id"].tolist(),
    format_func=lambda s: scenarios.loc[scenarios["scenario_id"] == s, "name"].iloc[0],
)
sev     = scenarios.loc[scenarios["scenario_id"] == chosen, "severity"].iloc[0]
horizon = int(scenarios.loc[scenarios["scenario_id"] == chosen, "horizon_quarters"].iloc[0])

sev_de = {"baseline": "Basislinie", "mild": "Leicht", "moderate": "Mittel",
          "severe": "Schwer", "extreme": "Extrem"}.get(sev, sev)
cols[1].metric("Schweregrad", sev_de)
cols[2].metric("Horizont",    f"{horizon} Q")

kpi = data.stress_kpi(chosen)
last = kpi.iloc[-1]

style.kpi_strip([
    {"label": "Engagement",         "value": style.fmt_compact(last["total_exposure"])[0],
     "unit":  style.fmt_compact(last["total_exposure"])[1]},
    {"label": "Erwarteter Verlust", "value": style.fmt_compact(last["expected_loss_total"])[0],
     "unit":  style.fmt_compact(last["expected_loss_total"])[1]},
    {"label": "Belehnung > 80 %",   "value": f"{last['share_ltv_gt80']*100:.1f}", "unit": "%"},
    {"label": "Tragbarkeit > 33 %", "value": f"{last['share_dsti_gt33']*100:.1f}", "unit": "%"},
    {"label": "NPL-Anteil",         "value": f"{last['npl_share']*100:.1f}",      "unit": "%"},
])

style.section_head(f"KPI-Verlauf · {chosen}")
fig_kpi = charts.stress_kpi_lines(kpi)
if fig_kpi is not None:
    st.plotly_chart(fig_kpi, use_container_width=True)

left, right = st.columns([3, 2], gap="medium")

with left:
    style.section_head("Regionale Konzentration · gestresster EV")
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
    style.section_head("Top 25 Belehnungssprünge")
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

style.section_head("Szenarienvergleich · letzte Periode")
comp = data.query("""
    SELECT s.scenario_id, s.name, s.severity,
           ROUND(SUM(m.stressed_expected_loss)/1e6, 2) AS el_mchf,
           ROUND(AVG(m.stressed_ltv), 1)               AS avg_stressed_ltv,
           ROUND(AVG(m.stressed_dsti), 1)              AS avg_stressed_dsti,
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
