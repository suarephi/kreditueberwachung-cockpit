"""Wertschriftendepots: Cross-Sell-Sicht für Hypothekenkunden."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import plotly.express as px     # noqa: E402

from dashboard import data, style, i18n    # noqa: E402

st.set_page_config(page_title="Wertschriften", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Wertschriften")

LANG = i18n.current_lang()
style.page_head(i18n.t("ph_securities_crumb"),
                i18n.t("ph_securities_title"),
                i18n.t("ph_securities_sub"))

# Probe: schema may not yet be migrated on cloud.
try:
    n_pf = int(data.query("SELECT COUNT(*) AS n FROM portfolio").iloc[0]["n"])
except Exception:
    n_pf = 0

if n_pf == 0:
    st.info(("Noch keine Wertschriftendepots im Datensatz. "
             "Lokal regenerieren: `python scripts/generate.py` "
             "(Anteil via `KU_PORTFOLIO_FRAC=…`).") if LANG == "de"
            else ("No securities portfolios in the dataset yet. "
                  "Regenerate locally with `python scripts/generate.py` "
                  "(share via `KU_PORTFOLIO_FRAC=…`)."))
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
    {"label": i18n.t("sec_kpi_count"),       "value": style.fmt_int(int(kpi["n_pf"] or 0))},
    {"label": i18n.t("sec_kpi_aum"),         "value": total_aum_n, "unit": total_aum_u},
    {"label": i18n.t("sec_kpi_avg_aum"),     "value": avg_aum_n,   "unit": avg_aum_u},
    {"label": i18n.t("sec_kpi_cash"),
     "value": f"{(float(kpi['total_cash'] or 0) / max(float(kpi['total_aum'] or 1), 1)) * 100:.1f}",
     "unit":  "%"},
    {"label": i18n.t("sec_kpi_ytd"),         "value": f"{float(kpi['avg_ytd'] or 0):.1f}", "unit": "%"},
])

style.section_head(i18n.t("sec_section_strategy"))
left, right = st.columns([1, 1], gap="medium")

with left:
    by_strategy = data.query("""
        SELECT strategy, COUNT(*) AS n,
               ROUND(CAST(SUM(total_value_chf)/1e6 AS numeric), 2) AS aum_mchf,
               ROUND(CAST(AVG(ytd_return_pct) AS numeric), 2) AS ytd
          FROM portfolio GROUP BY strategy
    """)
    if LANG == "de":
        label_map = {
            "konservativ": "Konservativ (100 % Bonds)",
            "vorsichtig":  "Vorsichtig (30/70)",
            "mittel":      "Mittel (50/50)",
            "wachstum":    "Wachstum (75/25)",
            "aktien":      "Aktien (100 % Equity)",
        }
    else:
        label_map = {
            "konservativ": "Conservative (100 % Bonds)",
            "vorsichtig":  "Cautious (30/70)",
            "mittel":      "Balanced (50/50)",
            "wachstum":    "Growth (75/25)",
            "aktien":      "Equity (100 %)",
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
    if LANG == "de":
        col_strategy, col_depots, col_aum, col_ytd = "Strategie", "Depots", "AuM (Mio. CHF)", "Ø YTD %"
    else:
        col_strategy, col_depots, col_aum, col_ytd = "Strategy", "Portfolios", "AuM (CHF mn)", "Avg YTD %"
    st.dataframe(by_strategy.rename(columns={
        "strategy": col_strategy, "n": col_depots,
        "aum_mchf": col_aum, "ytd": col_ytd,
    })[[col_strategy, col_depots, col_aum, col_ytd]],
    hide_index=True, use_container_width=True, height=300)

style.section_head(i18n.t("sec_section_alloc"))
by_ac = data.query("""
    SELECT asset_class, ROUND(CAST(SUM(market_value_chf)/1e6 AS numeric), 2) AS mchf, COUNT(*) AS positions
      FROM position GROUP BY asset_class ORDER BY mchf DESC
