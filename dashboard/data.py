"""Cached SQL helpers (SQLite local, PostgreSQL on Streamlit Cloud)."""
from __future__ import annotations
import datetime as dt
from sqlalchemy import text
import streamlit as st
import pandas as pd

from . import db


# ---------------------------------------------------------------------------
# Engine + helpers
# ---------------------------------------------------------------------------
def query(sql: str, params: dict | tuple | None = None) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame. Accepts either dict (named) or tuple
    (positional, but discouraged — pass dicts)."""
    if params is None:
        params = {}
    if isinstance(params, tuple) and len(params) == 0:
        params = {}
    if isinstance(params, tuple):
        # Legacy: caller passed empty tuple.
        params = {}
    return pd.read_sql_query(text(sql), db.engine(), params=params or {})


def today() -> dt.date:
    return dt.date.today()


def days_ago(n: int) -> str:
    return (dt.date.today() - dt.timedelta(days=n)).isoformat()


def days_ahead(n: int) -> str:
    return (dt.date.today() + dt.timedelta(days=n)).isoformat()


# ---------------------------------------------------------------------------
# Portfolio aggregates
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def portfolio_kpis() -> dict:
    df = query("""
        SELECT COUNT(*) AS n_loans,
               SUM(current_outstanding) AS total_outstanding,
               AVG(ltv_pct) AS avg_ltv,
               AVG(dsti_pct) AS avg_dsti,
               SUM(CASE WHEN ltv_pct>80 THEN 1 ELSE 0 END)*1.0/COUNT(*) AS share_ltv_gt80,
               SUM(CASE WHEN dsti_pct>33 THEN 1 ELSE 0 END)*1.0/COUNT(*) AS share_dsti_gt33
          FROM loan
    """)
    rm = query("""
        SELECT SUM(watchlist_flag)   AS n_watchlist,
               SUM(npl_flag)         AS n_npl,
               SUM(forbearance_flag) AS n_forbearance,
               SUM(expected_loss)    AS total_el
          FROM risk_metrics
    """)
    return {**df.iloc[0].to_dict(), **rm.iloc[0].to_dict()}


@st.cache_data(ttl=300, show_spinner=False)
def per_canton_metrics() -> pd.DataFrame:
    return query("""
        SELECT a.canton                                   AS canton_code,
               c.name_de                                  AS canton_name,
               COUNT(DISTINCT l.loan_id)                  AS n_loans,
               SUM(l.current_outstanding)                 AS total_outstanding,
               AVG(l.ltv_pct)                             AS avg_ltv,
               AVG(l.dsti_pct)                            AS avg_dsti,
               AVG(v.market_value/p.living_area_sqm)      AS chf_per_sqm,
               AVG(v.market_value)                        AS avg_market_value,
               SUM(rm.expected_loss)                      AS total_el,
               SUM(rm.watchlist_flag)                     AS n_watchlist,
               SUM(rm.npl_flag)                           AS n_npl
          FROM loan l
          JOIN property p USING(property_id)
          JOIN address  a ON a.address_id = p.address_id
          JOIN v_current_valuation v ON v.property_id = p.property_id
          LEFT JOIN risk_metrics rm  ON rm.loan_id = l.loan_id
          LEFT JOIN canton c ON c.canton_code = a.canton
         WHERE p.living_area_sqm > 0
           AND a.canton IN (SELECT canton_code FROM canton)
         GROUP BY a.canton, c.name_de
    """)


@st.cache_data(ttl=300, show_spinner=False)
def per_plz_metrics() -> pd.DataFrame:
    return query("""
        SELECT a.postal_code,
               a.city,
               a.canton,
               COUNT(DISTINCT l.loan_id)                  AS n_loans,
               SUM(l.current_outstanding)                 AS total_outstanding,
               AVG(l.ltv_pct)                             AS avg_ltv,
               AVG(v.market_value/p.living_area_sqm)      AS chf_per_sqm,
               AVG(v.market_value)                        AS avg_market_value
          FROM loan l
          JOIN property p USING(property_id)
          JOIN address  a ON a.address_id = p.address_id
          JOIN v_current_valuation v ON v.property_id = p.property_id
         WHERE p.living_area_sqm > 0
         GROUP BY a.postal_code, a.city, a.canton
    """)


@st.cache_data(ttl=300, show_spinner=False)
def ltv_distribution() -> pd.DataFrame:
    return query("SELECT ltv_pct FROM loan")


@st.cache_data(ttl=300, show_spinner=False)
def dsti_distribution() -> pd.DataFrame:
    return query("SELECT dsti_pct FROM loan")


@st.cache_data(ttl=300, show_spinner=False)
def tranche_count_per_loan() -> pd.DataFrame:
    return query("""
        SELECT n_tranches, COUNT(*) AS n_loans
          FROM (SELECT loan_id, COUNT(*) AS n_tranches FROM tranche GROUP BY loan_id) t
         GROUP BY n_tranches ORDER BY n_tranches
    """)


@st.cache_data(ttl=300, show_spinner=False)
def tranche_type_mix() -> pd.DataFrame:
    return query("""
        SELECT tranche_type, COUNT(*) AS n_tranches,
               ROUND(CAST(SUM(amount)/1e6 AS numeric), 1) AS total_mchf
          FROM tranche GROUP BY tranche_type
    """)


@st.cache_data(ttl=300, show_spinner=False)
def object_type_mix() -> pd.DataFrame:
    return query("""
        SELECT object_type, COUNT(*) AS n,
               ROUND(CAST(AVG(living_area_sqm) AS numeric)) AS avg_area
          FROM property GROUP BY object_type ORDER BY n DESC
    """)


# ---------------------------------------------------------------------------
# Surveillance & distress
# ---------------------------------------------------------------------------
@st.cache_data(ttl=180, show_spinner=False)
def open_events_by_severity() -> pd.DataFrame:
    return query("""
        SELECT severity, COUNT(*) AS n
          FROM event WHERE status IN ('open','in_progress','escalated')
         GROUP BY severity
    """)


@st.cache_data(ttl=180, show_spinner=False)
def events_by_type(top: int = 25) -> pd.DataFrame:
    return query("""
        SELECT event_type, COUNT(*) AS n
          FROM event GROUP BY event_type ORDER BY n DESC LIMIT :top
    """, {"top": int(top)})


@st.cache_data(ttl=180, show_spinner=False)
def overdue_events() -> pd.DataFrame:
    return query("""
        SELECT e.event_id, e.event_type, e.severity, e.status, e.detected_at,
               e.sla_due_date, e.assigned_to, e.loan_id, e.client_id, e.title
          FROM event e
         WHERE e.status IN ('open','in_progress','escalated')
           AND e.sla_due_date < :today
         ORDER BY e.sla_due_date ASC
         LIMIT 200
    """, {"today": today().isoformat()})


@st.cache_data(ttl=180, show_spinner=False)
def recent_escalations(limit: int = 50) -> pd.DataFrame:
    return query("""
        SELECT e.event_id, e.event_type, e.severity, e.detected_at,
               e.sla_due_date, e.loan_id, e.title, c.last_name, c.first_name
          FROM event e
          LEFT JOIN client c ON c.client_id = e.client_id
         WHERE e.status='escalated'
         ORDER BY e.detected_at DESC LIMIT :n
    """, {"n": int(limit)})


@st.cache_data(ttl=180, show_spinner=False)
def watchlist(limit: int = 200) -> pd.DataFrame:
    return query("""
        SELECT l.loan_id, c.last_name, c.first_name,
               a.canton, a.city, p.object_type,
               l.current_outstanding, l.ltv_pct, l.dsti_pct,
               rm.expected_loss, rm.pd_1y, rm.rating_internal,
               rm.npl_flag, rm.forbearance_flag, rm.days_past_due
          FROM loan l
          JOIN client c   ON c.client_id = l.primary_client_id
          JOIN property p USING(property_id)
          JOIN address  a ON a.address_id = p.address_id
          JOIN risk_metrics rm ON rm.loan_id = l.loan_id
         WHERE rm.watchlist_flag=1 OR rm.npl_flag=1
         ORDER BY rm.expected_loss DESC LIMIT :n
    """, {"n": int(limit)})


@st.cache_data(ttl=180, show_spinner=False)
def affordability_breakdown() -> pd.DataFrame:
    return query("""
        SELECT pass_fail, COUNT(*) AS n
          FROM affordability_assessment GROUP BY pass_fail
    """)


# ---------------------------------------------------------------------------
# Loan dossier
# ---------------------------------------------------------------------------
def search_clients(term: str, limit: int = 50) -> pd.DataFrame:
    if term.isdigit():
        return query(
            "SELECT client_id, first_name, last_name, birth_date, segment "
            "FROM client WHERE client_id = :cid LIMIT :n",
            {"cid": int(term), "n": limit},
        )
    like = f"%{term}%"
    return query("""
        SELECT client_id, first_name, last_name, birth_date, segment
          FROM client
         WHERE last_name LIKE :q OR first_name LIKE :q
         LIMIT :n
    """, {"q": like, "n": limit})


def loan_full(loan_id: int) -> dict:
    out: dict = {}
    out["loan"] = query("SELECT * FROM loan WHERE loan_id = :i", {"i": int(loan_id)})
    if out["loan"].empty:
        return out
    cid = int(out["loan"].iloc[0]["primary_client_id"])
    pid = int(out["loan"].iloc[0]["property_id"])
    hid = int(out["loan"].iloc[0]["household_id"])
    out["client"]    = query("SELECT * FROM client WHERE client_id = :i",       {"i": cid})
    out["household"] = query("SELECT * FROM household WHERE household_id = :i", {"i": hid})
    out["members"]   = query("""
        SELECT ch.role, ch.share_pct, c.client_id, c.first_name, c.last_name, c.birth_date
          FROM client_household ch JOIN client c USING(client_id)
         WHERE ch.household_id = :i
    """, {"i": hid})
    out["property"]  = query("""
        SELECT p.*, a.street, a.house_number, a.postal_code, a.city, a.canton
          FROM property p JOIN address a ON a.address_id = p.address_id
         WHERE p.property_id = :i
    """, {"i": pid})
    out["valuations"] = query("""
        SELECT valuation_date, valuation_method, market_value, mortgage_lending_value,
               confidence_band_low, confidence_band_high, is_current
          FROM valuation WHERE property_id = :i ORDER BY valuation_date
    """, {"i": pid})
    out["tranches"]  = query("SELECT * FROM tranche WHERE loan_id = :i", {"i": int(loan_id)})
    out["incomes"]   = query("""
        SELECT i.*
          FROM income i
          JOIN client_household ch USING(client_id)
         WHERE ch.household_id = :i
         ORDER BY i.reporting_year DESC
    """, {"i": hid})
    out["affordability"] = query("SELECT * FROM affordability_assessment WHERE loan_id = :i",
                                  {"i": int(loan_id)})
    out["risk"] = query("SELECT * FROM risk_metrics WHERE loan_id = :i",
                         {"i": int(loan_id)})
    out["events"] = query("""
        SELECT event_id, detected_at, event_type, severity, status, sla_due_date, title
          FROM event WHERE loan_id = :i ORDER BY detected_at DESC LIMIT 200
    """, {"i": int(loan_id)})
    out["cases"] = query("""
        SELECT case_id, case_type, opened_at, due_date, closed_at, status, decision, assigned_team
          FROM loan_case WHERE loan_id = :i ORDER BY opened_at DESC
    """, {"i": int(loan_id)})
    out["documents"] = query("""
        SELECT document_id, parent_type, parent_id, doc_type, status, expiry_date
          FROM document
         WHERE (parent_type='loan'     AND parent_id = :loan_id)
            OR (parent_type='client'   AND parent_id = :client_id)
            OR (parent_type='property' AND parent_id = :prop_id)
    """, {"loan_id": int(loan_id), "client_id": cid, "prop_id": pid})
    return out


# ---------------------------------------------------------------------------
# Stress test
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def stress_scenarios() -> pd.DataFrame:
    return query("SELECT * FROM stress_scenario ORDER BY severity, scenario_id")


@st.cache_data(ttl=300, show_spinner=False)
def stress_kpi(scenario_id: str) -> pd.DataFrame:
    return query("""
        SELECT period, total_exposure, expected_loss_total,
               weighted_avg_ltv, share_ltv_gt80, share_dsti_gt33, npl_share
          FROM stress_portfolio_kpi WHERE scenario_id = :s
         ORDER BY period
    """, {"s": scenario_id})


@st.cache_data(ttl=300, show_spinner=False)
def stress_per_canton(scenario_id: str) -> pd.DataFrame:
    return query("""
        SELECT a.canton AS canton_code,
               COUNT(DISTINCT m.loan_id)         AS n_loans,
               SUM(m.stressed_expected_loss)     AS stressed_el,
               SUM(m.covenant_breach_flag)       AS n_breaches,
               AVG(m.stressed_ltv)               AS avg_stressed_ltv
          FROM stress_loan_metrics m
          JOIN loan l ON l.loan_id = m.loan_id
          JOIN property p USING(property_id)
          JOIN address  a ON a.address_id = p.address_id
         WHERE m.scenario_id = :s
           AND m.period = (SELECT MAX(period) FROM stress_loan_metrics WHERE scenario_id = :s)
           AND a.canton IN (SELECT canton_code FROM canton)
         GROUP BY a.canton
    """, {"s": scenario_id})


@st.cache_data(ttl=300, show_spinner=False)
def stress_top_jumps(scenario_id: str, limit: int = 25) -> pd.DataFrame:
    return query("""
        SELECT loan_id, base_ltv, stressed_ltv, stressed_ltv-base_ltv AS jump,
               base_el, stressed_expected_loss
          FROM v_stress_loan_compare
         WHERE scenario_id = :s
           AND period = (SELECT MAX(period) FROM stress_loan_metrics WHERE scenario_id = :s)
         ORDER BY jump DESC LIMIT :n
    """, {"s": scenario_id, "n": int(limit)})


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def dq_summary() -> dict:
    out: dict = {}
    out["birth_date_dotformat"] = int(query(
        "SELECT COUNT(*) AS n FROM client WHERE birth_date LIKE '%.%'"
    ).iloc[0]["n"])
    out["email_anomalies"] = int(query(
        "SELECT COUNT(*) AS n FROM client WHERE email LIKE '% %' OR email LIKE '%@@%' "
        "OR email NOT LIKE '%.%'"
    ).iloc[0]["n"])
    out["plz_canton_mismatch"] = int(query("""
        SELECT COUNT(*) AS n FROM address a
        JOIN postal_code pc ON pc.postal_code = a.postal_code
        WHERE a.canton <> pc.canton_code AND length(a.canton)=2
    """).iloc[0]["n"])
    out["canton_full_name"] = int(query(
        "SELECT COUNT(*) AS n FROM address WHERE length(canton)>2"
    ).iloc[0]["n"])
    out["null_surrogate"] = int(query(
        "SELECT COUNT(*) AS n FROM client "
        "WHERE phone_landline IN ('-','N/A','unbekannt','tbd')"
    ).iloc[0]["n"])
    return out


def dq_examples(rule: str, limit: int = 25) -> pd.DataFrame:
    n = int(limit)
    if rule == "birth_date_dotformat":
        return query("SELECT client_id, last_name, birth_date FROM client "
                     "WHERE birth_date LIKE '%.%' LIMIT :n", {"n": n})
    if rule == "email_anomalies":
        return query("SELECT client_id, email FROM client "
                     "WHERE email LIKE '% %' OR email LIKE '%@@%' OR email NOT LIKE '%.%' "
                     "LIMIT :n", {"n": n})
    if rule == "plz_canton_mismatch":
        return query("""
            SELECT a.address_id, a.postal_code, a.city, a.canton, pc.canton_code AS expected
              FROM address a JOIN postal_code pc ON pc.postal_code = a.postal_code
             WHERE a.canton <> pc.canton_code AND length(a.canton)=2 LIMIT :n
        """, {"n": n})
    if rule == "canton_full_name":
        return query("SELECT address_id, postal_code, city, canton FROM address "
                     "WHERE length(canton)>2 LIMIT :n", {"n": n})
    if rule == "null_surrogate":
        return query("SELECT client_id, last_name, phone_landline FROM client "
                     "WHERE phone_landline IN ('-','N/A','unbekannt','tbd') LIMIT :n",
                     {"n": n})
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Date helpers exposed for page use
# ---------------------------------------------------------------------------
def overdue_count_recent(days_window: int = 90) -> int:
    return int(query("""
        SELECT COUNT(*) AS n FROM event
         WHERE status IN ('open','in_progress','escalated')
           AND detected_at >= :cutoff
           AND sla_due_date < :today
    """, {"cutoff": days_ago(days_window), "today": today().isoformat()}).iloc[0]["n"])
