"""Wertschriftendepots: Cross-Sell-Sicht für Hypothekenkunden."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import plotly.express as px     # noqa: E402

from dashboard import data, style    # noqa: E402

st.set_page_config(page_title="Wertschriften", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Wertschriften")

style.page_head("Wertschriften",
                "Depots der Hypothekenkunden",
                "Cross-Sell-Sicht: Anlagestrategie, Volumen, Asset-Allokation, Top-Positionen.")

# Probe: schema may not yet be migrated on cloud.
try:
    n_pf = int(data.query("SELECT COUNT(*) AS n FROM portfolio").iloc[0]["n"])
except Exception:
    n_pf = 0

if n_pf == 0:
    st.info("Noch keine Wertschriftendepots im Datensatz. "
            "Lokal regenerieren: `python scripts/generate.py` "
            "(Anteil via `KU_PORTFOLIO_FRAC=…`).")
    style.footer()
    st.stop()

# ---------- KPIs ----------
kpi = data.query("""
    SELECT COUNT(*) AS n_pf,
           SUM(total_value_chf)  AS total_aum,
           AVG(total_value_chf)  AS avg_aum,
           SUM(cash_chf)         AS total_cash,
           AVG(ytd_return_pct)   AS avg_ytd
      FROM portfolio
""").iloc[0]
total_aum_n, total_aum_u = style.fmt_compact(kpi["total_aum"] or 0)
avg_aum_n,   avg_aum_u   = style.fmt_compact(kpi["avg_aum"] or 0)
style.kpi_strip([
    {"label": "Depots",                 "value": style.fmt_int(int(kpi["n_pf"] or 0))},
    {"label": "Verwaltetes Vermögen",   "value": total_aum_n, "unit": total_aum_u},
    {"label": "Ø Depotvolumen",         "value": avg_aum_n,   "unit": avg_aum_u},
    {"label": "Cash-Quote (gesamt)",
     "value": f"{(float(kpi['total_cash'] or 0) / max(float(kpi['total_aum'] or 1), 1)) * 100:.1f}",
     "unit":  "%"},
    {"label": "Ø YTD-Rendite",          "value": f"{float(kpi['avg_ytd'] or 0):.1f}", "unit": "%"},
])

# ---------- Strategie-Verteilung ----------
style.section_head("Anlagestrategien · Verteilung & Volumen")
left, right = st.columns([1, 1], gap="medium")

with left:
    by_strategy = data.query("""
        SELECT strategy, COUNT(*) AS n,
               ROUND(CAST(SUM(total_value_chf)/1e6 AS numeric), 2) AS aum_mchf,
               ROUND(CAST(AVG(ytd_return_pct) AS numeric), 2) AS ytd
          FROM portfolio GROUP BY strategy
    """)
    label_map = {
        "konservativ": "Konservativ (100% Bonds)",
        "vorsichtig":  "Vorsichtig (30/70)",
        "mittel":      "Mittel (50/50)",
        "wachstum":    "Wachstum (75/25)",
        "aktien":      "Aktien (100% Equity)",
    }
    by_strategy["label"] = by_strategy["strategy"].map(label_map)
    fig = px.pie(by_strategy, names="label", values="n", hole=0.55,
                 color_discrete_sequence=style.CHART_COLORWAY)
    fig.update_traces(textinfo="label+percent",
                      textfont=dict(color="#FFFFFF", size=11),
                      marker=dict(line=dict(color="#FFFFFF", width=2)))
    fig.update_layout(height=320, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.dataframe(by_strategy.rename(columns={
        "strategy": "Strategie", "n": "Depots",
        "aum_mchf": "AuM (Mio. CHF)", "ytd": "Ø YTD %",
    })[["Strategie", "Depots", "AuM (Mio. CHF)", "Ø YTD %"]],
    hide_index=True, use_container_width=True, height=300)

# ---------- Asset-Allokation ----------
style.section_head("Asset-Allokation · gesamt")
by_ac = data.query("""
    SELECT asset_class, ROUND(CAST(SUM(market_value_chf)/1e6 AS numeric), 2) AS mchf, COUNT(*) AS positions
      FROM position GROUP BY asset_class ORDER BY mchf DESC
