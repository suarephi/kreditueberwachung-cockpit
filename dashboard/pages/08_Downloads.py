"""Downloads: CSV pro Tabelle, ZIP-Bundle, SQLite-DB, Ad-hoc-Abfrage."""
from __future__ import annotations
import io, json, sys, zipfile
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import streamlit as st          # noqa: E402

from kreditueberwachung_mock import config       # noqa: E402
from dashboard import data, style                # noqa: E402

st.set_page_config(page_title="Downloads", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Downloads")

style.page_head("Downloads",
                "Datenexport",
                "Einzelne Tabellen, das gesamte CSV-Bundle oder die SQLite-DB · "
                "alle Daten lokal und synthetisch.")

CSV_DIR = config.OUTPUT_DIR / "csv"
DB_PATH = config.DB_PATH


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,.1f} {unit}".replace(",", "'") if unit != "B" else f"{n:,} {unit}".replace(",", "'")
        n /= 1024


@st.cache_data(show_spinner=False, max_entries=24)
def _read_bytes(path_str: str) -> bytes:
    return Path(path_str).read_bytes()


@st.cache_data(show_spinner="ZIP wird erstellt…", ttl=600)
def _build_csv_zip(paths: tuple[str, ...]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in paths:
            zf.write(p, arcname=Path(p).name)
    return buf.getvalue()


# ---- KPI strip with archive metadata ----
csv_files = sorted(CSV_DIR.glob("*.csv"), key=lambda p: p.stat().st_size, reverse=True) if CSV_DIR.exists() else []
total_csv = sum(p.stat().st_size for p in csv_files)
db_size   = DB_PATH.stat().st_size if DB_PATH.exists() else 0
style.kpi_strip([
    {"label": "CSV-Tabellen",     "value": str(len(csv_files))},
    {"label": "CSV-Gesamtgrösse", "value": human_size(total_csv) if csv_files else "—"},
    {"label": "SQLite-DB",        "value": human_size(db_size) if db_size else "—"},
    {"label": "Generator-Seed",   "value": str(config.SEED)},
    {"label": "Stand",            "value": dt.date.today().strftime("%d.%m.%Y")},
])

# ---- per-table CSVs ----
style.section_head("CSV pro Tabelle", count=f"{len(csv_files)} Dateien")
if not csv_files:
    st.warning("CSV-Verzeichnis fehlt. Bitte `python scripts/generate.py` ausführen.")
else:
    cols = st.columns(3, gap="medium")
    for i, p in enumerate(csv_files):
        size = p.stat().st_size
        with cols[i % 3]:
            st.markdown(
                f"""
<div class="ku-card" style="margin-bottom:8px;padding:14px 16px;">
  <div style="font-weight:600;font-family:var(--mono);color:var(--ink);font-size:0.92rem">{p.name}</div>
  <div style="color:var(--ink-3);font-size:0.75rem;margin-top:2px">{human_size(size)}</div>
</div>
                """,
                unsafe_allow_html=True,
            )
            st.download_button(
                label=f"{p.name} herunterladen",
                data=_read_bytes(str(p)),
                file_name=p.name,
                mime="text/csv",
                key=f"dl_{p.name}",
                use_container_width=True,
            )

# ---- bundle ----
style.section_head("Bundle · alle CSVs als ZIP")
if csv_files:
    paths = tuple(sorted(str(p) for p in csv_files))
    cols = st.columns([2, 3])
    cols[0].markdown(f"**{len(paths)} Dateien** · {human_size(total_csv)}")
    if cols[1].button("ZIP erstellen", use_container_width=True):
        st.session_state["_zip_built"] = _build_csv_zip(paths)
    if "_zip_built" in st.session_state:
        st.download_button(
            label="kreditueberwachung_csv.zip herunterladen",
            data=st.session_state["_zip_built"],
            file_name=f"kreditueberwachung_csv_{dt.date.today().isoformat()}.zip",
            mime="application/zip", use_container_width=True,
        )

# ---- SQLite ----
style.section_head("SQLite-Datenbank")
if DB_PATH.exists():
    st.markdown(
        f"""
<div class="ku-card">
  <div style="font-family:var(--mono);color:var(--ink);font-size:0.92rem">{DB_PATH}</div>
  <div style="color:var(--ink-3);font-size:0.82rem;margin-top:6px">
    {human_size(db_size)} · {len(csv_files)} Tabellen
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    if db_size < 500 * 1024 * 1024:
        st.download_button(
            label=f"{DB_PATH.name} herunterladen",
            data=_read_bytes(str(DB_PATH)),
            file_name=DB_PATH.name,
            mime="application/x-sqlite3",
            use_container_width=True,
        )
    else:
        st.info(f"DB ist {human_size(db_size)} – zu gross für Browser-Download. "
                f"Direkt von der Festplatte kopieren:\n\n```bash\ncp {DB_PATH} ~/Downloads/\n```")

# ---- Ad-hoc query ----
style.section_head("Individuelle Abfrage")
default_sql = (
    "SELECT l.loan_id, c.last_name, a.canton, l.current_outstanding, l.ltv_pct, l.dsti_pct\n"
    "FROM loan l\n"
    "JOIN client   c ON c.client_id = l.primary_client_id\n"
    "JOIN property p USING(property_id)\n"
    "JOIN address  a ON a.address_id = p.address_id\n"
    "ORDER BY l.current_outstanding DESC LIMIT 1000"
)
sql = st.text_area("SQL · nur Lesen", default_sql, height=180)
if st.button("Abfrage ausführen", use_container_width=True):
    s = sql.strip().rstrip(";").lower()
    if not s.startswith("select"):
        st.error("Nur SELECT erlaubt.")
    elif any(b in s for b in (" insert ", " update ", " delete ", " drop ", " alter ", "pragma ")):
        st.error("Nur lesende Abfragen.")
    else:
        try:
            df = data.query(sql)
            st.success(f"{len(df):,} Zeilen.".replace(",", "'"))
            st.dataframe(df.head(500), use_container_width=True, height=320, hide_index=True)
            st.download_button(
                label="result.csv herunterladen",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="result.csv", mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Abfrage fehlgeschlagen: {e}")

# ---- JSON dossier ----
style.section_head("JSON · Kreditdossier")
lid = st.number_input("Kredit-ID", min_value=0, value=0, step=1, key="dl_loanid")
if lid:
    bundle = data.loan_full(int(lid))
    if bundle.get("loan", None) is None or bundle["loan"].empty:
        st.warning("Kredit nicht gefunden.")
    else:
        payload = {k: v.to_dict(orient="records") for k, v in bundle.items() if v is not None}
        st.download_button(
            label=f"dossier_loan_{int(lid)}.json herunterladen",
            data=json.dumps(payload, default=str, indent=2).encode("utf-8"),
            file_name=f"dossier_loan_{int(lid)}.json",
            mime="application/json",
            use_container_width=True,
        )

style.footer()
