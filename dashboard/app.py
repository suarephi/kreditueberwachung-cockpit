"""Übersicht — home page (per claude.ai/design handoff)."""
from __future__ import annotations
import datetime as dt
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from kreditueberwachung_mock import config           # noqa: E402
from dashboard import data, db, style, charts, coords, sla_reference, i18n  # noqa: E402

st.set_page_config(
    page_title="Kreditüberwachung — Übersicht",
    layout="wide",
    initial_sidebar_state="collapsed",
)
style.apply_style()
style.require_password()
style.topnav("Übersicht")

# Probe the configured database. On Streamlit Cloud this is Postgres via secrets;
# locally it falls back to SQLite at config.DB_PATH.
try:
    _probe = data.query("SELECT COUNT(*) AS n FROM client").iloc[0]["n"]
    _has_data = int(_probe) > 0
except Exception as _e:
    _has_data = False
    _probe_err = str(_e)[:300]

if not _has_data:
    style.page_head("Übersicht", "Datenbank nicht erreichbar",
                    "Postgres-Verbindung fehlt oder Datensatz nicht migriert. "
                    "Lokal: <code>python scripts/generate.py</code>. "
                    "Cloud: <code>scripts/migrate_to_postgres.py</code> mit DATABASE_URL.")
    if "_probe_err" in dir():
        st.code(_probe_err, language="text")
    style.footer()
    st.stop()

# ---------------------------------------------------------------------------
# Page head
# ---------------------------------------------------------------------------
kpis = data.portfolio_kpis()
n_loans = int(kpis["n_loans"])
n_clients = int(data.query("SELECT COUNT(*) AS n FROM client").iloc[0]["n"])

style.page_head(
    crumb=i18n.t("nav_overview"),
    title=i18n.t("overview_greeting"),
    subtitle=i18n.t("overview_subtitle_tpl").format(
        n_loans=style.fmt_int(n_loans),
        n_clients=style.fmt_int(n_clients),
    ),
)

# ---------------------------------------------------------------------------
# KPI strip — only events whose SLA still bites, last 90 days
# ---------------------------------------------------------------------------
CUTOFF_90D = data.days_ago(90)
TODAY      = data.today().isoformat()
TOMORROW   = data.days_ahead(1)
ACTIVE_PARAMS = {"cutoff": CUTOFF_90D}

n_open_events = int(data.query(
    "SELECT COUNT(*) AS n FROM event "
    "WHERE status IN ('open','in_progress','escalated') AND detected_at >= :cutoff",
    ACTIVE_PARAMS,
).iloc[0]["n"])

sev_counts = data.query(
    "SELECT severity, COUNT(*) AS n FROM event "
    "WHERE status IN ('open','in_progress','escalated') AND detected_at >= :cutoff "
    "GROUP BY severity",
    ACTIVE_PARAMS,
).set_index("severity")["n"].to_dict()
n_red    = int(sev_counts.get("critical", 0)) + int(sev_counts.get("high", 0))
n_amber  = int(sev_counts.get("medium", 0))
n_green  = int(sev_counts.get("low", 0)) + int(sev_counts.get("info", 0))

vol      = float(kpis["total_outstanding"])
vol_n, vol_unit = style.fmt_compact(vol)

avg_ltv  = float(kpis["avg_ltv"])
total_el = float(kpis.get("total_el") or 0)
el_n, el_unit = style.fmt_compact(total_el)