""")
ac_labels = {"bond": "Bond", "etf_bond": "Bond-ETF", "equity": "Aktie",
             "etf_equity": "Aktien-ETF", "cash": "Cash", "alternative": "Alt."}
by_ac["Asset-Klasse"] = by_ac["asset_class"].map(ac_labels).fillna(by_ac["asset_class"])
fig_ac = px.bar(by_ac, x="Asset-Klasse", y="mchf",
                color="Asset-Klasse", color_discrete_sequence=style.CHART_COLORWAY)
fig_ac.update_layout(height=280, showlegend=False, yaxis_title="Mio. CHF")
st.plotly_chart(fig_ac, use_container_width=True)

# ---------- Top Depots + Drill-down ----------
style.section_head("Top 50 Depots nach Volumen")
auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""
top = data.query("""
    SELECT pf.portfolio_id, pf.client_id, c.first_name, c.last_name, c.segment,
           pf.strategy, pf.total_value_chf, pf.ytd_return_pct,
           (SELECT COUNT(*) FROM position p WHERE p.portfolio_id = pf.portfolio_id) AS n_pos
      FROM portfolio pf
      JOIN client c ON c.client_id = pf.client_id
     ORDER BY pf.total_value_chf DESC LIMIT 50
""")
st.dataframe(top.rename(columns={
    "portfolio_id": "Depot-ID", "client_id": "Kunden-ID",
    "first_name": "Vorname", "last_name": "Nachname", "segment": "Segment",
    "strategy": "Strategie", "total_value_chf": "Volumen (CHF)",
    "ytd_return_pct": "YTD %", "n_pos": "#Pos.",
}).style.format({
    "Volumen (CHF)": "{:,.0f}", "YTD %": "{:.1f}",
}).background_gradient(subset=["Volumen (CHF)"], cmap="Blues"),
hide_index=True, use_container_width=True, height=420)

style.section_head("Drill-down · Positionen eines Depots")
pf_options = top["portfolio_id"].astype(int).tolist()
pf_label = {int(r["portfolio_id"]):
            f"#{int(r['portfolio_id']):05d} · {r['first_name']} {r['last_name']} · "
            f"{r['strategy']} · CHF {r['total_value_chf']:,.0f}"
            for _, r in top.iterrows()}
sel_pf = st.selectbox("Depot wählen", [0] + pf_options,
                       format_func=lambda i: ("Bitte wählen" if i == 0 else pf_label[i]))
if sel_pf:
    positions = data.query("""
        SELECT isin, name, asset_class, currency, quantity, avg_cost_chf,
               market_price_chf, market_value_chf, unrealized_pnl_chf, weight_pct
          FROM position WHERE portfolio_id = :i
         ORDER BY market_value_chf DESC
    """, {"i": int(sel_pf)})
    st.dataframe(positions.rename(columns={
        "isin": "ISIN", "name": "Instrument", "asset_class": "Asset-Klasse",
        "currency": "Währung", "quantity": "Menge",
        "avg_cost_chf": "Ø Einstand", "market_price_chf": "Kurs",
        "market_value_chf": "Marktwert", "unrealized_pnl_chf": "Unrealisierter G/V",
        "weight_pct": "Gewicht %",
    }).style.format({
        "Menge": "{:,.4f}", "Ø Einstand": "{:,.2f}", "Kurs": "{:,.2f}",
        "Marktwert": "{:,.0f}", "Unrealisierter G/V": "{:+,.0f}",
        "Gewicht %": "{:.2f}",
    }), hide_index=True, use_container_width=True, height=400)

style.footer()