""")
if LANG == "de":
    ac_labels = {"bond": "Bond", "etf_bond": "Bond-ETF", "equity": "Aktie",
                 "etf_equity": "Aktien-ETF", "cash": "Cash", "alternative": "Alt."}
    ac_col, y_axis = "Asset-Klasse", "Mio. CHF"
else:
    ac_labels = {"bond": "Bond", "etf_bond": "Bond ETF", "equity": "Equity",
                 "etf_equity": "Equity ETF", "cash": "Cash", "alternative": "Alt."}
    ac_col, y_axis = "Asset Class", "CHF mn"
by_ac[ac_col] = by_ac["asset_class"].map(ac_labels).fillna(by_ac["asset_class"])
fig_ac = px.bar(by_ac, x=ac_col, y="mchf",
                color=ac_col, color_discrete_sequence=style.CHART_COLORWAY)
fig_ac.update_layout(height=280, showlegend=False, yaxis_title=y_axis)
st.plotly_chart(fig_ac, use_container_width=True)

style.section_head(i18n.t("sec_section_top"))
auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""
top = data.query("""
    SELECT pf.portfolio_id, pf.client_id, c.first_name, c.last_name, c.segment,
           pf.strategy, pf.total_value_chf, pf.ytd_return_pct,
           (SELECT COUNT(*) FROM position p WHERE p.portfolio_id = pf.portfolio_id) AS n_pos
      FROM portfolio pf
      JOIN client c ON c.client_id = pf.client_id
     ORDER BY pf.total_value_chf DESC LIMIT 50
""")
vol_col = i18n.col("total_value_chf", "portfolio", LANG)
ytd_col = i18n.col("ytd_return_pct", "portfolio", LANG)
n_pos_col = "#Pos." if LANG == "de" else "#Pos."
top_renamed = i18n.rename(top, "portfolio").rename(columns={"n_pos": n_pos_col})
st.dataframe(top_renamed.style.format({
    vol_col: "{:,.0f}", ytd_col: "{:.1f}",
}).background_gradient(subset=[vol_col], cmap="Blues"),
hide_index=True, use_container_width=True, height=420)

style.section_head(i18n.t("sec_section_drill"))
pf_options = top["portfolio_id"].astype(int).tolist()
pf_label = {int(r["portfolio_id"]):
            f"#{int(r['portfolio_id']):05d} · {r['first_name']} {r['last_name']} · "
            f"{r['strategy']} · CHF {r['total_value_chf']:,.0f}"
            for _, r in top.iterrows()}
sel_pf = st.selectbox(i18n.t("sec_select_portfolio"), [0] + pf_options,
                       format_func=lambda i: (i18n.t("sec_pick") if i == 0 else pf_label[i]))
if sel_pf:
    positions = data.query("""
        SELECT isin, name, asset_class, currency, quantity, avg_cost_chf,
               market_price_chf, market_value_chf, unrealized_pnl_chf, weight_pct
          FROM position WHERE portfolio_id = :i
         ORDER BY market_value_chf DESC
    """, {"i": int(sel_pf)})
    qty_col = i18n.col("quantity", "position", LANG)
    cost_col = i18n.col("avg_cost_chf", "position", LANG)
    price_col = i18n.col("market_price_chf", "position", LANG)
    mv_col = i18n.col("market_value_chf", "position", LANG)
    pnl_col = i18n.col("unrealized_pnl_chf", "position", LANG)
    wt_col = i18n.col("weight_pct", "position", LANG)
    st.dataframe(i18n.rename(positions, "position").style.format({
        qty_col: "{:,.4f}", cost_col: "{:,.2f}", price_col: "{:,.2f}",
        mv_col: "{:,.0f}", pnl_col: "{:+,.0f}", wt_col: "{:.2f}",
    }), hide_index=True, use_container_width=True, height=400)

style.footer()
