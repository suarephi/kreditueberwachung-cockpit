"""Risikofälle: Watchlist, NPL, höchste erwartete Verluste."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402
import plotly.express as px     # noqa: E402

import pandas as _pd                              # noqa: E402
from dashboard import data, charts, style, sla_reference, i18n    # noqa: E402

st.set_page_config(page_title="Risikofälle", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Risikofälle")

LANG = i18n.current_lang()
style.page_head(i18n.t("ph_risk_crumb"), i18n.t("ph_risk_title"), i18n.t("ph_risk_sub"))

kpis = data.portfolio_kpis()
aff = data.affordability_breakdown()
fail = int(aff[aff['pass_fail'] == 'fail']['n'].sum())      if not aff.empty else 0
exc  = int(aff[aff['pass_fail'] == 'exception']['n'].sum()) if not aff.empty else 0

el_n, el_unit = style.fmt_compact(kpis.get("total_el") or 0)
if LANG == "de":
    risk_kpi_lbl = ("Beobachtungsliste", "NPL", "Forbearance",
                    "Erwarteter Verlust", "Tragb. Fail / Ausnahme")
else:
    risk_kpi_lbl = ("Watchlist", "NPL", "Forbearance",
                    "Expected Loss", "Affordability fail / exception")
style.kpi_strip([
    {"label": risk_kpi_lbl[0], "value": style.fmt_int(kpis.get("n_watchlist") or 0)},
    {"label": risk_kpi_lbl[1], "value": style.fmt_int(kpis.get("n_npl") or 0)},
    {"label": risk_kpi_lbl[2], "value": style.fmt_int(kpis.get("n_forbearance") or 0)},
    {"label": risk_kpi_lbl[3], "value": el_n, "unit": el_unit},
    {"label": risk_kpi_lbl[4],
     "value": f"{style.fmt_int(fail)} / {style.fmt_int(exc)}"},
])

style.section_head("Beobachtungsliste · Top 200 nach erwartetem Verlust" if LANG == "de"
                   else "Watchlist · Top 200 by expected loss")
wl = data.watchlist(limit=200)
left, right = st.columns([3, 2], gap="medium")

with left:
    if wl.empty:
        st.info("Keine Beobachtungsfälle." if LANG == "de" else "No watchlist cases.")
    else:
        if LANG == "de":
            ren = {
                "loan_id": "Kredit-ID", "last_name": "Nachname", "first_name": "Vorname",
                "canton": "Kanton", "city": "Ort", "object_type": "Objekt",
                "current_outstanding": "Saldo", "ltv_pct": "Belehnung",
                "dsti_pct": "Tragbarkeit", "expected_loss": "EV",
                "pd_1y": "PD 1J", "rating_internal": "Rating",
                "npl_flag": "NPL", "forbearance_flag": "Forb.", "days_past_due": "DPD",
            }
            saldo_c, lehn_c, trag_c, ev_c, pd_c = "Saldo", "Belehnung", "Tragbarkeit", "EV", "PD 1J"
        else:
            ren = {
                "loan_id": "Loan ID", "last_name": "Last Name", "first_name": "First Name",
                "canton": "Canton", "city": "City", "object_type": "Object",
                "current_outstanding": "Balance", "ltv_pct": "LTV",
                "dsti_pct": "DSTI", "expected_loss": "EL",
                "pd_1y": "PD 1Y", "rating_internal": "Rating",
                "npl_flag": "NPL", "forbearance_flag": "Forb.", "days_past_due": "DPD",
            }
            saldo_c, lehn_c, trag_c, ev_c, pd_c = "Balance", "LTV", "DSTI", "EL", "PD 1Y"
        wl_de = wl.rename(columns=ren)
        st.dataframe(
            wl_de.style.format({
                saldo_c: "{:,.0f}", lehn_c: "{:.1f}",
                trag_c: "{:.1f}", ev_c: "{:,.0f}", pd_c: "{:.4f}",
            }).background_gradient(subset=[ev_c], cmap="Reds"),
            use_container_width=True, height=520, hide_index=True,
        )

with right:
    title_lhs = "Belehnung vs. Tragbarkeit" if LANG == "de" else "LTV vs. DSTI"
    title_sub = ("Top 1 000 nach EV · Farbe = PD 1J" if LANG == "de"
                 else "Top 1,000 by EL · color = PD 1Y")
    st.markdown(
        f"""<div class="ku-cardhead" style="margin:0 0 4px"><div>
        <div class="ku-cardtitle">{title_lhs}</div>
        <div class="ku-cardsub">{title_sub}</div></div></div>""",
        unsafe_allow_html=True,
    )
    if not wl.empty:
        st.plotly_chart(charts.ltv_dsti_scatter(wl.head(1000)), use_container_width=True)

    style.section_head("Tragbarkeitsergebnis" if LANG == "de" else "Affordability result")
    if not aff.empty:
        aff_de = aff.copy()
        if LANG == "de":
            aff_de["label"] = aff_de["pass_fail"].map(
                {"pass": "Bestanden", "exception": "Ausnahme", "fail": "Nicht bestanden"})
        else:
            aff_de["label"] = aff_de["pass_fail"].map(
                {"pass": "Pass", "exception": "Exception", "fail": "Fail"})
        fig = px.pie(aff_de, names="label", values="n", hole=0.55,
                     color="pass_fail",
                     color_discrete_map={"pass": style.SEV_GREEN,
                                         "exception": style.SEV_AMBER,
                                         "fail": style.SEV_RED})
        fig.update_traces(textinfo="label+percent",
                          textfont=dict(color="#FFFFFF", size=12),
                          marker=dict(line=dict(color="#FFFFFF", width=2)))
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

style.section_head(i18n.t("dd_loans_kpi"))
dd_a, dd_b = st.columns(2, gap="medium")
with dd_a:
    flag = st.selectbox(i18n.t("dd_pick_flag"), ["", "watchlist", "npl", "forbearance"], key="dd_flag")
    if flag:
        df = data.loans_by_risk_flag(flag, limit=50)
        st.caption((f"Top 50 Kredite mit **{flag}**-Flag, sortiert nach EV" if LANG == "de"
                    else f"Top 50 loans with **{flag}** flag, sorted by EL"))
        st.dataframe(i18n.rename(df, "loan").rename(columns={
            "first_name": i18n.col("first_name", "client", LANG),
            "last_name": i18n.col("last_name", "client", LANG),
            "canton": i18n.col("canton", "address", LANG),
            "object_type": i18n.col("object_type", "property", LANG),
            "expected_loss": i18n.col("expected_loss", "risk_metrics", LANG),
            "pd_1y": i18n.col("pd_1y", "risk_metrics", LANG),
            "days_past_due": i18n.col("days_past_due", "risk_metrics", LANG),
        }), hide_index=True, use_container_width=True, height=380)

with dd_b:
    pf = st.selectbox(i18n.t("dd_pick_pf"), ["", "fail", "exception", "pass"], key="dd_pf")
    if pf:
        df = data.loans_by_affordability(pf, limit=50)
        st.caption((f"Top 50 Kredite mit Tragbarkeit **{pf}**, sortiert nach DSTI"
                    if LANG == "de"
                    else f"Top 50 loans with affordability **{pf}**, sorted by DSTI"))
        st.dataframe(i18n.rename(df, "loan").rename(columns={
            "first_name": i18n.col("first_name", "client", LANG),
            "last_name": i18n.col("last_name", "client", LANG),
            "canton": i18n.col("canton", "address", LANG),
            "object_type": i18n.col("object_type", "property", LANG),
            "dsti_calculated": i18n.col("dsti_calculated", "affordability_assessment", LANG),
            "dsti_threshold": i18n.col("dsti_threshold", "affordability_assessment", LANG),
            "income_basis": i18n.col("income_basis", "affordability_assessment", LANG),
        }), hide_index=True, use_container_width=True, height=380)

style.section_head(i18n.t("ifrs_section"), count=i18n.t("ifrs_section_sub"))
try:
    ifrs_summary = data.query("""
        SELECT ifrs9_stage, COUNT(*) AS n,
               ROUND(CAST(SUM(lifetime_el)/1e6 AS numeric), 2) AS lt_el_mchf
          FROM risk_metrics
         WHERE ifrs9_stage IS NOT NULL
         GROUP BY ifrs9_stage ORDER BY ifrs9_stage
    """)
except Exception:
    ifrs_summary = _pd.DataFrame()

if ifrs_summary.empty:
    st.info("Noch kein IFRS-9-Staging berechnet. Generator neu laufen lassen."
            if LANG == "de" else
            "IFRS-9 staging not computed yet. Re-run the generator.")
else:
    s_dict = ifrs_summary.set_index("ifrs9_stage")["n"].to_dict()
    el_dict = ifrs_summary.set_index("ifrs9_stage")["lt_el_mchf"].to_dict()
    total_lt_el = float(ifrs_summary["lt_el_mchf"].sum())
    style.kpi_strip([
        {"label": i18n.t("ifrs_kpi_s1"),
         "value": style.fmt_int(int(s_dict.get(1, 0))),
         "delta_html": style.delta(
             f"{el_dict.get(1, 0):.1f} Mio. CHF" if LANG == "de"
             else f"{el_dict.get(1, 0):.1f} CHF mn",
             "12-Mt ECL" if LANG == "de" else "12-mo ECL", "flat", "good")},
        {"label": i18n.t("ifrs_kpi_s2"),
         "value": style.fmt_int(int(s_dict.get(2, 0))),
         "delta_html": style.delta(
             f"{el_dict.get(2, 0):.1f} Mio. CHF" if LANG == "de"
             else f"{el_dict.get(2, 0):.1f} CHF mn",
             "Lifetime ECL" if LANG == "de" else "Lifetime ECL", "up", "bad")},
        {"label": i18n.t("ifrs_kpi_s3"),
         "value": style.fmt_int(int(s_dict.get(3, 0))),
         "delta_html": style.delta(
             f"{el_dict.get(3, 0):.1f} Mio. CHF" if LANG == "de"
             else f"{el_dict.get(3, 0):.1f} CHF mn",
             "Voll LGD×EAD" if LANG == "de" else "Full LGD×EAD", "up", "bad")},
        {"label": i18n.t("ifrs_kpi_lifetime_el"),
         "value": f"{total_lt_el:.1f}",
         "unit": "Mio. CHF" if LANG == "de" else "CHF mn"},
    ])

    # Stage 2 + 3 detail tables
    auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""
    for st_num, card_key in [(2, "ifrs_card_stage2"), (3, "ifrs_card_stage3")]:
        df = data.query("""
            SELECT l.loan_id, c.first_name, c.last_name, ad.canton,
                   p.object_type, l.current_outstanding, l.ltv_pct,
                   r.pd_1y, r.expected_loss, r.lifetime_el, r.ifrs9_sicr_reason
              FROM risk_metrics r
              JOIN loan l    ON l.loan_id = r.loan_id
              JOIN client c  ON c.client_id = l.primary_client_id
              JOIN property p USING(property_id)
              JOIN address ad ON ad.address_id = p.address_id
             WHERE r.ifrs9_stage = :s
             ORDER BY r.lifetime_el DESC LIMIT 50
        """, {"s": st_num})
        if df.empty:
            continue
        st.markdown(f"<div class='ku-cardhead' style='margin:14px 0 6px'>"
                    f"<div><div class='ku-cardtitle'>{i18n.t(card_key)}</div></div>"
                    f"</div>", unsafe_allow_html=True)
        rows = []
        for _, r in df.iterrows():
            loan_url = f"/Kreditdossier?loan_id={int(r['loan_id'])}{auth_suffix}&lang={LANG}"
            name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
            chip_kind = "red" if st_num == 3 else "amber"
            rows.append(f"""
