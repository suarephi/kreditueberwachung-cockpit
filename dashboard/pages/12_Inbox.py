"""Inbox · Persönliche Pendenzenliste für E. Schärli."""
from __future__ import annotations
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402

from dashboard import data, style, i18n    # noqa: E402

st.set_page_config(page_title="Inbox", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Übersicht")

LANG = i18n.current_lang()
OFFICER = style.DEMO_OFFICER  # OFFICER-7

style.page_head(
    "Inbox" if LANG == "en" else "Posteingang",
    i18n.t("inbox_title"),
    i18n.t("inbox_subtitle"),
)

today = dt.date.today().isoformat()
tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()

# ---- KPIs ----
events_open = data.query("""
    SELECT COUNT(*) AS n_open,
           SUM(CASE WHEN sla_due_date < :today THEN 1 ELSE 0 END) AS n_overdue,
           SUM(CASE WHEN sla_due_date BETWEEN :today AND :tomorrow THEN 1 ELSE 0 END) AS n_24h,
           SUM(CASE WHEN severity IN ('critical','high') THEN 1 ELSE 0 END) AS n_crit
      FROM event
     WHERE assigned_to = :o AND status IN ('open','in_progress','escalated')
""", {"o": OFFICER, "today": today, "tomorrow": tomorrow}).iloc[0]

style.kpi_strip([
    {"label": i18n.t("inbox_kpi_open"),
     "value": style.fmt_int(int(events_open["n_open"] or 0))},
    {"label": i18n.t("inbox_kpi_overdue"),
     "value": style.fmt_int(int(events_open["n_overdue"] or 0))},
    {"label": i18n.t("inbox_kpi_24h"),
     "value": style.fmt_int(int(events_open["n_24h"] or 0))},
    {"label": i18n.t("inbox_kpi_critical"),
     "value": style.fmt_int(int(events_open["n_crit"] or 0))},
])

auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""

# ---- Events table ----
style.section_head(i18n.t("inbox_section_events"))
events = data.query("""
    SELECT e.event_id, e.event_type, e.severity, e.detected_at, e.sla_due_date,
           e.title, e.loan_id, c.first_name, c.last_name, a.canton
      FROM event e
      LEFT JOIN loan l    ON l.loan_id    = e.loan_id
      LEFT JOIN client c  ON c.client_id  = e.client_id
      LEFT JOIN property p ON p.property_id = l.property_id
      LEFT JOIN address a ON a.address_id  = p.address_id
     WHERE e.assigned_to = :o
       AND e.status IN ('open','in_progress','escalated')
     ORDER BY e.sla_due_date ASC NULLS LAST LIMIT 200
""", {"o": OFFICER})

if events.empty:
    st.info(i18n.t("inbox_no_events"))
else:
    today_d = dt.date.today()
    rows = []
    for _, r in events.iterrows():
        try:
            sla = dt.date.fromisoformat(str(r["sla_due_date"]))
            delta = (sla - today_d).days
        except Exception:
            delta = 999
        if delta < 0:
            sla_lbl = (f"−{abs(delta)} T überfällig" if LANG == "de"
                       else f"{abs(delta)} d overdue")
            sla_kind = "red"
        elif delta == 0:
            sla_lbl, sla_kind = ("jetzt fällig" if LANG == "de" else "due now"), "amber"
        elif delta == 1:
            sla_lbl, sla_kind = "in 24h", "amber"
        else:
            sla_lbl = f"in {delta} T" if LANG == "de" else f"in {delta}d"
            sla_kind = "amber" if delta < 7 else "green"
        sev_kind = ({"critical": "red", "high": "red", "medium": "amber"}
                    .get(r["severity"], "green"))
        loan_url = (f"/Kreditdossier?loan_id={int(r['loan_id'])}{auth_suffix}&lang={LANG}"
                    if r['loan_id'] else
                    f"/Kreditdossier?{auth_suffix.lstrip('&')}&lang={LANG}")
        name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
        rows.append(f"""
<tr>
  <td>{style.chip(r['severity'], sev_kind)}</td>
  <td style="font-family:var(--mono);font-size:11.5px">{r['event_type']}</td>
  <td>
    <a href="{loan_url}" target="_self" style="color:inherit;text-decoration:none">
      <div style="font-family:var(--mono);font-size:11px;color:var(--ink-3)">K-{int(r['loan_id'] or 0):06d}</div>
      <div style="color:var(--ink);font-weight:500;font-size:12.5px;margin-top:1px">{name}</div>
    </a>
  </td>
  <td>{style.tag_canton(r.get('canton')) if r.get('canton') else '—'}</td>
  <td style="color:var(--ink-3);font-size:11.5px;font-family:var(--mono)">{r['detected_at']}</td>
  <td>{style.chip(sla_lbl, sla_kind)}</td>
  <td><a href="{loan_url}" target="_self" style="color:var(--ink-3);font-size:12.5px;text-decoration:none">{i18n.t('open_link')}</a></td>
</tr>""")
    th_titles = (
        ("Severity", "Auslöser", "Kredit / Kunde", "Kanton", "Erkannt", "SLA", "")
        if LANG == "de" else
        ("Severity", "Trigger", "Loan / Client", "Canton", "Detected", "SLA", "")
    )
    th = "".join(
        f'<th style="text-align:left;padding:10px 12px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:var(--ink-3);background:var(--surface-2);'
        f'border-bottom:1px solid var(--line)">{c}</th>'
        for c in th_titles
    )
    st.markdown(
        f'<div class="ku-card ku-card-flush"><table style="width:100%;'
        f'border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )

# ---- Cases ----
style.section_head(i18n.t("inbox_section_cases"))
cases = data.query("""
    SELECT lc.case_id, lc.case_type, lc.opened_at, lc.due_date, lc.status,
           lc.priority, lc.loan_id, c.first_name, c.last_name
      FROM loan_case lc
      LEFT JOIN client c ON c.client_id = lc.client_id
     WHERE lc.assigned_officer = :o AND lc.status NOT IN ('closed_resolved','waived')
     ORDER BY lc.due_date ASC NULLS LAST LIMIT 100
""", {"o": OFFICER})

if cases.empty:
    st.info(i18n.t("inbox_no_cases"))
else:
    rows = []
    for _, r in cases.iterrows():
        loan_url = (f"/Kreditdossier?loan_id={int(r['loan_id'])}{auth_suffix}&lang={LANG}"
                    if r['loan_id'] else
                    f"/Kreditdossier?{auth_suffix.lstrip('&')}&lang={LANG}")
        name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
        prio = r.get("priority") or ""
        prio_kind = "red" if prio == "high" else ("amber" if prio == "normal" else "green")
        rows.append(f"""
<tr>
  <td style="font-family:var(--mono);font-size:11.5px">{r['case_id']}</td>
  <td style="color:var(--ink-2);font-size:12.5px">{r['case_type']}</td>
  <td>{style.chip(prio, prio_kind) if prio else '—'}</td>
  <td>
    <a href="{loan_url}" target="_self" style="color:inherit;text-decoration:none">
      <div style="font-family:var(--mono);font-size:11px;color:var(--ink-3)">K-{int(r['loan_id'] or 0):06d}</div>
      <div style="color:var(--ink);font-weight:500;font-size:12.5px">{name}</div>
    </a>
  </td>
  <td style="color:var(--ink-3);font-family:var(--mono);font-size:11.5px">{r['opened_at']}</td>
  <td style="color:var(--ink-2);font-family:var(--mono);font-size:11.5px">{r.get('due_date') or '—'}</td>
  <td>{r['status']}</td>
</tr>""")
    th_titles = (
        ("ID", "Typ", "Priorität", "Kredit / Kunde", "Eröffnet", "Frist", "Status")
        if LANG == "de" else
        ("ID", "Type", "Priority", "Loan / Client", "Opened", "Due", "Status")
    )
    th = "".join(
        f'<th style="text-align:left;padding:10px 12px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:var(--ink-3);background:var(--surface-2);'
        f'border-bottom:1px solid var(--line)">{c}</th>'
        for c in th_titles
    )
    st.markdown(
        f'<div class="ku-card ku-card-flush"><table style="width:100%;'
        f'border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )

style.footer()
