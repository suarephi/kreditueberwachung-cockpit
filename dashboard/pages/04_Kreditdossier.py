"""Kreditdossier: Suche und Drill-Down zu einem einzelnen Kredit."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import pandas as pd             # noqa: E402
import plotly.express as px     # noqa: E402

from dashboard import data, charts, style    # noqa: E402

st.set_page_config(page_title="Kreditdossier", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Kreditdossier")

style.page_head("Kreditdossier",
                "Suche und Drill-Down",
                "Kunde oder Kredit suchen und ins vollständige Überwachungsdossier eintauchen.")

# ---------- Search ----------
# Deep-link support: /Kreditdossier?loan_id=42 jumps straight to that loan.
prefill_loan_id = 0
try:
    qp = st.query_params.get("loan_id")
    if qp:
        prefill_loan_id = int(qp)
except (TypeError, ValueError):
    prefill_loan_id = 0

search_col1, search_col2 = st.columns([2, 1])
search_term  = search_col1.text_input("Suche nach Kunden-ID, Nachname oder Vorname",
                                      placeholder="z. B. Müller · 12345")
loan_id_input = search_col2.number_input("oder direkt zur Kredit-ID",
                                          min_value=0, value=prefill_loan_id, step=1)

selected_loan_id: int | None = None
if loan_id_input:
    selected_loan_id = int(loan_id_input)
elif search_term:
    matches = data.search_clients(search_term, limit=25)
    if matches.empty:
        st.warning("Keine Kundentreffer.")
    else:
        st.write(f"**{len(matches)}** Kunden gefunden:")
        st.dataframe(matches.rename(columns={
            "client_id": "Kunden-ID", "first_name": "Vorname", "last_name": "Nachname",
            "birth_date": "Geburtsdatum", "segment": "Segment",
        }), use_container_width=True, height=200, hide_index=True)
        chosen = st.number_input("Kunden-ID auswählen", min_value=0, value=0, step=1)
        if chosen:
            loans = data.query("SELECT loan_id FROM loan WHERE primary_client_id = :c",
                               {"c": int(chosen)})
            if not loans.empty:
                lid = st.selectbox("Kredite", options=loans["loan_id"].tolist())
                if lid:
                    selected_loan_id = int(lid)

if selected_loan_id is None:
    st.info("Oben suchen oder eine Kredit-ID eingeben.")
    style.footer()
    st.stop()

dossier = data.loan_full(selected_loan_id)
if dossier.get("loan", None) is None or dossier["loan"].empty:
    st.error(f"Kredit-ID {selected_loan_id} nicht gefunden.")
    style.footer()
    st.stop()

loan   = dossier["loan"].iloc[0]
client = dossier["client"].iloc[0] if not dossier["client"].empty else None
prop   = dossier["property"].iloc[0] if not dossier["property"].empty else None
risk   = dossier["risk"].iloc[0] if not dossier["risk"].empty else None

# ---- Header card ----
title = (f"{client.get('salutation') or ''} {client.get('first_name') or ''} "
         f"{client.get('last_name') or ''}").strip() if client is not None else f"Kredit {selected_loan_id}"
sub_lines = []
if client is not None:
    sub_lines.append(f"Kunde {client.get('client_id')} · {client.get('language_correspondence')} · "
                     f"{client.get('segment')} · KYC {client.get('kyc_level')}")
if prop is not None:
    ot = prop.get("object_type")
    area_val = prop.get("living_area_sqm")
    plot_val = prop.get("plot_area_sqm")
    if ot == "Bauland":
        size_html = (f"{plot_val:.0f} m² Grundstück" if plot_val is not None
                     else "Bauland")
    elif area_val is not None:
        size_html = f"{area_val:.0f} m²"
    else:
        size_html = "—"
    sub_lines.append(
        f"<b>{ot}</b> · {size_html} · "
        f"{prop.get('street')} {prop.get('house_number')}, "
        f"{prop.get('postal_code')} {prop.get('city')} ({prop.get('canton')})"
    )

st.markdown(
    f"""
<div class="ku-card" style="margin:18px 0">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:24px">
    <div>
      <div class="ku-cardtitle" style="font-size:22px">{title}</div>
      <div class="ku-cardsub" style="margin-top:6px">{'<br>'.join(sub_lines)}</div>
    </div>
    <div>{style.tag_canton(f'KRD-{selected_loan_id:06d}')}</div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

