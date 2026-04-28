"""Datenprofil: Eigenschaften des synthetischen Datensatzes."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st         # noqa: E402
import pandas as pd            # noqa: E402
import plotly.express as px    # noqa: E402

from kreditueberwachung_mock import config       # noqa: E402
from dashboard import data, charts, style        # noqa: E402

st.set_page_config(page_title="Datenprofil", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Datenprofil")

style.page_head("Datenprofil",
                "Eigenschaften des synthetischen Hypothekenportfolios",
                "Volumen, Verteilungen, Tranchen-Realismus, FPRE-Index, Referenzzinsen.")

# ---- Generator-Parameter ----
style.kpi_strip([
    {"label": "Anzahl Kunden",       "value": style.fmt_int(config.N_CLIENTS)},
    {"label": "Seed",                "value": str(config.SEED)},
    {"label": "Imputierter Zinssatz","value": f"{config.IMPUTED_INTEREST_PCT:.1f}", "unit": "%"},
    {"label": "Tragb.-Schwelle",     "value": f"{config.DSTI_THRESHOLD_PCT:.0f}", "unit": "%"},
    {"label": "LTV-Spanne",          "value": "30 – 110", "unit": "%"},
])

# ---- Mengengerüst ----
style.section_head("Mengengerüst · Zeilen pro Tabelle")
tables = ["client", "address", "household", "client_household", "property",
          "valuation", "loan", "tranche", "income", "affordability_assessment",
          "risk_metrics", "event", "loan_case", "document", "audit_log",
          "fpre_index_history", "rate_history", "stress_scenario",
          "stress_loan_metrics", "stress_event"]
rows = [{"Tabelle": t, "Zeilen": int(data.query(f"SELECT COUNT(*) AS n FROM {t}").iloc[0]["n"])}
        for t in tables]
counts_df = pd.DataFrame(rows)

l, r = st.columns([2, 3], gap="medium")
with l:
    st.dataframe(counts_df.style.format({"Zeilen": "{:,.0f}".format}),
                 use_container_width=True, hide_index=True, height=520)
with r:
    fig = px.bar(counts_df.sort_values("Zeilen"),
                 x="Zeilen", y="Tabelle", orientation="h",
                 color_discrete_sequence=[style.INK_3])
    fig.update_traces(marker_line_width=0)
    fig.update_layout(height=520, xaxis_title="Zeilen", yaxis_title="", xaxis_type="log")
    st.plotly_chart(fig, use_container_width=True)

# ---- Tranchen-Realismus ----
style.section_head("Tranchen-Realismus")
left, right = st.columns(2, gap="medium")

with left:
    st.markdown("**Tranchen pro Kredit**")
    tcnt = data.query("""
        SELECT n_tranches, COUNT(*) AS n_loans,
               ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER (), 2) AS pct
          FROM (SELECT loan_id, COUNT(*) AS n_tranches FROM tranche GROUP BY loan_id)
         GROUP BY n_tranches ORDER BY n_tranches
    """).rename(columns={"n_tranches": "Tranchen", "n_loans": "Kredite", "pct": "Anteil (%)"})
    st.dataframe(tcnt.style.format({"Kredite": "{:,.0f}", "Anteil (%)": "{:.2f}"}),
                 use_container_width=True, hide_index=True, height=200)
    fig_t = charts.tranche_count_distribution(tcnt.rename(columns={"Tranchen": "n_tranches",
                                                                     "Kredite": "n_loans"}))
    if fig_t:
        st.plotly_chart(fig_t, use_container_width=True)

with right:
    st.markdown("**Tranchen-Typen-Verteilung**")
    ttype = data.query("""
        SELECT tranche_type, COUNT(*) AS n_tranches,
               ROUND(SUM(amount)/1e6, 1) AS total_mchf,
               ROUND(AVG(interest_rate_pct), 2) AS avg_rate
          FROM tranche GROUP BY 1
    """).rename(columns={"tranche_type": "Typ", "n_tranches": "Tranchen",
                          "total_mchf": "Summe (Mio. CHF)", "avg_rate": "Ø Zins (%)"})
    st.dataframe(ttype.style.format({"Tranchen": "{:,.0f}",
                                      "Summe (Mio. CHF)": "{:,.1f}",
                                      "Ø Zins (%)": "{:.2f}"}),
                 use_container_width=True, hide_index=True, height=160)

    by_size = data.query("""
        SELECT CASE
                 WHEN current_outstanding < 300000  THEN '< 300k'
                 WHEN current_outstanding < 800000  THEN '300-800k'
                 WHEN current_outstanding < 1500000 THEN '800k-1.5M'
                 WHEN current_outstanding < 2500000 THEN '1.5-2.5M'
                 ELSE '> 2.5M' END                  AS size_bucket,
               n_tranches, COUNT(*) AS n_loans
          FROM (SELECT l.current_outstanding,
                       (SELECT COUNT(*) FROM tranche WHERE loan_id = l.loan_id) AS n_tranches
                  FROM loan l)
         GROUP BY size_bucket, n_tranches ORDER BY size_bucket, n_tranches
    """)
    if not by_size.empty:
        order = ["< 300k", "300-800k", "800k-1.5M", "1.5-2.5M", "> 2.5M"]
        fig = px.bar(by_size, x="size_bucket", y="n_loans", color="n_tranches",
                     category_orders={"size_bucket": order},
                     color_continuous_scale=style.CHOROPLETH_STOPS,
                     labels={"size_bucket": "Saldo-Bucket", "n_loans": "Kredite",
                             "n_tranches": "Tranchen"})
        fig.update_traces(marker_line_width=0)
        fig.update_layout(height=320, barmode="stack",
                          coloraxis_colorbar=dict(title="Tranchen", thickness=12))
        st.plotly_chart(fig, use_container_width=True)

# ---- Belehnungs-Buckets ----
style.section_head("Belehnungsverteilung · Buckets")
ltv_dist = data.query("""
    SELECT
      SUM(CASE WHEN ltv_pct<50               THEN 1 ELSE 0 END) AS "lt50",
      SUM(CASE WHEN ltv_pct BETWEEN 50 AND 60 THEN 1 ELSE 0 END) AS "50-60",
      SUM(CASE WHEN ltv_pct BETWEEN 60 AND 75 THEN 1 ELSE 0 END) AS "60-75",
      SUM(CASE WHEN ltv_pct BETWEEN 75 AND 80 THEN 1 ELSE 0 END) AS "75-80",
      SUM(CASE WHEN ltv_pct BETWEEN 80 AND 90 THEN 1 ELSE 0 END) AS "80-90",
      SUM(CASE WHEN ltv_pct BETWEEN 90 AND 100 THEN 1 ELSE 0 END) AS "90-100",
      SUM(CASE WHEN ltv_pct>100              THEN 1 ELSE 0 END) AS "gt100"
    FROM loan