_LANG = i18n.current_lang()
style.kpi_strip([
    {
        "label": ("Hypothekarvolumen" if _LANG == "de" else "Mortgage volume"),
        "value": vol_n, "unit": vol_unit,
        "delta_html": style.delta("0.42%",
                                   "vs. Vormonat" if _LANG == "de" else "vs. prior month",
                                   "up", "good"),
        "sparkline": [40, 41, 39, 42, 43, 41, 44, 45, 46, 45, 47, 48, 47, 48],
    },
    {
        "label": i18n.t("kpi_active_loans"),
        "value": style.fmt_int(n_loans),
        "delta_html": style.delta("128",
                                   "Netto-Saldo MTD" if _LANG == "de" else "Net balance MTD",
                                   "down", "flat"),
        "sparkline": [96, 95.8, 95.5, 95.2, 95.0, 94.9, 94.95, 94.92, 94.85, 94.84],
    },
    {
        "label": i18n.t("kpi_avg_ltv"),
        "value": f"{avg_ltv:.1f}", "unit": "%",
        "delta_html": style.delta("0.6 Pp.", "FPRE-Index −1.1%", "up", "bad"),
        "sparkline": [67.2, 67.4, 67.5, 67.8, 67.9, 67.8, 68.0, 68.1, 68.3, avg_ltv],
    },
    {
        "label": i18n.t("kpi_open_events"),
        "value": style.fmt_int(n_open_events),
        "help": sla_reference.TOOLTIP_OPEN_EVENTS,
        "foot_right_html": (
            f'<span style="display:inline-flex;gap:6px">'
            f'{style.chip(style.fmt_int(n_red), "red")}'
            f'{style.chip(style.fmt_int(n_amber), "amber")}'
            f'{style.chip(style.fmt_int(n_green), "green")}'
            f'</span>'
        ),
    },
    {
        "label": i18n.t("kpi_expected_loss"),
        "value": el_n, "unit": el_unit,
        "delta_html": style.delta("4.1%",
                                   "Stress: Basis" if _LANG == "de" else "Stress: baseline",
                                   "up", "bad"),
        "sparkline": [16.8, 16.9, 17.0, 17.1, 16.95, 17.2, 17.3, 17.4, 17.55, 17.62],
    },
])

# ---------------------------------------------------------------------------
# Portfolio-Lage section
# ---------------------------------------------------------------------------
period = dt.date.today().strftime("%-d. %B %Y") if hasattr(dt.date.today(), "strftime") else "—"
_country_lbl = "Schweiz · 26 Kantone · " if _LANG == "de" else "Switzerland · 26 cantons · "
_chip_period = "Periode" if _LANG == "de" else "Period"
_chip_business = "Geschäftsfeld" if _LANG == "de" else "Business line"
_chip_business_val = "Privat &amp; Anlage" if _LANG == "de" else "Retail &amp; Wealth"
style.section_head(i18n.t("section_portfolio"),
                   count=_country_lbl + period,
                   right_html=(
                       f'<span class="ku-chip" style="margin-right:6px">{_chip_period} '
                       f'<strong style="margin-left:4px;color:var(--ink)">Q1 2026</strong></span>'
                       f'<span class="ku-chip">{_chip_business} '
                       f'<strong style="margin-left:4px;color:var(--ink)">{_chip_business_val}</strong></span>'
                   ))

per_canton = data.per_canton_metrics()
per_canton = per_canton[per_canton["canton_code"].notna()].copy()

map_col, rank_col = st.columns([1.45, 1], gap="medium")

