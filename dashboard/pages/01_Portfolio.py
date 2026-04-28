"""Portfolio: Schweiz-Heatmap + Rangliste + Verteilungen."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st             # noqa: E402
import plotly.express as px        # noqa: E402

from dashboard import data, charts, coords, style    # noqa: E402

st.set_page_config(page_title="Portfolio", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Übersicht")  # Portfolio is reached from nav cards on Übersicht

style.page_head("Portfolio",
                "Hypothekenbestand im Detail",
                "Schweiz-Heatmap, Rangliste und Verteilungen über das gesamte Hypothekarbuch.")

# ---------- KPI strip ----------
kpis = data.portfolio_kpis()
vol_n, vol_unit = style.fmt_compact(kpis["total_outstanding"])
el_n,  el_unit  = style.fmt_compact(kpis.get("total_el") or 0)

style.kpi_strip([
    {"label": "Aktive Kredite",        "value": style.fmt_int(kpis["n_loans"])},
    {"label": "Gesamtengagement",      "value": vol_n, "unit": vol_unit},
    {"label": "Ø Belehnung",           "value": f"{kpis['avg_ltv']:.1f}", "unit": "%"},
    {"label": "Belehnung > 80 %",      "value": f"{kpis['share_ltv_gt80']*100:.1f}", "unit": "%"},
    {"label": "Tragbarkeit > 33 %",    "value": f"{kpis['share_dsti_gt33']*100:.1f}", "unit": "%"},
])

# ---------- Heatmap ----------
style.section_head("Schweiz-Heatmap", count="26 Kantone · live")

per_canton = data.per_canton_metrics()
per_canton = per_canton[per_canton["canton_code"].notna()].copy()

ctrl1, ctrl2 = st.columns([2, 2])
metric_label = ctrl1.selectbox(
    "Kanton-Kennzahl",
    options=[
        ("CHF / m²  ·  Ø aktueller Marktwert",  "chf_per_sqm",       ",.0f"),
        ("Bankengagement  ·  Gesamtsaldo",      "total_outstanding", ",.0f"),
        ("Anzahl Kredite",                      "n_loans",           ",.0f"),
        ("Ø Belehnung (%)",                     "avg_ltv",           ".1f"),
        ("Ø Tragbarkeit (%)",                   "avg_dsti",          ".1f"),
        ("Erwarteter Verlust (CHF)",            "total_el",          ",.0f"),
    ],
    format_func=lambda x: x[0],
)
plz_overlay = ctrl2.selectbox(
    "PLZ-Überlagerung",
    options=[
        ("Keine",                                                  None,                None),
        ("Bubbles · Grösse = Engagement · Farbe = CHF/m²",         "total_outstanding", "chf_per_sqm"),
        ("Bubbles · Grösse = Anzahl Kredite · Farbe = CHF/m²",     "n_loans",           "chf_per_sqm"),
        ("Bubbles · Grösse = Engagement · Farbe = Ø Belehnung",    "total_outstanding", "avg_ltv"),
    ],
    format_func=lambda x: x[0],
)

if not per_canton.empty:
    title = metric_label[0].split("  ·")[0].strip()
    if plz_overlay[1] is None:
        fig = charts.ch_choropleth(per_canton, metric_col=metric_label[1],
                                    metric_label=title)
    else:
        plz_geo = coords.plz_with_coords()
        plz_df  = plz_geo.merge(data.per_plz_metrics(),
                                on=["postal_code", "city"], how="left")
        fig = charts.ch_choropleth_with_plz_overlay(
            per_canton, plz_df,
            canton_metric=metric_label[1], canton_label=title,
            plz_metric_size=plz_overlay[1], plz_metric_color=plz_overlay[2],
        )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Rangliste + Distributions ----------
style.section_head("Rangliste & Verteilungen")

left, right = st.columns([3, 2], gap="medium")

with left:
    rank = per_canton.copy()
    rank["Engagement (Mio. CHF)"] = rank["total_outstanding"] / 1e6
    rank["EV (Tsd. CHF)"]         = rank["total_el"] / 1e3
    rank = rank[[
        "canton_code", "canton_name", "n_loans", "Engagement (Mio. CHF)",
        "avg_ltv", "avg_dsti", "chf_per_sqm", "EV (Tsd. CHF)", "n_watchlist", "n_npl",
    ]].rename(columns={
        "canton_code": "Kanton", "canton_name": "Name", "n_loans": "Kredite",
        "avg_ltv": "Ø LTV", "avg_dsti": "Ø DSTI", "chf_per_sqm": "CHF/m²",
        "n_watchlist": "Watchlist", "n_npl": "NPL",
    }).sort_values("Engagement (Mio. CHF)", ascending=False)
    st.dataframe(
        rank.style.format({
            "Engagement (Mio. CHF)": "{:,.1f}",
            "Ø LTV":      "{:.1f}",
            "Ø DSTI":     "{:.1f}",
            "CHF/m²":     "{:,.0f}",
            "EV (Tsd. CHF)": "{:,.0f}",
        }).background_gradient(subset=["Engagement (Mio. CHF)"], cmap="Greys"),
        use_container_width=True, height=560, hide_index=True,
    )

with right:
    obj = data.object_type_mix()
    label_map = {"EFH": "Einfamilienhaus", "ETW": "Eigentumswohnung",
                 "MFH": "Mehrfamilienhaus", "Ferienwohnung": "Ferienwohnung",
                 "Gewerbe": "Gewerbe", "Bauland": "Bauland"}
    obj["label"] = obj["object_type"].map(label_map).fillna(obj["object_type"])
    fig_obj = px.pie(obj, values="n", names="label", hole=0.55,
                     color_discrete_sequence=style.CHART_COLORWAY)
    fig_obj.update_traces(textinfo="label+percent",
                           textfont=dict(color="#FFFFFF", size=11),
                           marker=dict(line=dict(color="#FFFFFF", width=2)))
    fig_obj.update_layout(height=260, showlegend=False)
    st.plotly_chart(fig_obj, use_container_width=True)

    tcnt = data.tranche_count_per_loan()
    fig_t = charts.tranche_count_distribution(tcnt)
    if fig_t:
        st.plotly_chart(fig_t, use_container_width=True)

    ltv = data.ltv_distribution()
    st.plotly_chart(charts.histogram(ltv["ltv_pct"], xlabel="LTV (%)", height=200),
                    use_container_width=True)

    dsti = data.dsti_distribution()
    st.plotly_chart(charts.histogram(dsti["dsti_pct"], xlabel="DSTI (%)", height=200,
                                     color=style.SEV_RED),
                    use_container_width=True)

style.footer()
