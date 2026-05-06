"""Globale Suche · Volltextsuche über Kunden, Kredite und Adressen."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import pandas as pd             # noqa: E402

from dashboard import data, style, i18n    # noqa: E402

st.set_page_config(page_title="Suche", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Übersicht")

LANG = i18n.current_lang()
q = (st.query_params.get("q") or "").strip()

if q:
    subtitle = (f'Suche nach "{q}"' if LANG == "de" else f'Search for "{q}"')
else:
    subtitle = ("Kunde, Kredit-ID, IBAN, PLZ, Ort, NOGA-Code" if LANG == "de"
                else "Client, loan ID, IBAN, postal code, city, NOGA code")
style.page_head(
    "Suche" if LANG == "de" else "Search",
    subtitle,
    ("Live-Treffer aus client, loan, address, account."
     if LANG == "de" else
     "Live matches across client, loan, address, account."),
)

if not q:
    if LANG == "de":
        st.info("Tippe oben rechts in das Suchfeld und drücke Enter. "
                "Treffer in Kunden, Krediten, Adressen und IBANs werden hier "
                "gesammelt aufgelistet.")
    else:
        st.info("Type into the search field at the top right and press Enter. "
                "Matches across clients, loans, addresses and IBANs appear "
                "here grouped by category.")
    style.footer()
    st.stop()

q_like = f"%{q}%"
auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""
lang_suffix = f"&lang={LANG}"


# ---- 1. Direct ID hits (numeric input) ----
hits_loan = pd.DataFrame()
hits_client = pd.DataFrame()
if q.isdigit():
    qid = int(q)
    hits_loan = data.query("""
        SELECT l.loan_id, l.primary_client_id AS client_id,
               c.first_name, c.last_name, p.object_type, a.canton, a.city,
               l.current_outstanding, l.ltv_pct, l.dsti_pct
          FROM loan l
          JOIN client c ON c.client_id = l.primary_client_id
          JOIN property p USING(property_id)
          JOIN address a ON a.address_id = p.address_id
         WHERE l.loan_id = :i
    """, {"i": qid})
    hits_client = data.query("""
        SELECT c.client_id, c.first_name, c.last_name, c.segment, c.email,
               c.iban, a.canton, a.city
          FROM client c
          LEFT JOIN address a ON a.address_id = c.address_id
         WHERE c.client_id = :i
    """, {"i": qid})

# ---- 2. Name / email / IBAN / city / postal-code search ----
hits_clients_text = data.query("""
    SELECT c.client_id, c.first_name, c.last_name, c.segment, c.email,
           c.iban, a.canton, a.city, a.postal_code
      FROM client c
      LEFT JOIN address a ON a.address_id = c.address_id
     WHERE c.last_name  LIKE :q OR c.first_name LIKE :q
        OR c.email      LIKE :q OR c.iban       LIKE :q
        OR a.city       LIKE :q OR a.postal_code LIKE :q
     LIMIT 100
""", {"q": q_like})

# ---- 3. Loan via primary client name match ----
hits_loans_text = data.query("""
    SELECT l.loan_id, l.primary_client_id AS client_id,
           c.first_name, c.last_name, p.object_type, a.canton, a.city,
           l.current_outstanding, l.ltv_pct, l.dsti_pct
      FROM loan l
      JOIN client c ON c.client_id = l.primary_client_id
      JOIN property p USING(property_id)
      JOIN address a ON a.address_id = p.address_id
     WHERE c.last_name LIKE :q OR c.first_name LIKE :q OR a.city LIKE :q
        OR a.postal_code LIKE :q OR p.object_type LIKE :q
     LIMIT 100
""", {"q": q_like})

# ---- 4. Account by IBAN ----
hits_accounts = data.query("""
    SELECT a.account_id, a.iban, a.account_type, a.client_id,
           c.first_name, c.last_name, a.current_balance_chf
      FROM account a
      JOIN client c ON c.client_id = a.client_id
     WHERE a.iban LIKE :q
     LIMIT 50
""", {"q": q_like}) if q else pd.DataFrame()

# ---- Render ----
total = (len(hits_loan) + len(hits_client) + len(hits_clients_text)
         + len(hits_loans_text) + len(hits_accounts))
if total == 0:
    msg = (f'Keine Treffer für "{q}".' if LANG == "de"
           else f'No matches for "{q}".')
    st.warning(msg)
    style.footer()
    st.stop()

style.kpi_strip([
    {"label": "Treffer total" if LANG == "de" else "Total matches",
     "value": str(total)},
    {"label": "Direkte IDs" if LANG == "de" else "Direct IDs",
     "value": str(len(hits_loan) + len(hits_client))},
    {"label": "Kunden" if LANG == "de" else "Clients",
     "value": str(len(hits_clients_text))},
    {"label": "Kredite" if LANG == "de" else "Loans",
     "value": str(len(hits_loans_text))},
    {"label": "Konten" if LANG == "de" else "Accounts",
     "value": str(len(hits_accounts))},
])


def _link_cell(label: str, url: str) -> str:
    return (f'<a href="{url}" target="_self" '
            f'style="color:var(--ink);text-decoration:none;font-weight:500">'
            f'{label}</a>')


def _render_loan_table(df: pd.DataFrame, title: str) -> None:
    if df.empty:
        return
    style.section_head(title, count=str(len(df)))
    rows = []
    for _, r in df.iterrows():
        loan_url = (f"/Kreditdossier?loan_id={int(r['loan_id'])}"
                    f"{auth_suffix}{lang_suffix}")
        name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
        rows.append(f"""
