"""Konten & Transaktionen: Bewegungsanalyse für Kreditkunden."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import plotly.express as px     # noqa: E402
import pandas as pd             # noqa: E402

from dashboard import data, style, i18n    # noqa: E402

st.set_page_config(page_title="Konten", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Konten")

LANG = i18n.current_lang()
style.page_head(i18n.t("ph_accounts_crumb"),
                i18n.t("ph_accounts_title"),
                i18n.t("ph_accounts_sub"))

# Probe
try:
    n_acc = int(data.query("SELECT COUNT(*) AS n FROM account").iloc[0]["n"])
except Exception:
    n_acc = 0

if n_acc == 0:
    st.info(("Keine Konten/Transaktionen im Datensatz. "
             "Lokal regenerieren: `KU_TX_FRAC=0.30 python scripts/generate.py`.")
            if LANG == "de" else
            ("No accounts/transactions in the dataset. "
             "Regenerate locally: `KU_TX_FRAC=0.30 python scripts/generate.py`."))
    style.footer()
    st.stop()

# ---------- KPIs ----------
kpi = data.query("""
    SELECT COUNT(*) AS n_acc,
           SUM(current_balance_chf) AS total_balance,
           AVG(current_balance_chf) AS avg_balance
      FROM account
""").iloc[0]
_cutoff_12m = data.days_ago(365)
salary_kpi = data.query("""
    SELECT COUNT(*) AS n_clients,
           AVG(monthly) AS avg_monthly
      FROM (SELECT a.client_id,
                   AVG(CASE WHEN at.category='salary' THEN at.amount_chf END) AS monthly
              FROM account a JOIN account_tx at ON a.account_id=at.account_id
             WHERE a.account_type='salary'
               AND at.tx_date >= :cutoff
             GROUP BY a.client_id) t
     WHERE monthly IS NOT NULL
""", {"cutoff": _cutoff_12m}).iloc[0]
total_bal_n, total_bal_u = style.fmt_compact(float(kpi["total_balance"] or 0))
avg_bal_n,   avg_bal_u   = style.fmt_compact(float(kpi["avg_balance"] or 0))
style.kpi_strip([
    {"label": i18n.t("acc_kpi_count"),         "value": style.fmt_int(int(kpi["n_acc"] or 0))},
    {"label": i18n.t("acc_kpi_total_balance"), "value": total_bal_n, "unit": total_bal_u},
    {"label": i18n.t("acc_kpi_avg_balance"),   "value": avg_bal_n,   "unit": avg_bal_u},
    {"label": i18n.t("acc_kpi_salary_clients"),"value": style.fmt_int(int(salary_kpi["n_clients"] or 0))},
    {"label": i18n.t("acc_kpi_avg_salary"),
     "value": style.fmt_chf(float(salary_kpi["avg_monthly"] or 0)).replace(' CHF',''),
     "unit":  "CHF"},
])

style.section_head(i18n.t("acc_section_consistency"))
consistency = data.query("""
    SELECT i.client_id,
           c.first_name, c.last_name, c.segment,
           i.gross_salary,
           ROUND(CAST(12.0 * AVG(CASE WHEN at.category='salary' THEN at.amount_chf END) AS numeric), 0) AS implied_annual,
           ROUND(CAST(100.0 * (12.0 * AVG(CASE WHEN at.category='salary' THEN at.amount_chf END)
                              - i.gross_salary) / i.gross_salary AS numeric), 1) AS deviation_pct
      FROM income i
      JOIN client c ON c.client_id = i.client_id
      JOIN account a ON a.client_id = i.client_id AND a.account_type='salary'
      JOIN account_tx at ON at.account_id = a.account_id
     WHERE at.tx_date >= :cutoff
       AND i.gross_salary > 0
     GROUP BY i.client_id, c.first_name, c.last_name, c.segment, i.gross_salary