<tr>
  <td>{style.chip(f"S{st_num}", chip_kind)}</td>
  <td>
    <a href="{loan_url}" target="_self" style="color:inherit;text-decoration:none">
      <div style="font-family:var(--mono);font-size:11px;color:var(--ink-3)">K-{int(r['loan_id']):06d}</div>
      <div style="color:var(--ink);font-weight:500;font-size:12.5px">{name}</div>
    </a>
  </td>
  <td>{style.tag_canton(r.get('canton')) if r.get('canton') else '—'}</td>
  <td style="font-size:12.5px">{r.get('object_type') or '—'}</td>
  <td style="text-align:right">{r['ltv_pct']:.1f}%</td>
  <td style="text-align:right">{r['pd_1y']:.4f}</td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{style.fmt_chf(r['lifetime_el']).replace(' CHF','')}</td>
  <td style="color:var(--ink-3);font-size:11.5px">{r.get('ifrs9_sicr_reason') or '—'}</td>
</tr>""")
        th_titles = (
            (i18n.t("ifrs_th_stage"), i18n.t("klr_th_client"),
             i18n.t("klr_th_canton"), "Objekt", "LTV", "PD 1J",
             i18n.t("ifrs_th_lifetime_el"), i18n.t("ifrs_th_reason"))
            if LANG == "de" else
            (i18n.t("ifrs_th_stage"), i18n.t("klr_th_client"),
             i18n.t("klr_th_canton"), "Object", "LTV", "PD 1Y",
             i18n.t("ifrs_th_lifetime_el"), i18n.t("ifrs_th_reason"))
        )
        th = "".join(
            f'<th style="text-align:left;padding:9px 10px;font-size:11px;'
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

style.section_head(i18n.t("klr_section"), count=i18n.t("klr_section_sub"))
total_exp = data.total_exposure_chf()
sn_df = data.concentration_single_name(25)
ct_df = data.concentration_canton()
ng_df = data.concentration_noga()

# KPI-Strip mit Konzentrations-Schwellen-Status
top_sn_share = (float(sn_df.iloc[0]["exposure"]) / max(total_exp, 1.0) * 100
                if not sn_df.empty else 0.0)
top_ct_share = (float(ct_df.iloc[0]["exposure"]) / max(total_exp, 1.0) * 100
                if not ct_df.empty else 0.0)
top_ng_share = (float(ng_df.iloc[0]["exposure"]) / max(total_exp, 1.0) * 100
                if not ng_df.empty else 0.0)
total_n, total_u = style.fmt_compact(total_exp)
sn_break = top_sn_share > 10.0
ct_break = top_ct_share > 25.0
ng_break = top_ng_share > 20.0
style.kpi_strip([
    {"label": i18n.t("klr_total_exposure"), "value": total_n, "unit": total_u},
    {"label": i18n.t("klr_top_threshold"),
     "value": f"{top_sn_share:.2f}", "unit": "%",
     "delta_html": style.delta(
         "Schwelle 10%" if LANG == "de" else "threshold 10%",
         "über Limit" if (sn_break and LANG == "de") else
         ("over limit" if sn_break else
          ("im Rahmen" if LANG == "de" else "within limit")),
         "down" if not sn_break else "up",
         "good" if not sn_break else "bad")},
    {"label": i18n.t("klr_canton_top"),
     "value": (ct_df.iloc[0]["canton"] if not ct_df.empty else "—"),
     "unit": f"{top_ct_share:.1f} %"},
    {"label": i18n.t("klr_noga_top"),
     "value": str(ng_df.iloc[0]["noga_code"]) if not ng_df.empty else "—",
     "unit": f"{top_ng_share:.1f} %"},
])

c1, c2 = st.columns([2, 1], gap="medium")

with c1:
    st.markdown(f"<div class='ku-cardhead' style='margin:0 0 6px'>"
                f"<div><div class='ku-cardtitle'>{i18n.t('klr_card_single')}</div>"
                f"</div></div>", unsafe_allow_html=True)
    sn_view = sn_df.copy()
    sn_view["share_pct"] = sn_view["exposure"] / max(total_exp, 1.0) * 100
    sn_view["name"] = sn_view["first_name"].fillna("") + " " + sn_view["last_name"].fillna("")
    auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""
    rows = []
    for _, r in sn_view.iterrows():
        share = float(r["share_pct"])
        chip_kind = "red" if share > 10 else ("amber" if share > 5 else "green")
        url = (f"/Suche?q={int(r['client_id'])}{auth_suffix}&lang={LANG}")
        rows.append(f"""