# ---- KPI strip ----
kpi_items = [
    {"label": "Saldo",       "value": style.fmt_compact(loan["current_outstanding"])[0],
     "unit": style.fmt_compact(loan["current_outstanding"])[1]},
    {"label": "Belehnung",   "value": f"{loan['ltv_pct']:.1f}", "unit": "%"},
    {"label": "Tragbarkeit", "value": f"{loan['dsti_pct']:.1f}", "unit": "%"},
    {"label": "Tranchen",    "value": str(len(dossier["tranches"]))},
]
if risk is not None:
    kpi_items.append({"label": "Internes Rating", "value": str(int(risk["rating_internal"])),
                      "delta_html": f'<span style="color:var(--ink-3);font-size:11px">PD {risk["pd_1y"]:.4f}</span>'})

style.kpi_strip(kpi_items)

payload = {k: v.to_dict(orient="records") for k, v in dossier.items() if v is not None}
st.download_button(
    label=f"Dossier als JSON · loan_{selected_loan_id}.json",
    data=json.dumps(payload, default=str, indent=2).encode("utf-8"),
    file_name=f"dossier_loan_{selected_loan_id}.json",
    mime="application/json",
)

# ---- Tabs ----
tabs = st.tabs(["Kredit & Tranchen", "Objekt & Bewertungen", "Tragbarkeit",
                "Risikokennzahlen", "Ereignisse", "Fälle", "Dokumente",
                "Haushaltseinkommen", "Konten & Bewegungen"])

with tabs[0]:
    st.markdown("**Kredit**")
    st.dataframe(dossier["loan"].T.rename(columns={0: "Wert"}),
                 use_container_width=True, height=380)
    st.markdown(f"**Tranchenstruktur** · {len(dossier['tranches'])} Tranchen")
    if dossier["tranches"].empty:
        st.info("Keine Tranchen.")
    else:
        a, b = st.columns([1, 2])
        with a:
            fig_pie = charts.tranche_pie(dossier["tranches"])
            if fig_pie: st.plotly_chart(fig_pie, use_container_width=True)
        with b:
            fig_lad = charts.tranche_ladder_bar(dossier["tranches"])
            if fig_lad: st.plotly_chart(fig_lad, use_container_width=True)
        st.dataframe(dossier["tranches"], use_container_width=True, hide_index=True)

with tabs[1]:
    if prop is not None:
        st.markdown("**Objekt**")
        st.dataframe(dossier["property"].T.rename(columns={0: "Wert"}),
                     use_container_width=True, height=300)
    st.markdown("**Bewertungshistorie**")
    if not dossier["valuations"].empty:
        st.plotly_chart(charts.valuation_history(dossier["valuations"]),
                        use_container_width=True)
        st.dataframe(dossier["valuations"], use_container_width=True, hide_index=True)

with tabs[2]:
    st.dataframe(dossier["affordability"], use_container_width=True, hide_index=True)
with tabs[3]:
    st.dataframe(dossier["risk"], use_container_width=True, hide_index=True)
with tabs[4]:
    if not dossier["events"].empty:
        st.dataframe(dossier["events"], use_container_width=True, height=520, hide_index=True)
with tabs[5]:
    if not dossier["cases"].empty:
        st.dataframe(dossier["cases"], use_container_width=True, height=520, hide_index=True)
with tabs[6]:
    if not dossier["documents"].empty:
        st.dataframe(dossier["documents"], use_container_width=True, height=520, hide_index=True)
with tabs[7]:
    st.markdown("**Haushaltsmitglieder**")
    st.dataframe(dossier["members"], use_container_width=True, hide_index=True)
    st.markdown("**Haushaltseinkommen**")
    st.dataframe(dossier["incomes"], use_container_width=True, hide_index=True)