""", {"cutoff": _cutoff_12m})
consistency["status"] = consistency["deviation_pct"].abs().apply(
    lambda d: i18n.t("ampel_green") if d < 5
              else (i18n.t("ampel_yellow") if d < 15 else i18n.t("ampel_red")))

flag_counts = consistency["status"].value_counts()
cols = st.columns(3)
for i, (label, count) in enumerate(flag_counts.items()):
    cols[i % 3].metric(label, int(count))

if LANG == "de":
    rename_map = {
        "client_id": "Kunden-ID", "first_name": "Vorname", "last_name": "Nachname",
        "segment": "Segment", "gross_salary": "Lohnausweis (CHF/J)",
        "implied_annual": "Konto-impliziert", "deviation_pct": "Δ %", "status": "Flag",
    }
    delta_col = "Δ %"
else:
    rename_map = {
        "client_id": "Client ID", "first_name": "First Name", "last_name": "Last Name",
        "segment": "Segment", "gross_salary": "Payslip (CHF/y)",
        "implied_annual": "Account-implied", "deviation_pct": "Δ %", "status": "Flag",
    }
    delta_col = "Δ %"
st.dataframe(consistency.rename(columns=rename_map)
             .sort_values(delta_col, key=lambda s: s.abs(), ascending=False),
hide_index=True, use_container_width=True, height=320)

style.section_head(i18n.t("acc_section_changes"))
changes = data.query("""
    SELECT a.client_id, c.first_name, c.last_name,
           at.tx_date, at.category, at.amount_chf,
           at.counterparty, at.description
      FROM account_tx at
      JOIN account a ON a.account_id = at.account_id
      JOIN client c  ON c.client_id  = a.client_id
     WHERE at.category IN ('third_pillar_payout','transfer_in','transfer_out')
       AND ABS(at.amount_chf) > 40000
     ORDER BY ABS(at.amount_chf) DESC LIMIT 100
""")
if not changes.empty:
    amt_col = i18n.col("amount_chf", "account_tx", LANG)
    st.dataframe(i18n.rename(changes, "account_tx").style.format({amt_col: "{:+,.0f}"}),
                 hide_index=True, use_container_width=True, height=320)
else:
    st.info("Keine ausserordentlichen Bewegungen im Datensatz."
            if LANG == "de" else "No exceptional movements in the dataset.")

style.section_head(i18n.t("acc_section_alerts"),
                   count=i18n.t("acc_section_alerts_sub"))
auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""
alerts = data.query("""
    SELECT e.event_id, e.event_type, e.severity, e.detected_at, e.sla_due_date,
           e.title, e.description,
           e.loan_id, c.first_name, c.last_name,
           aff.dsti_calculated, aff.household_income_used, aff.pass_fail
      FROM event e
      JOIN loan l   ON l.loan_id   = e.loan_id
      JOIN client c ON c.client_id = e.client_id
      LEFT JOIN (
          SELECT loan_id, dsti_calculated, household_income_used, pass_fail
            FROM (SELECT loan_id, dsti_calculated, household_income_used, pass_fail,
                         ROW_NUMBER() OVER (PARTITION BY loan_id ORDER BY assessment_date DESC) AS rn
                    FROM affordability_assessment
                   WHERE income_basis LIKE '%Recheck nach Tx%') x
           WHERE rn = 1
      ) aff ON aff.loan_id = e.loan_id
     WHERE e.title LIKE '%Tx-Anomalie%' OR e.title LIKE '%Lohnausfall%'
     ORDER BY e.detected_at DESC
""")
if alerts.empty:
    st.info("Keine Tragbarkeits-Alerts aus Bewegungen im Datensatz."
            if LANG == "de" else "No affordability alerts from movements in the dataset.")
else:
    counts = alerts["event_type"].value_counts()
    cols = st.columns(min(5, len(counts)))
    for i, (etype, n) in enumerate(counts.items()):
        cols[i % len(cols)].metric(etype, int(n))
    rows_html = []
    for _, r in alerts.iterrows():
        loan_url = f"/Kreditdossier?loan_id={int(r['loan_id'])}{auth_suffix}"
        sev_color = {"critical": "var(--sev-red)", "high": "var(--sev-red)",
                     "medium": "var(--sev-amber)", "low": "var(--ink-3)",
                     "info": "var(--ink-3)"}.get(r["severity"], "var(--ink-3)")
        dsti = r["dsti_calculated"]
        dsti_html = (f"<span style='color:{sev_color};font-weight:600'>{dsti:.1f}%</span>"
                     if pd.notna(dsti) else "—")
        inc = r["household_income_used"]
        income_html = (f"{int(inc):,} CHF".replace(",", "'") if pd.notna(inc) else "—")
        pf = (r["pass_fail"] or "—")
        pf_html = (f"<span style='color:var(--sev-red);font-weight:600'>{pf}</span>"
                   if pf == "fail" else pf)
        rows_html.append(f"""