<tr>
  <td style="font-family:var(--mono);font-size:11.5px;color:var(--ink-3)">#{int(r['client_id'])}</td>
  <td><a href="{url}" target="_self" style="color:var(--ink);text-decoration:none;font-weight:500">{r['name'].strip()}</a></td>
  <td style="color:var(--ink-3);font-size:12px">{r.get('segment') or ''}</td>
  <td style="text-align:right">{int(r['n_loans'])}</td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{style.fmt_chf(r['exposure']).replace(' CHF','')}</td>
  <td style="text-align:right">{style.chip(f'{share:.2f}%', chip_kind)}</td>
</tr>""")
    th = "".join(
        f'<th style="text-align:left;padding:8px 10px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:var(--ink-3);background:var(--surface-2);'
        f'border-bottom:1px solid var(--line)">{c}</th>'
        for c in (
            "ID",
            i18n.t("klr_th_client"),
            i18n.t("klr_th_segment"),
            i18n.t("klr_th_loans"),
            i18n.t("klr_th_exposure"),
            i18n.t("klr_th_share"),
        )
    )
    st.markdown(
        f'<div class="ku-card ku-card-flush"><table style="width:100%;'
        f'border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(f"<div class='ku-cardhead' style='margin:0 0 6px'>"
                f"<div><div class='ku-cardtitle'>{i18n.t('klr_card_canton')}</div>"
                f"</div></div>", unsafe_allow_html=True)
    ct_view = ct_df.copy()
    ct_view["share_pct"] = ct_view["exposure"] / max(total_exp, 1.0) * 100
    rows = []
    for _, r in ct_view.iterrows():
        share = float(r["share_pct"])
        chip_kind = "red" if share > 25 else ("amber" if share > 15 else "green")
        rows.append(f"""
