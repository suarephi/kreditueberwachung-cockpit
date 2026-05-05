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
from dashboard import data, charts, style, i18n  # noqa: E402

st.set_page_config(page_title="Datenprofil", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Datenprofil")

LANG = i18n.current_lang()
style.page_head(i18n.t("ph_profile_crumb"),
                "Eigenschaften des synthetischen Hypothekenportfolios" if LANG == "de"
                else "Properties of the synthetic mortgage portfolio",
                "Volumen, Verteilungen, Tranchen-Realismus, FPRE-Index, Referenzzinsen." if LANG == "de"
                else "Volume, distributions, tranche realism, FPRE index, reference rates.")

if LANG == "de":
    p_lbl = ("Anzahl Kunden", "Seed", "Imputierter Zinssatz",
             "Tragb.-Schwelle", "LTV-Spanne")
else:
    p_lbl = ("Number of clients", "Seed", "Imputed interest rate",
             "Affordability threshold", "LTV range")
style.kpi_strip([
    {"label": p_lbl[0], "value": style.fmt_int(config.N_CLIENTS)},
    {"label": p_lbl[1], "value": str(config.SEED)},
    {"label": p_lbl[2], "value": f"{config.IMPUTED_INTEREST_PCT:.1f}", "unit": "%"},
    {"label": p_lbl[3], "value": f"{config.DSTI_THRESHOLD_PCT:.0f}", "unit": "%"},
    {"label": p_lbl[4], "value": "30 – 110", "unit": "%"},
])

style.section_head("Mengengerüst · Zeilen pro Tabelle" if LANG == "de"
                   else "Volume · rows per table")
tables = ["client", "address", "household", "client_household", "property",
          "valuation", "loan", "tranche", "income", "affordability_assessment",
          "risk_metrics", "event", "loan_case", "document", "audit_log",
          "fpre_index_history", "rate_history", "stress_scenario",
          "stress_loan_metrics", "stress_event"]
tbl_lbl = "Tabelle" if LANG == "de" else "Table"
row_lbl = "Zeilen" if LANG == "de" else "Rows"
rows = [{tbl_lbl: t, row_lbl: int(data.query(f"SELECT COUNT(*) AS n FROM {t}").iloc[0]["n"])}
        for t in tables]
counts_df = pd.DataFrame(rows)

l, r = st.columns([2, 3], gap="medium")
with l:
    st.dataframe(counts_df.style.format({row_lbl: "{:,.0f}".format}),
                 use_container_width=True, hide_index=True, height=520)
with r:
    fig = px.bar(counts_df.sort_values(row_lbl),
                 x=row_lbl, y=tbl_lbl, orientation="h",
                 color_discrete_sequence=[style.INK_3])
    fig.update_traces(marker_line_width=0)
    fig.update_layout(height=520, xaxis_title=row_lbl, yaxis_title="", xaxis_type="log")
    st.plotly_chart(fig, use_container_width=True)

style.section_head("Tranchen-Realismus" if LANG == "de" else "Tranche realism")
left, right = st.columns(2, gap="medium")

with left:
    st.markdown("**Tranchen pro Kredit**" if LANG == "de" else "**Tranches per loan**")
    if LANG == "de":
        tr_cols = {"n_tranches": "Tranchen", "n_loans": "Kredite", "pct": "Anteil (%)"}
        loans_lbl, share_lbl = "Kredite", "Anteil (%)"
    else:
        tr_cols = {"n_tranches": "Tranches", "n_loans": "Loans", "pct": "Share (%)"}
        loans_lbl, share_lbl = "Loans", "Share (%)"
    tcnt = data.query("""
        SELECT n_tranches, COUNT(*) AS n_loans,
               ROUND(CAST(COUNT(*)*100.0/SUM(COUNT(*)) OVER () AS numeric), 2) AS pct
          FROM (SELECT loan_id, COUNT(*) AS n_tranches FROM tranche GROUP BY loan_id) t
         GROUP BY n_tranches ORDER BY n_tranches
    """).rename(columns=tr_cols)
    st.dataframe(tcnt.style.format({loans_lbl: "{:,.0f}", share_lbl: "{:.2f}"}),
                 use_container_width=True, hide_index=True, height=200)
    fig_t = charts.tranche_count_distribution(tcnt.rename(columns={
        list(tr_cols.values())[0]: "n_tranches",
        list(tr_cols.values())[1]: "n_loans",
    }))
    if fig_t:
        st.plotly_chart(fig_t, use_container_width=True)

with right:
    st.markdown("**Tranchen-Typen-Verteilung**" if LANG == "de"
                else "**Tranche-type distribution**")
    if LANG == "de":
        tt_cols = {"tranche_type": "Typ", "n_tranches": "Tranchen",
                   "total_mchf": "Summe (Mio. CHF)", "avg_rate": "Ø Zins (%)"}
        tr_lbl, sum_lbl, rate_lbl = "Tranchen", "Summe (Mio. CHF)", "Ø Zins (%)"
    else:
        tt_cols = {"tranche_type": "Type", "n_tranches": "Tranches",
                   "total_mchf": "Total (CHF mn)", "avg_rate": "Avg rate (%)"}
        tr_lbl, sum_lbl, rate_lbl = "Tranches", "Total (CHF mn)", "Avg rate (%)"
    ttype = data.query("""
        SELECT tranche_type, COUNT(*) AS n_tranches,
               ROUND(CAST(SUM(amount)/1e6      AS numeric), 1) AS total_mchf,
               ROUND(CAST(AVG(interest_rate_pct) AS numeric), 2) AS avg_rate
          FROM tranche GROUP BY tranche_type
    """).rename(columns=tt_cols)
    st.dataframe(ttype.style.format({tr_lbl: "{:,.0f}",
                                      sum_lbl: "{:,.1f}",
                                      rate_lbl: "{:.2f}"}),
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
        if LANG == "de":
            chart_lbl = {"size_bucket": "Saldo-Bucket", "n_loans": "Kredite",
                         "n_tranches": "Tranchen"}
            cb_title = "Tranchen"
        else:
            chart_lbl = {"size_bucket": "Balance bucket", "n_loans": "Loans",
                         "n_tranches": "Tranches"}
            cb_title = "Tranches"
        fig = px.bar(by_size, x="size_bucket", y="n_loans", color="n_tranches",
                     category_orders={"size_bucket": order},
                     color_continuous_scale=style.CHOROPLETH_STOPS,
                     labels=chart_lbl)
        fig.update_traces(marker_line_width=0)
        fig.update_layout(height=320, barmode="stack",
                          coloraxis_colorbar=dict(title=cb_title, thickness=12))
        st.plotly_chart(fig, use_container_width=True)

style.section_head("Belehnungsverteilung · Buckets" if LANG == "de"
                   else "LTV distribution · buckets")
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
if LANG == "de":
    char_labels = ["Abgezahlt", "Mittel", "Bulk", "Reg. Grenze",
                   "Sonderfälle", "Seltene Ausnahmen", "Underwater"]
    col_b, col_l, col_c, col_a = "Bucket", "Kredite", "Charakter", "Anteil (%)"
else:
    char_labels = ["Paid down", "Middle", "Bulk", "Reg. limit",
                   "Special cases", "Rare exceptions", "Underwater"]
    col_b, col_l, col_c, col_a = "Bucket", "Loans", "Profile", "Share (%)"
buckets = pd.DataFrame({
    col_b: ["< 50 %", "50-60 %", "60-75 %", "75-80 %",
            "80-90 %", "90-100 %", "> 100 %"],
    col_l: [int(ltv_dist[k]) for k in
            ["lt50", "50-60", "60-75", "75-80", "80-90", "90-100", "gt100"]],
    col_c: char_labels,
})
buckets[col_a] = buckets[col_l] / buckets[col_l].sum() * 100

bar_l_col, bar_r_col = st.columns([3, 2])
with bar_l_col:
    fig = px.bar(buckets, x=col_b, y=col_l, color=col_c,
                 color_discrete_sequence=style.CHART_COLORWAY)
    fig.update_traces(marker_line_width=0)
    fig.update_layout(height=380, xaxis_title="", yaxis_title=col_l,
                      legend=dict(orientation="h", y=-0.20))
    st.plotly_chart(fig, use_container_width=True)
with bar_r_col:
    st.dataframe(buckets.style.format({col_l: "{:,.0f}", col_a: "{:.2f}"}),
                 use_container_width=True, hide_index=True, height=380)

style.section_head("FPRE-Index · Verlauf nach Kanton (EFH)" if LANG == "de"
                   else "FPRE index · trajectory by canton (EFH)")
fpre = data.query("""
    SELECT region_code, period, index_value FROM fpre_index_history
     WHERE object_type='EFH'
       AND region_code IN ('ZH','BE','VD','GE','TI','VS','BS','LU','ZG','GR')
     ORDER BY period, region_code
""")
if not fpre.empty:
    fpre_lbl = ({"period": "Periode", "index_value": "Index (Basis 100)", "region_code": "Kanton"}
                if LANG == "de" else
                {"period": "Period", "index_value": "Index (base 100)", "region_code": "Canton"})
    fig = px.line(fpre, x="period", y="index_value", color="region_code",
                  color_discrete_sequence=style.CHART_COLORWAY,
                  labels=fpre_lbl)
    fig.update_layout(height=380, legend=dict(orientation="h", y=-0.25),
                       xaxis=dict(showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

style.section_head("Referenzzinsen" if LANG == "de" else "Reference rates")
rates = data.query("""
    SELECT rate_date, rate_name, rate_pct FROM rate_history
     WHERE rate_name IN ('SARON_3M','FIX_5Y','FIX_10Y') ORDER BY rate_date
""")
if not rates.empty:
    rate_lbl = ({"rate_date": "Datum", "rate_pct": "Zins (%)", "rate_name": "Referenzzins"}
                if LANG == "de" else
                {"rate_date": "Date", "rate_pct": "Rate (%)", "rate_name": "Reference rate"})
    fig = px.line(rates, x="rate_date", y="rate_pct", color="rate_name",
                  color_discrete_map={"SARON_3M": style.INK_2,
                                      "FIX_5Y":   style.ACCENT,
                                      "FIX_10Y":  style.SEV_GREEN},
                  labels=rate_lbl)
    fig.update_layout(height=320, legend=dict(orientation="h", y=-0.20))
    st.plotly_chart(fig, use_container_width=True)

style.footer()