""").iloc[0]
buckets = pd.DataFrame({
    "Bucket": ["< 50 %", "50-60 %", "60-75 %", "75-80 %",
                "80-90 %", "90-100 %", "> 100 %"],
    "Kredite": [int(ltv_dist[k]) for k in
                 ["lt50", "50-60", "60-75", "75-80", "80-90", "90-100", "gt100"]],
    "Charakter": ["Abgezahlt", "Mittel", "Bulk", "Reg. Grenze",
                   "Sonderfälle", "Seltene Ausnahmen", "Underwater"],
})
buckets["Anteil (%)"] = buckets["Kredite"] / buckets["Kredite"].sum() * 100

bar_l, bar_r = st.columns([3, 2])
with bar_l:
    fig = px.bar(buckets, x="Bucket", y="Kredite", color="Charakter",
                 color_discrete_sequence=style.CHART_COLORWAY)
    fig.update_traces(marker_line_width=0)
    fig.update_layout(height=380, xaxis_title="", yaxis_title="Kredite",
                      legend=dict(orientation="h", y=-0.20))
    st.plotly_chart(fig, use_container_width=True)
with bar_r:
    st.dataframe(buckets.style.format({"Kredite": "{:,.0f}", "Anteil (%)": "{:.2f}"}),
                 use_container_width=True, hide_index=True, height=380)

# ---- FPRE Index ----
style.section_head("FPRE-Index · Verlauf nach Kanton (EFH)")
fpre = data.query("""
    SELECT region_code, period, index_value FROM fpre_index_history
     WHERE object_type='EFH'
       AND region_code IN ('ZH','BE','VD','GE','TI','VS','BS','LU','ZG','GR')
     ORDER BY period, region_code
""")
if not fpre.empty:
    fig = px.line(fpre, x="period", y="index_value", color="region_code",
                  color_discrete_sequence=style.CHART_COLORWAY,
                  labels={"period": "Periode", "index_value": "Index (Basis 100)",
                          "region_code": "Kanton"})
    fig.update_layout(height=380, legend=dict(orientation="h", y=-0.25),
                       xaxis=dict(showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

# ---- Rates ----
style.section_head("Referenzzinsen")
rates = data.query("""
    SELECT rate_date, rate_name, rate_pct FROM rate_history
     WHERE rate_name IN ('SARON_3M','FIX_5Y','FIX_10Y') ORDER BY rate_date
""")
if not rates.empty:
    fig = px.line(rates, x="rate_date", y="rate_pct", color="rate_name",
                  color_discrete_map={"SARON_3M": style.INK_2,
                                      "FIX_5Y":   style.ACCENT,
                                      "FIX_10Y":  style.SEV_GREEN},
                  labels={"rate_date": "Datum", "rate_pct": "Zins (%)",
                          "rate_name": "Referenzzins"})
    fig.update_layout(height=320, legend=dict(orientation="h", y=-0.20))
    st.plotly_chart(fig, use_container_width=True)

style.footer()