<tr>
  <td>{style.tag_canton(r['canton'])}</td>
  <td style="text-align:right">{int(r['n_loans'])}</td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{style.fmt_chf(r['exposure']).replace(' CHF','')}</td>
  <td style="text-align:right">{style.chip(f'{share:.1f}%', chip_kind)}</td>
</tr>""")
    th = "".join(
        f'<th style="text-align:left;padding:8px 10px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:var(--ink-3);background:var(--surface-2);'
        f'border-bottom:1px solid var(--line)">{c}</th>'
        for c in (i18n.t("klr_th_canton"), i18n.t("klr_th_loans"),
                   i18n.t("klr_th_exposure"), i18n.t("klr_th_share"))
    )
    st.markdown(
        f'<div class="ku-card ku-card-flush"><table style="width:100%;'
        f'border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )

# Branch (NOGA) full-width below
st.markdown(f"<div class='ku-cardhead' style='margin:18px 0 6px'>"
            f"<div><div class='ku-cardtitle'>{i18n.t('klr_card_noga')}</div>"
            f"</div></div>", unsafe_allow_html=True)
ng_view = ng_df.copy()
ng_view["share_pct"] = ng_view["exposure"] / max(total_exp, 1.0) * 100
rows = []
for _, r in ng_view.iterrows():
    share = float(r["share_pct"])
    chip_kind = "red" if share > 20 else ("amber" if share > 10 else "green")
    rows.append(f"""