with tabs[8]:
    cid = int(loan["primary_client_id"])
    accounts = data.query("""
        SELECT account_id, iban, account_type, current_balance_chf,
               avg_balance_12m_chf, opened_date
          FROM account WHERE client_id = :c ORDER BY account_type
    """, {"c": cid})

    if accounts.empty:
        st.info("Dieser Kunde hat keine Konten im Datensatz "
                "(Tx-Erfassung läuft nur für ~5 % des Bestandes).")
    else:
        st.markdown("**Konten**")
        st.dataframe(accounts.rename(columns={
            "account_id": "Konto-ID", "iban": "IBAN", "account_type": "Typ",
            "current_balance_chf": "Saldo (CHF)",
            "avg_balance_12m_chf": "Ø Saldo 12 Mt (CHF)",
            "opened_date": "Eröffnung",
        }).style.format({
            "Saldo (CHF)": "{:,.0f}", "Ø Saldo 12 Mt (CHF)": "{:,.0f}",
        }), hide_index=True, use_container_width=True)

        # Salary trend (24 months) — substr(tx_date,1,7) is portable to PG and SQLite.
        salary_trend = data.query("""
            SELECT substr(at.tx_date, 1, 7) AS month, SUM(at.amount_chf) AS amount
              FROM account_tx at JOIN account a ON a.account_id = at.account_id
             WHERE a.client_id = :c AND at.category = 'salary'
             GROUP BY substr(at.tx_date, 1, 7) ORDER BY 1
        """, {"c": cid})
        if not salary_trend.empty:
            col_l, col_r = st.columns([3, 2], gap="medium")
            with col_l:
                st.markdown("**Lohnzahlungen pro Monat**")
                fig = px.bar(salary_trend, x="month", y="amount",
                             color_discrete_sequence=[style.ACCENT])
                fig.update_layout(height=240, margin=dict(l=8, r=8, t=8, b=8),
                                  xaxis_title="", yaxis_title="CHF")
                st.plotly_chart(fig, use_container_width=True)
            with col_r:
                # Konsistenz-Ampel gegen Lohnausweis
                cutoff_12m = data.days_ago(365)
                cons = data.query("""
                    SELECT i.gross_salary,
                           12.0 * AVG(CASE WHEN at.category='salary' THEN at.amount_chf END) AS implied
                      FROM income i
                      JOIN account a ON a.client_id = i.client_id AND a.account_type='salary'
                      JOIN account_tx at ON at.account_id = a.account_id
                     WHERE i.client_id = :c AND at.tx_date >= :cutoff
                     GROUP BY i.gross_salary
                """, {"c": cid, "cutoff": cutoff_12m})
                if not cons.empty:
                    gs = float(cons.iloc[0]["gross_salary"] or 0)
                    impl = float(cons.iloc[0]["implied"] or 0)
                    if gs > 0:
                        dev = (impl - gs) / gs * 100.0
                        flag = ("🟢 ±5 %" if abs(dev) < 5
                                else ("🟡 5-15 %" if abs(dev) < 15 else "🔴 > 15 %"))
                        st.markdown("**Konsistenz Lohn ↔ Lohnausweis**")
                        st.metric("Lohnausweis", f"{gs:,.0f} CHF".replace(",", "'"))
                        st.metric("Konto-impliziert", f"{impl:,.0f} CHF".replace(",", "'"),
                                  delta=f"{dev:+.1f} %")
                        st.markdown(f"**Status:** {flag}")

        # Tx-Anomalien als Events für diesen Loan
        tx_alerts = data.query("""
            SELECT event_id, event_type, severity, detected_at, sla_due_date, title, description
              FROM event
             WHERE loan_id = :l
               AND (title LIKE '%Tx-Anomalie%' OR title LIKE '%Lohnausfall%')
             ORDER BY detected_at DESC
        """, {"l": int(selected_loan_id)})
        if not tx_alerts.empty:
            st.markdown("**Tragbarkeits-Alerts aus Bewegungen**")
            st.dataframe(tx_alerts.rename(columns={
                "event_id": "Event-ID", "event_type": "Auslöser",
                "severity": "Severity", "detected_at": "Erkannt",
                "sla_due_date": "SLA-Frist", "title": "Titel",
                "description": "Beschreibung",
            }), hide_index=True, use_container_width=True)

        # Materielle Veränderungen
        big = data.query("""
            SELECT at.tx_date, at.category, at.amount_chf, at.counterparty, at.description
              FROM account_tx at JOIN account a ON a.account_id = at.account_id
             WHERE a.client_id = :c
               AND at.category IN ('third_pillar_payout','transfer_in','transfer_out')
               AND ABS(at.amount_chf) > 40000
             ORDER BY at.tx_date DESC
        """, {"c": cid})
        if not big.empty:
            st.markdown("**Materielle Bewegungen (> CHF 40'000)**")
            st.dataframe(big.rename(columns={
                "tx_date": "Datum", "category": "Kategorie",
                "amount_chf": "Betrag (CHF)", "counterparty": "Gegenpartei",
                "description": "Beschreibung",
            }).style.format({"Betrag (CHF)": "{:+,.0f}"}),
            hide_index=True, use_container_width=True)

        # Letzte 100 Tx
        st.markdown("**Letzte 100 Buchungen**")
        recent = data.query("""
            SELECT at.tx_date, at.amount_chf, at.category, at.counterparty, at.description
              FROM account_tx at JOIN account a ON a.account_id = at.account_id
             WHERE a.client_id = :c
             ORDER BY at.tx_date DESC LIMIT 100
        """, {"c": cid})
        st.dataframe(recent.rename(columns={
            "tx_date": "Datum", "amount_chf": "Betrag (CHF)",
            "category": "Kategorie", "counterparty": "Gegenpartei",
            "description": "Beschreibung",
        }).style.format({"Betrag (CHF)": "{:+,.2f}"}),
        hide_index=True, use_container_width=True, height=420)

style.footer()