<tr>
  <td>{_link_cell(f"K-{int(r['loan_id']):06d}", loan_url)}</td>
  <td style="color:var(--ink-2)">{name}</td>
  <td>{r.get('object_type') or '—'}</td>
  <td>{style.tag_canton(r.get('canton')) if r.get('canton') else '—'}</td>
  <td>{r.get('city') or '—'}</td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{style.fmt_chf(r['current_outstanding']).replace(' CHF','')}</td>
  <td style="text-align:right">{r['ltv_pct']:.1f}%</td>
  <td style="text-align:right">{r['dsti_pct']:.1f}%</td>
</tr>""")
    cols = (("Kredit", "Kunde", "Objekt", "Kanton", "Ort", "Saldo", "LTV", "DSTI")
            if LANG == "de" else
            ("Loan", "Client", "Object", "Canton", "City", "Balance", "LTV", "DSTI"))
    th = "".join(
        f'<th style="text-align:left;padding:10px 12px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:var(--ink-3);background:var(--surface-2);'
        f'border-bottom:1px solid var(--line)">{c}</th>'
        for c in cols
    )
    st.markdown(
        f'<div class="ku-card ku-card-flush"><table style="width:100%;'
        f'border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _render_client_table(df: pd.DataFrame, title: str) -> None:
    if df.empty:
        return
    style.section_head(title, count=str(len(df)))
    rows = []
    for _, r in df.iterrows():
        # Find first loan for this client to make name clickable.
        url = f"/Kreditdossier?{auth_suffix.lstrip('&')}{lang_suffix}"
        cid = int(r['client_id'])
        name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
        rows.append(f"""
<tr>
  <td><span style="font-family:var(--mono);font-size:11.5px;color:var(--ink-3)">#{cid}</span></td>
  <td style="font-weight:600;color:var(--ink)">{name}</td>
  <td>{r.get('segment') or '—'}</td>
  <td style="color:var(--ink-3);font-size:12.5px">{r.get('email') or '—'}</td>
  <td>{style.tag_canton(r.get('canton')) if r.get('canton') else '—'}</td>
  <td>{r.get('city') or '—'} {r.get('postal_code') or ''}</td>
</tr>""")
    cols = (("Kunden-ID", "Name", "Segment", "E-Mail", "Kanton", "Ort")
            if LANG == "de" else
            ("Client ID", "Name", "Segment", "Email", "Canton", "City"))
    th = "".join(
        f'<th style="text-align:left;padding:10px 12px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:var(--ink-3);background:var(--surface-2);'
        f'border-bottom:1px solid var(--line)">{c}</th>'
        for c in cols
    )
    st.markdown(
        f'<div class="ku-card ku-card-flush"><table style="width:100%;'
        f'border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _render_account_table(df: pd.DataFrame, title: str) -> None:
    if df.empty:
        return
    style.section_head(title, count=str(len(df)))
    rows = []
    for _, r in df.iterrows():
        # Jump to dossier of any of the client's loans.
        loan_first = data.query(
            "SELECT loan_id FROM loan WHERE primary_client_id = :i LIMIT 1",
            {"i": int(r['client_id'])},
        )
        loan_id = (int(loan_first.iloc[0]['loan_id'])
                   if not loan_first.empty else None)
        url = (f"/Kreditdossier?loan_id={loan_id}{auth_suffix}{lang_suffix}"
               if loan_id else
               f"/Kreditdossier?{auth_suffix.lstrip('&')}{lang_suffix}")
        name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
        rows.append(f"""
<tr>
  <td>{_link_cell(r['iban'], url)}</td>
  <td>{r.get('account_type') or ''}</td>
  <td style="color:var(--ink-2)">{name}</td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{style.fmt_chf(r['current_balance_chf']).replace(' CHF','')}</td>
</tr>""")
    cols = (("IBAN", "Typ", "Inhaber", "Saldo") if LANG == "de" else
            ("IBAN", "Type", "Holder", "Balance"))
    th = "".join(
        f'<th style="text-align:left;padding:10px 12px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:var(--ink-3);background:var(--surface-2);'
        f'border-bottom:1px solid var(--line)">{c}</th>'
        for c in cols
    )
    st.markdown(
        f'<div class="ku-card ku-card-flush"><table style="width:100%;'
        f'border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


# Render in order of relevance
if not hits_loan.empty:
    _render_loan_table(hits_loan,
                       "Direkte Kredit-ID-Treffer" if LANG == "de"
                       else "Direct loan-ID match")
if not hits_client.empty:
    _render_client_table(hits_client,
                         "Direkter Kunden-ID-Treffer" if LANG == "de"
                         else "Direct client-ID match")
if not hits_loans_text.empty:
    _render_loan_table(hits_loans_text,
                       "Kredite" if LANG == "de" else "Loans")
if not hits_clients_text.empty:
    _render_client_table(hits_clients_text,
                         "Kunden" if LANG == "de" else "Clients")
if not hits_accounts.empty:
    _render_account_table(hits_accounts,
                          "Konten" if LANG == "de" else "Accounts")

style.footer()