<tr>
  <td><a href="{loan_url}" target="_self" style="text-decoration:none;color:inherit">
        <div style="font-family:var(--mono);font-size:11px;color:var(--ink-2);font-weight:600">K-{int(r['loan_id']):06d}</div>
        <div style="color:var(--ink-3);margin-top:2px;font-size:12.5px">{r['first_name']} {r['last_name']}</div>
      </a></td>
  <td style="font-size:12.5px">{r['event_type']}</td>
  <td>{style.chip(r['severity'], 'red' if r['severity'] in ('critical','high') else ('amber' if r['severity']=='medium' else 'green'))}</td>
  <td style="font-size:12.5px">{r['detected_at']}</td>
  <td style="text-align:right">{dsti_html}</td>
  <td style="text-align:right">{income_html}</td>
  <td>{pf_html}</td>
  <td><a href="{loan_url}" target="_self" style="color:var(--ink-3);font-size:12.5px;text-decoration:none">{i18n.t('open_link')}</a></td>
</tr>""")
    th_loan_client = i18n.t("tbl_th_loan_client")
    th_trigger = "Auslöser" if LANG == "de" else "Trigger"
    th_severity = "Severity"
    th_detected = "Erkannt" if LANG == "de" else "Detected"
    th_dsti = "DSTI neu" if LANG == "de" else "New DSTI"
    th_income = "Einkommen neu" if LANG == "de" else "New income"
    th_pf = "Tragbarkeit" if LANG == "de" else "Affordability"
    st.markdown(f"""
<div class="ku-card ku-card-flush" style="margin-top:8px">
  <table style="width:100%;border-collapse:collapse">
    <thead>
      <tr>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{th_loan_client}</th>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{th_trigger}</th>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{th_severity}</th>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{th_detected}</th>
        <th style="text-align:right;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{th_dsti}</th>
        <th style="text-align:right;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{th_income}</th>
        <th style="text-align:left;padding:10px 12px;font-size:11px;font-weight:500;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-3);background:var(--surface-2);border-bottom:1px solid var(--line)">{th_pf}</th>
        <th></th>
      </tr>
    </thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

style.section_head(i18n.t("acc_section_drill"))
top_acc = data.query("""
    SELECT a.account_id, c.first_name, c.last_name, a.account_type,
           a.iban, a.current_balance_chf
      FROM account a JOIN client c ON c.client_id = a.client_id
     ORDER BY ABS(a.current_balance_chf) DESC LIMIT 100
""")
acc_options = top_acc["account_id"].astype(int).tolist()
acc_label = {int(r["account_id"]):
             f"#{int(r['account_id']):05d} · {r['first_name']} {r['last_name']} · "
             f"{r['account_type']} · {r['iban']} · CHF {r['current_balance_chf']:,.0f}"
             for _, r in top_acc.iterrows()}
sel = st.selectbox(i18n.t("acc_select_account"), [0] + acc_options,
                    format_func=lambda i: (i18n.t("sec_pick") if i == 0 else acc_label[i]))
if sel:
    cat_filter = st.multiselect(i18n.t("acc_filter_categories"), [
        "salary", "mortgage_payment", "rental_income", "standing_order",
        "card_purchase", "withdrawal", "tax", "3a_contribution",
        "transfer_in", "transfer_out", "third_pillar_payout",
    ])
    where = "account_id = :i"
    params = {"i": int(sel)}
    if cat_filter:
        placeholders = ", ".join(f":c{i}" for i in range(len(cat_filter)))
        where += f" AND category IN ({placeholders})"
        for i, c in enumerate(cat_filter):
            params[f"c{i}"] = c
    txs = data.query(f"""
        SELECT tx_date, amount_chf, category, counterparty, description
          FROM account_tx WHERE {where}
         ORDER BY tx_date DESC LIMIT 500
    """, params)
    st.caption(i18n.t("acc_caption_recent").format(n=len(txs)))
    amt_col = i18n.col("amount_chf", "account_tx", LANG)
    st.dataframe(i18n.rename(txs, "account_tx").style.format({amt_col: "{:+,.2f}"}),
                 hide_index=True, use_container_width=True, height=420)

style.footer()
