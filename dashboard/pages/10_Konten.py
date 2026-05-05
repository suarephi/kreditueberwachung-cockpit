"""Konten & Transaktionen: Bewegungsanalyse für Kreditkunden."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import plotly.express as px     # noqa: E402

from dashboard import data, style    # noqa: E402

st.set_page_config(page_title="Konten", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Konten")

style.page_head("Konten",
                "Bewegungsanalyse",
                "Lohnzahlungen, Daueraufträge, materielle Veränderungen über die letzten 24 Monate.")

# Probe
try:
    n_acc = int(data.query("SELECT COUNT(*) AS n FROM account").iloc[0]["n"])
except Exception:
    n_acc = 0

if n_acc == 0:
    st.info("Keine Konten/Transaktionen im Datensatz. "
            "Lokal regenerieren: `KU_TX_FRAC=0.30 python scripts/generate.py`.")
    style.footer()
    st.stop()

# ---------- KPIs ----------
kpi = data.query("""
    SELECT COUNT(*) AS n_acc,
           SUM(current_balance_chf) AS total_balance,
           AVG(current_balance_chf) AS avg_balance
      FROM account
""").iloc[0]
salary_kpi = data.query("""
    SELECT COUNT(*) AS n_clients,
           AVG(monthly) AS avg_monthly
      FROM (SELECT a.client_id,
                   AVG(CASE WHEN at.category='salary' THEN at.amount_chf END) AS monthly
              FROM account a JOIN account_tx at ON a.account_id=at.account_id
             WHERE a.account_type='salary'
               AND at.tx_date >= date('now','-12 months')
             GROUP BY a.client_id)
     WHERE monthly IS NOT NULL
""").iloc[0]
total_bal_n, total_bal_u = style.fmt_compact(float(kpi["total_balance"] or 0))
avg_bal_n,   avg_bal_u   = style.fmt_compact(float(kpi["avg_balance"] or 0))
style.kpi_strip([
    {"label": "Konten",                  "value": style.fmt_int(int(kpi["n_acc"] or 0))},
    {"label": "Saldo gesamt",            "value": total_bal_n, "unit": total_bal_u},
    {"label": "Ø Saldo / Konto",         "value": avg_bal_n,   "unit": avg_bal_u},
    {"label": "Lohnkunden (12 Mt)",      "value": style.fmt_int(int(salary_kpi["n_clients"] or 0))},
    {"label": "Ø monatlicher Lohn",
     "value": style.fmt_chf(float(salary_kpi["avg_monthly"] or 0)).replace(' CHF',''),
     "unit":  "CHF"},
])

# ---------- Konsistenz Lohnzahlung ↔ Lohnausweis ----------
style.section_head("Konsistenz · Lohnzahlung vs. Lohnausweis")
consistency = data.query("""
    SELECT i.client_id,
           c.first_name, c.last_name, c.segment,
           i.gross_salary,
           ROUND(12.0 * AVG(CASE WHEN at.category='salary' THEN at.amount_chf END), 0) AS implied_annual,
           ROUND(100.0 * (12.0 * AVG(CASE WHEN at.category='salary' THEN at.amount_chf END)
                         - i.gross_salary) / i.gross_salary, 1) AS deviation_pct
      FROM income i
      JOIN client c ON c.client_id = i.client_id
      JOIN account a ON a.client_id = i.client_id AND a.account_type='salary'
      JOIN account_tx at ON at.account_id = a.account_id
     WHERE at.tx_date >= date('now','-12 months')
       AND i.gross_salary > 0
     GROUP BY i.client_id, c.first_name, c.last_name, c.segment, i.gross_salary
""")
consistency["status"] = consistency["deviation_pct"].abs().apply(
    lambda d: "🟢 ±5%" if d < 5 else ("🟡 5–15%" if d < 15 else "🔴 >15%"))

flag_counts = consistency["status"].value_counts()
cols = st.columns(3)
for i, (label, count) in enumerate(flag_counts.items()):
    cols[i % 3].metric(label, int(count))

st.dataframe(consistency.rename(columns={
    "client_id": "Kunden-ID", "first_name": "Vorname", "last_name": "Nachname",
    "segment": "Segment", "gross_salary": "Lohnausweis (CHF/J)",
    "implied_annual": "Konto-impliziert", "deviation_pct": "Δ %", "status": "Flag",
}).sort_values("Δ %", key=lambda s: s.abs(), ascending=False),
hide_index=True, use_container_width=True, height=320)

# ---------- Verdächtige Veränderungen ----------
style.section_head("Materielle Veränderungen · einmalige Grosseingänge/-ausgänge")
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
    st.dataframe(changes.rename(columns={
        "client_id": "Kunden-ID", "first_name": "Vorname", "last_name": "Nachname",
        "tx_date": "Datum", "category": "Kategorie", "amount_chf": "Betrag (CHF)",
        "counterparty": "Gegenpartei", "description": "Beschreibung",
    }).style.format({"Betrag (CHF)": "{:+,.0f}"}),
    hide_index=True, use_container_width=True, height=320)
else:
    st.info("Keine ausserordentlichen Bewegungen im Datensatz.")

# ---------- Drill-down: Konto wählen, Tx anzeigen ----------
style.section_head("Drill-down · Transaktionshistorie")
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
sel = st.selectbox("Konto wählen", [0] + acc_options,
                    format_func=lambda i: ("Bitte wählen" if i == 0 else acc_label[i]))
if sel:
    cat_filter = st.multiselect("Kategorien filtern (leer = alle)", [
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
    st.caption(f"Letzte 500 Buchungen · {len(txs)} angezeigt")
    st.dataframe(txs.rename(columns={
        "tx_date": "Datum", "amount_chf": "Betrag (CHF)",
        "category": "Kategorie", "counterparty": "Gegenpartei",
        "description": "Beschreibung",
    }).style.format({"Betrag (CHF)": "{:+,.2f}"}),
    hide_index=True, use_container_width=True, height=420)

style.footer()
