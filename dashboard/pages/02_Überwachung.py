"""Überwachung: severity strip, SLA-Verletzungen, Eskalationspfad, Donut, Heatmap, Queue."""
from __future__ import annotations
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st        # noqa: E402

from dashboard import data, charts, style, i18n    # noqa: E402

st.set_page_config(page_title="Überwachung", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Überwachung")

# ---------------------------------------------------------------------------
sev_df  = data.open_events_by_severity()
sev_map = dict(zip(sev_df["severity"], sev_df["n"]))
n_total = int(sum(sev_map.values()))
n_red   = int(sev_map.get("critical", 0)) + int(sev_map.get("high", 0))

LANG = i18n.current_lang()
style.page_head(
    crumb=i18n.t("ph_monitoring_crumb"),
    title=("Ereignisstrom & SLA" if LANG == "de" else "Event stream & SLA"),
    subtitle=((f"{style.fmt_int(n_total)} offene Ereignisse "
               f"· {style.fmt_int(n_red)} kritisch oder hoch "
               f"· Pipeline V12.4.") if LANG == "de"
              else (f"{style.fmt_int(n_total)} open events "
                    f"· {style.fmt_int(n_red)} critical or high "
                    f"· Pipeline V12.4.")),
)

# ---------- Severity key bar (replaces KPI strip) ----------
if LANG == "de":
    labels = [
        ("critical", "Kritisch · S5"),
        ("high",     "Hoch · S4"),
        ("medium",   "Mittel · S3"),
        ("low",      "Niedrig · S2"),
        ("info",     "Information · S1"),
    ]
else:
    labels = [
        ("critical", "Critical · S5"),
        ("high",     "High · S4"),
        ("medium",   "Medium · S3"),
        ("low",      "Low · S2"),
        ("info",     "Info · S1"),
    ]
style.kpi_strip([
    {"label": lbl, "value": style.fmt_int(sev_map.get(sev, 0))}
    for sev, lbl in labels
])

# ---------- Ereignisstrom strip (96 cells × 5 rows) ----------
style.section_head("Ereignisstrom · 7 Tage" if LANG == "de" else "Event stream · 7 days")

import datetime as _dt
import pandas as _pd
_evts = data.query(
    "SELECT severity, detected_at FROM event WHERE detected_at >= :cutoff",
    {"cutoff": data.days_ago(7)},
)
intensity = defaultdict(lambda: defaultdict(int))
if not _evts.empty:
    _now  = _dt.datetime.now()
    _ts   = _pd.to_datetime(_evts["detected_at"], errors="coerce")
    _mask = _ts.notna()
    if _mask.any():
        _bucket = ((_now - _ts[_mask]).dt.total_seconds() / (1.75 * 3600)).astype(int)
        for sev, b in zip(_evts.loc[_mask, "severity"], _bucket):
            if 0 <= int(b) < 96:
                intensity[sev][95 - int(b)] += 1

severity_order = ["critical", "high", "medium", "low", "info"]
sev_label_de = {"critical": "S5 · Kritisch", "high": "S4 · Hoch",
                "medium":   "S3 · Mittel",   "low":  "S2 · Niedrig",
                "info":     "S1 · Information"}
sev_color = {
    "critical": style.SEV_RED, "high": "#A04A28", "medium": style.SEV_AMBER,
    "low": style.SEV_GREEN, "info": style.SEV_BLUE,
}
strip_rows = []
all_counts = [intensity[s][i] for s in severity_order for i in range(96)]
mx = max(all_counts) if all_counts else 1
for sev in severity_order:
    cells = []
    for i in range(96):
        n = intensity[sev][i]
        op = (n / mx) if mx else 0
        if op < 0.04:
            cells.append('<div style="background:var(--surface-2);border-radius:2px"></div>')
        else:
            cells.append(
                f'<div style="background:{sev_color[sev]};opacity:{0.25 + op*0.75:.2f};'
                f'border-radius:2px" title="{n}"></div>'
            )
    strip_rows.append(f"""
<div style="display:grid;grid-template-columns:80px 1fr;gap:10px;margin-bottom:4px;align-items:center">
  <div style="font-size:10.5px;text-transform:uppercase;letter-spacing:0.06em;
              color:var(--ink-3);font-family:var(--mono)">{sev_label_de[sev]}</div>
  <div style="display:grid;grid-template-columns:repeat(96,1fr);gap:2px;height:18px">
    {''.join(cells)}
  </div>
</div>
    """)

st.markdown(
    f"""
<div class="ku-card">
  {''.join(strip_rows)}
  <div style="display:grid;grid-template-columns:80px 1fr;gap:10px;margin-top:8px">
    <div></div>
    <div style="display:grid;grid-template-columns:repeat(8,1fr);font-size:10.5px;
                color:var(--ink-4);font-family:var(--mono);letter-spacing:0.04em">
      <span>−7 T</span><span>−6 T</span><span>−5 T</span><span>−4 T</span>
      <span>−3 T</span><span>−2 T</span><span>−1 T</span><span style="text-align:right">jetzt</span>
    </div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

# ---------- 3-card row: SLA / Funnel / Donut ----------
style.section_head("Mix")  # English is the same
left, mid, right = st.columns([1, 1, 1], gap="medium")

with left:
    if not sev_df.empty:
        st.plotly_chart(charts.severity_bar(sev_df), use_container_width=True)

with mid:
    funnel_df = data.query("""
        SELECT
          (SELECT COUNT(*) FROM event)                                  AS ausgeloest,
          (SELECT COUNT(*) FROM event WHERE status<>'open')             AS triagiert,
          (SELECT COUNT(*) FROM event
           WHERE status IN ('in_progress','escalated','closed_resolved','waived')) AS bearbeitung,
          (SELECT COUNT(*) FROM event WHERE status IN ('escalated','closed_resolved')) AS eskaliert,
          (SELECT COUNT(*) FROM event WHERE status='closed_resolved')   AS massnahme
    """).iloc[0]
    stages = [
        ("Ausgelöst",      int(funnel_df["ausgeloest"]),    style.INK_2),
        ("Triagiert",      int(funnel_df["triagiert"]),     "#4F535C"),
        ("In Bearbeitung", int(funnel_df["bearbeitung"]),   style.INK_3),
        ("Eskaliert",      int(funnel_df["eskaliert"]),     style.ACCENT),
        ("Massnahme",      int(funnel_df["massnahme"]),     style.SEV_RED),
    ]
    mx_v = max(s[1] for s in stages) or 1
    rows = []
    for name, v, c in stages:
        pct = v / mx_v * 100
        rows.append(f"""
<div style="display:grid;grid-template-columns:140px 1fr;gap:12px;margin-bottom:8px;align-items:center">
  <div>
    <div style="font-size:13px;color:var(--ink-2);font-weight:500">{name}</div>
    <div style="font-size:11px;color:var(--ink-4);font-variant-numeric:tabular-nums">{style.fmt_int(v)}</div>
  </div>
  <div style="position:relative;height:24px;background:var(--surface-2);border-radius:4px;overflow:hidden">
    <div style="background:{c};height:100%;width:{pct:.0f}%;display:flex;align-items:center;
                padding-left:10px;color:#FFF;font-size:11.5px;font-weight:500;
                font-variant-numeric:tabular-nums;letter-spacing:0.02em">
      {pct:.0f}%
    </div>
  </div>
</div>
        """)
    st.markdown(
        f"""
<div class="ku-card" style="height:100%">
  <div class="ku-cardhead" style="margin-bottom:14px">
    <div>
      <div class="ku-cardtitle">Eskalationspfad</div>
      <div class="ku-cardsub">Stufenweise Konversion</div>
    </div>
  </div>
  {''.join(rows)}
</div>
        """,
        unsafe_allow_html=True,
    )

with right:
    by_type = data.events_by_type(top=20)
    st.plotly_chart(charts.event_type_bar(by_type), use_container_width=True)

# ---------- Drill-down: Severity → offene Events; Event-Typ → alle Events ----------
style.section_head(i18n.t("dd_events_under"))
dd_a, dd_b = st.columns(2, gap="medium")
with dd_a:
    sev_options = (sev_df.sort_values("n", ascending=False)["severity"].tolist()
                   if not sev_df.empty else
                   ["critical", "high", "medium", "low", "info"])
    sel_sev = st.selectbox(i18n.t("dd_pick_severity"), [""] + sev_options, key="dd_sev")
    if sel_sev:
        df = data.open_events_by_severity_detail(sel_sev, limit=50)
        st.caption((f"Nächste 50 offene Events der Severity **{sel_sev}**, sortiert nach SLA"
                    if LANG == "de"
                    else f"Next 50 open events at severity **{sel_sev}**, sorted by SLA"))
        st.dataframe(i18n.rename(df, "event").rename(columns={
            "first_name": i18n.col("first_name", "client", LANG),
            "last_name": i18n.col("last_name", "client", LANG),
        }), hide_index=True, use_container_width=True, height=360)

with dd_b:
    type_options = by_type["event_type"].head(15).tolist() if not by_type.empty else []
    sel_type = st.selectbox(i18n.t("dd_pick_event_type"), [""] + type_options, key="dd_type")
    if sel_type:
        df = data.events_by_type_detail(sel_type, limit=50)
        st.caption((f"Letzte 50 Events vom Typ **{sel_type}**" if LANG == "de"
                    else f"Last 50 events of type **{sel_type}**"))
        st.dataframe(i18n.rename(df, "event").rename(columns={
            "first_name": i18n.col("first_name", "client", LANG),
            "last_name": i18n.col("last_name", "client", LANG),
        }), hide_index=True, use_container_width=True, height=360)

style.section_head("Verteilung nach Tageszeit" if LANG == "de" else "Hour-of-day distribution")
_hour_evts = data.query("SELECT severity, detected_at FROM event")
grid = defaultdict(lambda: defaultdict(int))
if not _hour_evts.empty:
    _hts   = _pd.to_datetime(_hour_evts["detected_at"], errors="coerce")
    _hmask = _hts.notna()
    if _hmask.any():
        _hours = _hts[_hmask].dt.hour.astype(int)
        for sev, h in zip(_hour_evts.loc[_hmask, "severity"], _hours):
            grid[sev][int(h)] += 1
mx = max(v for s in grid for v in grid[s].values()) if grid else 1
hm_rows = []
for sev in severity_order:
    cells = []
    for h in range(24):
        n = grid[sev][h]
        op = (n / mx) if mx else 0
        if op < 0.04:
            cells.append('<div style="background:var(--surface-2);border-radius:2px"></div>')
        else:
            cells.append(
                f'<div style="background:{sev_color[sev]};opacity:{0.20 + op*0.80:.2f};'
                f'border-radius:2px" title="{n}"></div>'
            )
    hm_rows.append(f"""
<div style="display:grid;grid-template-columns:80px 1fr;gap:10px;margin-bottom:3px;align-items:center">
  <div style="font-size:10.5px;text-transform:uppercase;letter-spacing:0.06em;
              color:var(--ink-3);font-family:var(--mono)">{sev_label_de[sev]}</div>
  <div style="display:grid;grid-template-columns:repeat(24,1fr);gap:2px;height:16px">
    {''.join(cells)}
  </div>
</div>
    """)
st.markdown(
    f"""
<div class="ku-card">
  {''.join(hm_rows)}
  <div style="display:grid;grid-template-columns:80px 1fr;gap:10px;margin-top:8px">
    <div></div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);font-size:10.5px;
                color:var(--ink-4);font-family:var(--mono);letter-spacing:0.04em">
      <span>00</span><span>06</span><span>12</span><span>18</span><span style="text-align:right">23</span>
    </div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

# ---------- Queue ----------
_n_open = int(data.query(
    "SELECT COUNT(*) AS n FROM event "
    "WHERE status IN ('open','in_progress','escalated')"
).iloc[0]["n"])
style.section_head(
    "Aktive Warteliste" if LANG == "de" else "Active queue",
    count=(f"{style.fmt_int(_n_open)} offen" if LANG == "de"
           else f"{style.fmt_int(_n_open)} open"),
)

overdue_only = st.toggle("Nur überfällige" if LANG == "de" else "Overdue only", value=False)
sql = """
    SELECT e.event_id, e.event_type, e.severity, e.status, e.detected_at, e.sla_due_date,
           e.assigned_to, e.loan_id, e.client_id,
           c.first_name, c.last_name,
           a.canton, p.object_type,
           l.current_outstanding, l.ltv_pct, l.dsti_pct
      FROM event e
      LEFT JOIN loan l     ON l.loan_id = e.loan_id
      LEFT JOIN client c   ON c.client_id = e.client_id
      LEFT JOIN property p ON p.property_id = l.property_id
      LEFT JOIN address a  ON a.address_id = p.address_id
     WHERE e.status IN ('open','in_progress','escalated')
"""
qparams: dict = {}
if overdue_only:
    sql += " AND e.sla_due_date < :today"
    qparams["today"] = data.today().isoformat()
sql += " ORDER BY e.sla_due_date ASC LIMIT 60"
q = data.query(sql, qparams)

st.dataframe(
    q.rename(columns={
        "event_id": "ID", "event_type": "Ereignis", "severity": "Schwere",
        "status": "Status", "detected_at": "Erkannt", "sla_due_date": "SLA",
        "assigned_to": "Owner", "loan_id": "Kredit",
        "first_name": "Vorname", "last_name": "Nachname",
        "canton": "Kanton", "object_type": "Objekt",
        "current_outstanding": "Saldo", "ltv_pct": "Belehnung", "dsti_pct": "Tragbarkeit",
    }).style.format({"Saldo": "{:,.0f}", "Belehnung": "{:.1f}", "Tragbarkeit": "{:.1f}"}),
    use_container_width=True, height=520, hide_index=True,
)

style.footer()
