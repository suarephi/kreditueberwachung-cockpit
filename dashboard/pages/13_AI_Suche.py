"""AI-Suche · Natural-Language → SQL via Claude → live Drill-down."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402

from dashboard import data, style, i18n, ai_search    # noqa: E402

st.set_page_config(page_title="AI Suche", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Übersicht")

LANG = i18n.current_lang()
style.page_head(
    "AI-Suche" if LANG == "de" else "AI search",
    "Natürlichsprachliche Abfrage" if LANG == "de" else "Natural-language query",
    ("Frage in Worten formulieren — Claude erzeugt SQL, Resultat wird live "
     "auf der Live-Datenbank ausgeführt. Read-only, ein einziges SELECT pro "
     "Abfrage.") if LANG == "de" else
    ("Ask in plain language — Claude generates SQL, executed live on the "
     "production database. Read-only, single SELECT per query."),
)

# Read API key from Streamlit secrets (same mechanism as the DB URL)
api_key = None
try:
    api_key = st.secrets["anthropic"]["api_key"]
except Exception:
    api_key = None

if not api_key:
    st.warning(
        ("Kein Anthropic-API-Key konfiguriert. Bitte in Streamlit Cloud "
         "→ App-Settings → Secrets ergänzen:\n\n```\n[anthropic]\napi_key = \"sk-ant-...\"\n```")
        if LANG == "de" else
        ("No Anthropic API key configured. Add it in Streamlit Cloud → "
         "App Settings → Secrets:\n\n```\n[anthropic]\napi_key = \"sk-ant-...\"\n```")
    )
    style.footer()
    st.stop()

# ---- Examples ----
example_de = [
    "Top 10 Kredite nach LTV",
    "Wieviele Loans pro IFRS-9-Stage und wieviel Lifetime ECL?",
    "MFH in Zürich mit DSTI über 30",
    "Welche Kunden haben in den letzten 90 Tagen einen Lohnausfall im Konto?",
    "Top 25 Wertschriftendepots nach Volumen mit Strategie",
    "Welche Loans haben mehr als CHF 10'000 Rückstand in der 1. Mahnung?",
]
example_en = [
    "Top 10 loans by LTV",
    "Loans per IFRS-9 stage and lifetime ECL",
    "MFH in Zürich with DSTI above 30",
    "Clients with a salary loss in the last 90 days",
    "Top 25 securities portfolios by AUM with strategy",
    "Loans with more than CHF 10'000 overdue in stage-1 dunning",
]
examples = example_de if LANG == "de" else example_en

# Persist last query/sql across reruns
if "ai_q" not in st.session_state:
    st.session_state["ai_q"] = ""

st.markdown("**" + ("Beispiele" if LANG == "de" else "Examples") + "**")
ex_cols = st.columns(3, gap="small")
for i, ex in enumerate(examples):
    if ex_cols[i % 3].button(ex, key=f"ex_{i}", use_container_width=True):
        st.session_state["ai_q"] = ex

q = st.text_area(
    "Frage" if LANG == "de" else "Question",
    value=st.session_state["ai_q"],
    height=80,
    placeholder=("z. B. 'Top 20 Kredite mit LTV > 90 in BE und DSTI > 33'"
                 if LANG == "de" else
                 "e.g. 'Top 20 loans with LTV > 90 in BE and DSTI > 33'"),
    key="ai_q_input",
)

run = st.button("Abfrage ausführen" if LANG == "de" else "Run query",
                type="primary", use_container_width=False)

if run and q.strip():
    st.session_state["ai_q"] = q
    with st.spinner("Lade …" if LANG == "de" else "Loading …"):
        try:
            sql = ai_search.generate_sql(q.strip(), api_key=api_key)
        except Exception as e:
            st.error(f"Claude-API-Fehler: {e}" if LANG == "de"
                     else f"Claude API error: {e}")
            style.footer()
            st.stop()

    ok, reason = ai_search.is_safe_select(sql)
    style.section_head("Generiertes SQL" if LANG == "de" else "Generated SQL")
    st.code(sql, language="sql")

    if not ok:
        st.error(("SQL abgelehnt: " + reason) if LANG == "de"
                 else ("SQL rejected: " + reason))
        style.footer()
        st.stop()

    style.section_head("Resultat" if LANG == "de" else "Result")
    try:
        df = data.query(sql)
    except Exception as e:
        st.error(("Ausführung fehlgeschlagen: " + str(e)[:300]) if LANG == "de"
                 else ("Execution failed: " + str(e)[:300]))
        style.footer()
        st.stop()

    if df.empty:
        st.info("Keine Treffer." if LANG == "de" else "No matches.")
    else:
        n = len(df)
        st.caption((f"{n} Zeilen" if LANG == "de" else f"{n} rows").replace(",", "'"))
        st.dataframe(df, use_container_width=True, height=520, hide_index=True)
        st.download_button(
            label=("Resultat als CSV" if LANG == "de" else "Download CSV"),
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="ai_search_result.csv",
            mime="text/csv",
        )

style.footer()