<tr>
  <td style="font-family:var(--mono);font-size:11.5px">{r['noga_code']}</td>
  <td style="color:var(--ink-2);font-size:12.5px">{r.get('noga_label') or '—'}</td>
  <td style="text-align:right">{int(r['n_loans'])}</td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{style.fmt_chf(r['exposure']).replace(' CHF','')}</td>
  <td style="text-align:right">{style.chip(f'{share:.2f}%', chip_kind)}</td>
</tr>""")
th = "".join(
    f'<th style="text-align:left;padding:8px 10px;font-size:11px;'
    f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
    f'color:var(--ink-3);background:var(--surface-2);'
    f'border-bottom:1px solid var(--line)">{c}</th>'
    for c in (i18n.t("klr_th_noga"), i18n.t("klr_th_branch"),
               i18n.t("klr_th_loans"), i18n.t("klr_th_exposure"),
               i18n.t("klr_th_share"))
)
st.markdown(
    f'<div class="ku-card ku-card-flush"><table style="width:100%;'
    f'border-collapse:collapse">'
    f'<thead><tr>{th}</tr></thead>'
    f'<tbody>{"".join(rows)}</tbody></table></div>',
    unsafe_allow_html=True,
)

style.section_head(i18n.t("dunning_section"), count=i18n.t("dunning_section_sub"))
try:
    dunning = data.query("""
        SELECT d.dunning_id, d.loan_id, d.step, d.step_label, d.issued_date,
               d.due_date, d.amount_overdue_chf, d.fee_chf, d.status,
               c.first_name, c.last_name, ad.canton
          FROM dunning_step d
          JOIN loan l    ON l.loan_id    = d.loan_id
          JOIN client c  ON c.client_id  = l.primary_client_id
          JOIN property p ON p.property_id = l.property_id
          JOIN address ad ON ad.address_id = p.address_id
         WHERE d.status IN ('open','escalated')
         ORDER BY d.step DESC, d.amount_overdue_chf DESC LIMIT 100
    """)
except Exception:
    dunning = _pd.DataFrame()

if dunning.empty:
    st.info(i18n.t("dunning_no_active"))
else:
    auth_suffix = f"&k={style.auth_token()}" if style.auth_token() else ""
    rows = []
    for _, r in dunning.iterrows():
        step = int(r["step"])
        kind = "red" if step >= 3 else ("amber" if step == 2 else "green")
        loan_url = f"/Kreditdossier?loan_id={int(r['loan_id'])}{auth_suffix}&lang={LANG}"
        name = f"{r.get('first_name') or ''} {r.get('last_name') or ''}".strip()
        rows.append(f"""