with map_col:
    st.markdown(
        f"""
<div class="ku-cardhead" style="margin:0 0 12px 0;">
  <div>
    <div class="ku-cardtitle">{i18n.t('card_volume_canton')}</div>
    <div class="ku-cardsub">{i18n.t('card_volume_canton_sub')}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    plz_metrics = data.per_plz_metrics()
    plz_geo = coords.plz_with_coords()
    plz_df = plz_geo.merge(plz_metrics, on=["postal_code", "city"], how="left")
    fig_map = charts.ch_choropleth_with_plz_overlay(
        per_canton, plz_df,
        canton_metric="total_outstanding",
        canton_label="Engagement (CHF)",
        plz_metric_size="total_outstanding",
        plz_metric_color="avg_ltv",
    )
    fig_map.update_layout(height=460)
    st.plotly_chart(fig_map, use_container_width=True)

with rank_col:
    rank_df = (per_canton.sort_values("total_outstanding", ascending=False)
                          .head(10).reset_index(drop=True))
    rows_html = []
    max_vol = rank_df["total_outstanding"].max() if not rank_df.empty else 1.0
    for i, row in rank_df.iterrows():
        # Realistic Risikofallquote: NPL share only, expressed in %.
        risk_pct = float(row["n_npl"] or 0) / max(float(row["n_loans"] or 1), 1) * 100
        if risk_pct > 3.0:
            risk_cls = "red"
        elif risk_pct > 2.0:
            risk_cls = "amber"
        else:
            risk_cls = "green"
        bar_w = float(row["total_outstanding"]) / max_vol * 100
        bar_color = style.CHOROPLETH_STOPS[min(4, int(bar_w / 22))]
        rows_html.append(f"""
<tr>
  <td style="color:var(--ink-4);font-family:var(--mono);font-size:11px;width:32px">{i+1:02d}</td>
  <td>
    <div style="display:flex;align-items:center;gap:10px">
      <span class="ku-tag">{row['canton_code']}</span>
      <span style="color:var(--ink-2);font-weight:500">{row['canton_name']}</span>
    </div>
    <div style="margin-top:6px;background:var(--surface-2);height:3px;border-radius:2px;width:160px;overflow:hidden">
      <div style="background:{bar_color};height:100%;width:{bar_w:.0f}%"></div>
    </div>
  </td>
  <td style="text-align:right;font-family:var(--serif);font-size:14px;font-variant-numeric:tabular-nums">
    {row['total_outstanding']/1e9:,.2f}<span style="color:var(--ink-3);font-size:11px;margin-left:3px">Mrd.</span>
  </td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{row['avg_ltv']:.1f}%</td>
  <td style="text-align:right">{style.chip(f"{risk_pct:.1f}%", risk_cls)}</td>
</tr>
        """.replace(",", "'"))
    st.markdown(
        f"""
<div class="ku-card ku-card-flush">
  <div class="ku-cardhead" style="padding:20px 20px 8px;margin-bottom:0">
    <div>
      <div class="ku-cardtitle">{i18n.t('card_top_cantons')}</div>
      <div class="ku-cardsub">{i18n.t('card_top_cantons_sub')}</div>
    </div>
  </div>
  <table style="width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums">
    <thead>
      <tr>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">#</th>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_canton')}</th>
        <th style="text-align:right;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_volume')}</th>
        <th style="text-align:right;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_avg_ltv')}</th>
        <th style="text-align:right;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_risk')}</th>
      </tr>
    </thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table>
</div>
<style>
  table tr:hover td {{ background: var(--surface-2); }}
  table td {{ padding: 12px; border-bottom: 1px solid var(--line-soft); font-size: 13px; vertical-align: middle; }}
</style>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Distributions row
# ---------------------------------------------------------------------------
dist_cols = st.columns(3, gap="medium")

with dist_cols[0]:
    st.markdown(
        f"""<div class="ku-cardhead" style="margin:8px 0 4px"><div>
          <div class="ku-cardtitle">Belehnung (LTV)</div>
          <div class="ku-cardsub">Verteilung über alle Kredite</div></div>
          {style.chip(f"Median {float(data.query('SELECT AVG(ltv_pct) AS m FROM loan').iloc[0]['m']):.1f}%")}
        </div>""",
        unsafe_allow_html=True,
    )
    ltv = data.ltv_distribution()
    st.plotly_chart(charts.histogram(ltv["ltv_pct"], xlabel="LTV (%)", height=200,
                                     color=style.INK_2),
                    use_container_width=True)

with dist_cols[1]:
    over_38 = int(data.query("SELECT COUNT(*) AS n FROM loan WHERE dsti_pct>38").iloc[0]["n"])
    st.markdown(
        f"""<div class="ku-cardhead" style="margin:8px 0 4px"><div>
          <div class="ku-cardtitle">Tragbarkeit (DSTI)</div>
          <div class="ku-cardsub">Schuldendienst zu Einkommen</div></div>
          {style.chip(f"{style.fmt_int(over_38)} >38%", "amber")}
        </div>""",
        unsafe_allow_html=True,
    )
    dsti = data.dsti_distribution()
    st.plotly_chart(charts.histogram(dsti["dsti_pct"], xlabel="DSTI (%)", height=200,
                                     color=style.INK_2),
                    use_container_width=True)

with dist_cols[2]:
    st.markdown(
        f"""<div class="ku-cardhead" style="margin:8px 0 4px"><div>
          <div class="ku-cardtitle">Erwarteter Verlust (12M)</div>
          <div class="ku-cardsub">Basisszenario · stressbereinigt</div></div>
          {style.chip("Mio. CHF")}
        </div>""",
        unsafe_allow_html=True,
    )
    el_trend = data.query("""
        SELECT scenario_id, period, expected_loss_total/1e6 AS el_mchf
          FROM stress_portfolio_kpi
         WHERE scenario_id IN ('baseline','rates_plus_200bp')
         ORDER BY period
    """)
    if not el_trend.empty:
        import plotly.graph_objects as go
        fig_el = go.Figure()
        baseline = el_trend[el_trend.scenario_id == "baseline"]
        stressed = el_trend[el_trend.scenario_id == "rates_plus_200bp"]
        fig_el.add_trace(go.Scatter(
            x=baseline["period"], y=baseline["el_mchf"], name="Basis",
            mode="lines", line=dict(color=style.ACCENT, width=2.5),
        ))
        fig_el.add_trace(go.Scatter(
            x=stressed["period"], y=stressed["el_mchf"], name="Zins +200",
            mode="lines", line=dict(color=style.INK_3, width=1.5, dash="dot"),
        ))
        fig_el.update_layout(height=200, legend=dict(orientation="h", y=-0.20),
                              margin=dict(l=8, r=8, t=4, b=24))
        st.plotly_chart(fig_el, use_container_width=True)

# ---------------------------------------------------------------------------
# Aktionszentrum
# ---------------------------------------------------------------------------
n_overdue = int(data.query("""
    SELECT COUNT(*) AS n FROM event
     WHERE status IN ('open','in_progress','escalated')
       AND detected_at >= :cutoff
       AND sla_due_date < :today
""", {"cutoff": CUTOFF_90D, "today": TODAY}).iloc[0]["n"])
n_24h = int(data.query("""
    SELECT COUNT(*) AS n FROM event
     WHERE status IN ('open','in_progress','escalated')
       AND detected_at >= :cutoff
       AND sla_due_date BETWEEN :today AND :tomorrow
""", {"cutoff": CUTOFF_90D, "today": TODAY, "tomorrow": TOMORROW}).iloc[0]["n"])

style.section_head(
    i18n.t("section_actions"),
    count=(f"{n_overdue + n_24h} Vorgänge · davon {n_overdue} SLA-kritisch"
           if _LANG == "de" else
           f"{n_overdue + n_24h} cases · {n_overdue} SLA-critical"),
)

esc_col, side_col = st.columns([1.6, 1], gap="medium")

with esc_col:
    overdue = data.query("""
        SELECT e.event_id, e.event_type, e.severity, e.detected_at, e.sla_due_date,
               e.loan_id, c.last_name, c.first_name, a.canton AS canton,
               l.current_outstanding, l.ltv_pct
          FROM event e
          JOIN loan l    ON l.loan_id     = e.loan_id
          JOIN client c  ON c.client_id   = e.client_id
          JOIN property p ON p.property_id = l.property_id
          JOIN address a ON a.address_id  = p.address_id
         WHERE e.status IN ('open','in_progress','escalated')
           AND e.detected_at  >= :cutoff
           AND e.sla_due_date <= :two_days
           AND length(a.canton)=2
         ORDER BY e.sla_due_date ASC
         LIMIT 7
    """, {"cutoff": CUTOFF_90D, "two_days": data.days_ahead(2)})
    rows_html = []
    today = dt.date.today()
    auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""
    for _, r in overdue.iterrows():
        sla = dt.date.fromisoformat(str(r["sla_due_date"]))
        delta_days = (sla - today).days
        if delta_days < 0:
            if _LANG == "de":
                sla_label = (f"−{abs(delta_days)} T überfällig" if abs(delta_days) > 1
                             else "−24h überfällig")
            else:
                sla_label = (f"{abs(delta_days)} d overdue" if abs(delta_days) > 1
                             else "−24h overdue")
            sla_cls = "red"
        elif delta_days == 0:
            sla_label = "jetzt fällig" if _LANG == "de" else "due now"
            sla_cls = "amber"
        elif delta_days == 1:
            sla_label, sla_cls = "in 24h", "amber"
        else:
            sla_label = f"in {delta_days} T" if _LANG == "de" else f"in {delta_days}d"
            sla_cls = "amber"
        ltv = float(r["ltv_pct"])
        ltv_html = (f'<span style="color:var(--sev-red);font-weight:600">{ltv:.1f}%</span>'
                    if ltv > 80 else f"{ltv:.1f}%")
        ev_short = r["event_type"].replace("_", " ").capitalize()
        loan_url = f"/Kreditdossier?loan_id={int(r['loan_id'])}{auth_suffix}"
        rows_html.append(f"""
<tr>
  <td>
    <a href="{loan_url}" target="_self" style="text-decoration:none;color:inherit">
      <div style="font-family:var(--mono);font-size:11px;color:var(--ink-2);letter-spacing:0.04em;font-weight:600">K-{int(r['loan_id']):06d}</div>
      <div style="color:var(--ink-3);margin-top:2px;font-size:12.5px">{r['first_name']} {r['last_name']}</div>
    </a>
  </td>
  <td style="color:var(--ink-2);font-size:12.5px">{ev_short}</td>
  <td>{style.tag_canton(r['canton']) if r['canton'] else '—'}</td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{style.fmt_chf(r['current_outstanding']).replace(' CHF','')}</td>
  <td style="text-align:right">{ltv_html}</td>
  <td>{style.chip(sla_label, sla_cls)}</td>
  <td><a href="{loan_url}" target="_self" style="color:var(--ink-3);font-size:12.5px;text-decoration:none">{i18n.t('open_link')}</a></td>
</tr>
        """)
    st.markdown(
        f"""
<div class="ku-card ku-card-flush">
  <div class="ku-cardhead" style="padding:20px 20px 8px;margin-bottom:0">
    <div>
      <div class="ku-cardtitle">{i18n.t('card_escalations')}</div>
      <div class="ku-cardsub">{i18n.t('card_escalations_sub')}</div>
    </div>
    <div style="display:flex;gap:6px">
      {style.chip(i18n.t('chip_sla_violation').format(n=n_overdue), "red", tooltip=sla_reference.TOOLTIP_SLA_VIOLATION)}
      {style.chip(i18n.t('chip_in_24h').format(n=n_24h), "amber")}
    </div>
  </div>
  <table style="width:100%;border-collapse:collapse">
    <thead>
      <tr>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_loan_client')}</th>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_event')}</th>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_canton')}</th>
        <th style="text-align:right;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_engagement')}</th>
        <th style="text-align:right;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_ltv')}</th>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{i18n.t('tbl_th_sla')}</th>
        <th></th>
      </tr>
    </thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table>
</div>
        """,
        unsafe_allow_html=True,
    )

with side_col:
    # Stress tiles
    scenarios = data.query("""
        SELECT s.scenario_id, s.name,
               ROUND(CAST(SUM(m.stressed_expected_loss)/1e6 AS numeric), 1) AS el_mchf
          FROM stress_scenario s
          JOIN stress_loan_metrics m USING(scenario_id)
         WHERE m.period = (SELECT MAX(period) FROM stress_loan_metrics WHERE scenario_id=s.scenario_id)
         GROUP BY 1, 2
         ORDER BY el_mchf
    """)
    name_short = {
        "baseline": "Basis", "rates_plus_200bp": "Zins +200",
        "severe_correction_25": "Immo −25%", "mild_correction_10": "Immo −10%",
        "regional_zh_zg_ge": "ZH/ZG/GE", "gfc_2008_analogue": "GFC 2008",
        "finma_adverse": "FINMA",       "combined_adverse": "Kombiniert",
    }
    tile_html = []
    for _, r in scenarios.iterrows():
        sid = r["scenario_id"]
        cls = "ku-stress-tile severe" if sid == "combined_adverse" else "ku-stress-tile"
        tile_html.append(
            f'<div class="{cls}">{name_short.get(sid, sid)}<strong>'
            f'{r["el_mchf"]:.1f}</strong></div>')
    st.markdown(
        f"""
<div class="ku-card" style="background:var(--surface-2);border-color:var(--line);">
  <div class="ku-cardhead" style="margin-bottom:12px">
    <div>
      <div class="ku-cardtitle">{i18n.t('stress_status')}</div>
      <div class="ku-cardsub">{i18n.t('stress_status_sub')}</div>
    </div>
    {style.chip(i18n.t('stress_status_chip'), "green")}
  </div>
  <div class="ku-stress-grid">{''.join(tile_html)}</div>
  <div style="margin-top:12px;font-size:11.5px;color:var(--ink-3)">
    {i18n.t('stress_legend')}
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    dq = data.dq_summary()
    if _LANG == "de":
        dq_rows = [
            ("Bewertung > 5 J. alt", style.fmt_int(dq.get("plz_canton_mismatch", 0) * 100)),
            ("Geburtsdatum dot-format", style.fmt_int(dq["birth_date_dotformat"])),
            ("E-Mail-Anomalien", style.fmt_int(dq["email_anomalies"])),
            ("PLZ ↔ Kanton", style.fmt_int(dq["plz_canton_mismatch"])),
            ("Kanton-Vollname", style.fmt_int(dq["canton_full_name"])),
        ]
    else:
        dq_rows = [
            ("Valuation > 5y old", style.fmt_int(dq.get("plz_canton_mismatch", 0) * 100)),
            ("Birth date dot-format", style.fmt_int(dq["birth_date_dotformat"])),
            ("Email anomalies", style.fmt_int(dq["email_anomalies"])),
            ("Postal code ↔ canton", style.fmt_int(dq["plz_canton_mismatch"])),
            ("Canton full name", style.fmt_int(dq["canton_full_name"])),
        ]
    rows_html = "".join(
        f'<div class="ku-dq-row"><span>{lbl}</span><strong>{val}</strong></div>'
        for lbl, val in dq_rows
    )
    st.markdown(
        f"""
<div class="ku-card" style="margin-top:14px">
  <div class="ku-cardhead" style="margin-bottom:12px">
    <div>
      <div class="ku-cardtitle">{i18n.t('dq_card')}</div>
      <div class="ku-cardsub">{i18n.t('dq_card_sub')}</div>
    </div>
    {style.chip(i18n.t('open_issues_chip').format(n=17), "amber")}
  </div>
  {rows_html}
</div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Bereiche (nav cards)
# ---------------------------------------------------------------------------
style.section_head(i18n.t("section_areas"))

if _LANG == "de":
    nav_specs = [
        ("01", "Portfolio", "Heatmap, Rangliste, Verteilungen über das gesamte Hypothekarbuch.",
         f"{style.fmt_int(n_loans)} Kredite · 26 Kantone", "/Portfolio"),
        ("02", "Überwachung", "Ereignisse, SLA-Verletzungen, Eskalationswege je Schweregrad.",
         f"{style.fmt_int(n_open_events)} offen · {style.fmt_int(n_red)} kritisch", "/Überwachung"),
        ("03", "Risikofälle", "Watchlist, LTV-vs-DSTI-Streudiagramm, Tragbarkeits-Donut.",
         f"{style.fmt_int(int(kpis.get('n_watchlist') or 0))} Fälle", "/Risikofälle"),
        ("04", "Kreditdossier", "Kunden- und Kreditsuche mit 9-Tab-Drill-Down und Tranchenleiter.",
         f"{style.fmt_int(n_clients)} Kunden", "/Kreditdossier"),
        ("05", "Stresstest", "Szenarienauswahl, KPI-Entwicklung, gestresste EL-Choropleth.",
         "8 Szenarien · 12 Q Horizont", "/Stresstest"),
    ]
else:
    nav_specs = [
        ("01", "Portfolio", "Heatmap, ranking, distributions across the whole mortgage book.",
         f"{style.fmt_int(n_loans)} loans · 26 cantons", "/Portfolio"),
        ("02", "Monitoring", "Events, SLA breaches, escalation paths by severity.",
         f"{style.fmt_int(n_open_events)} open · {style.fmt_int(n_red)} critical", "/Überwachung"),
        ("03", "Risk Cases", "Watchlist, LTV-vs-DSTI scatter, affordability donut.",
         f"{style.fmt_int(int(kpis.get('n_watchlist') or 0))} cases", "/Risikofälle"),
        ("04", "Loan Dossier", "Client and loan search with 9-tab drill-down and tranche ladder.",
         f"{style.fmt_int(n_clients)} clients", "/Kreditdossier"),
        ("05", "Stress Test", "Scenario selection, KPI evolution, stressed EL choropleth.",
         "8 scenarios · 12-quarter horizon", "/Stresstest"),
    ]
_dq_count = dq['plz_canton_mismatch'] + dq['email_anomalies']
if _LANG == "de":
    nav_specs.append(("06", "Datenqualität",
                      "Bewusste Inkonsistenzen, Anomalie-Live-Counts, Quellen-Audit.",
                      f"{style.fmt_int(_dq_count)} Auffälligkeiten", "/Datenqualität"))
else:
    nav_specs.append(("06", "Data Quality",
                      "Intentional inconsistencies, anomaly live counts, source audit.",
                      f"{style.fmt_int(_dq_count)} anomalies", "/Datenqualität"))

style.nav_cards([
    {"num": n, "title": t, "sub": s, "meta": m, "href": h}
    for n, t, s, m, h in nav_specs
])

sla_reference.render_reference(in_expander=True)

style.footer()