<tr>
  <td>{style.chip(f"Stufe {step}" if LANG == "de" else f"Step {step}", kind)}</td>
  <td style="color:var(--ink-2);font-size:12.5px">{r['step_label']}</td>
  <td>
    <a href="{loan_url}" target="_self" style="color:inherit;text-decoration:none">
      <div style="font-family:var(--mono);font-size:11px;color:var(--ink-3)">K-{int(r['loan_id']):06d}</div>
      <div style="color:var(--ink);font-weight:500;font-size:12.5px">{name}</div>
    </a>
  </td>
  <td>{style.tag_canton(r.get('canton')) if r.get('canton') else '—'}</td>
  <td style="color:var(--ink-3);font-family:var(--mono);font-size:11.5px">{r['issued_date']}</td>
  <td style="color:var(--ink-3);font-family:var(--mono);font-size:11.5px">{r['due_date']}</td>
  <td style="text-align:right;font-variant-numeric:tabular-nums">{style.fmt_chf(r['amount_overdue_chf']).replace(' CHF','')}</td>
  <td style="text-align:right">{r['fee_chf']:.0f}</td>
  <td>{style.chip(r['status'], 'red' if r['status']=='escalated' else 'amber')}</td>
</tr>""")
    th_titles = (
        (i18n.t("dunning_th_step"), "Beschreibung", i18n.t("klr_th_client"),
         i18n.t("klr_th_canton"), i18n.t("dunning_th_issued"),
         i18n.t("dunning_th_due"), i18n.t("dunning_th_overdue"),
         i18n.t("dunning_th_fee"), i18n.t("dunning_th_status"))
        if LANG == "de" else
        (i18n.t("dunning_th_step"), "Description", i18n.t("klr_th_client"),
         i18n.t("klr_th_canton"), i18n.t("dunning_th_issued"),
         i18n.t("dunning_th_due"), i18n.t("dunning_th_overdue"),
         i18n.t("dunning_th_fee"), i18n.t("dunning_th_status"))
    )
    th = "".join(
        f'<th style="text-align:left;padding:10px 12px;font-size:11px;'
        f'font-weight:500;letter-spacing:0.06em;text-transform:uppercase;'
        f'color:var(--ink-3);background:var(--surface-2);'
        f'border-bottom:1px solid var(--line)">{c}</th>' for c in th_titles
    )
    st.markdown(
        f'<div class="ku-card ku-card-flush"><table style="width:100%;'
        f'border-collapse:collapse">'
        f'<thead><tr>{th}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )

style.section_head("SLA-Matrix · Bearbeitungsfristen pro Auslöser" if LANG == "de"
                   else "SLA matrix · deadlines per trigger")
sla_reference.render_reference(in_expander=False)

style.footer()
