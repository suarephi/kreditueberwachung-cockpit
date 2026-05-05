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
from dashboard import data, style, i18n          # noqa: E402

st.set_page_config(page_title="Downloads", layout="wide",
                   initial_sidebar_state="collapsed")
style.apply_style()
style.require_password()
style.topnav("Downloads")

LANG = i18n.current_lang()
style.page_head(i18n.t("ph_downloads_crumb"),
                "Datenexport" if LANG == "de" else "Data export",
                ("Einzelne Tabellen, das gesamte CSV-Bundle oder die SQLite-DB · "
                 "alle Daten lokal und synthetisch.") if LANG == "de" else
                ("Single tables, the full CSV bundle or the SQLite DB · "
                 "all data local and synthetic."))

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


@st.cache_data(show_spinner="Lade …", ttl=600)
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
if LANG == "de":
    dl_lbl = ("CSV-Tabellen", "CSV-Gesamtgrösse", "SQLite-DB",
              "Generator-Seed", "Stand")
else:
    dl_lbl = ("CSV tables", "CSV total size", "SQLite DB",
              "Generator seed", "As of")
style.kpi_strip([
    {"label": dl_lbl[0], "value": str(len(csv_files))},
    {"label": dl_lbl[1], "value": human_size(total_csv) if csv_files else "—"},
    {"label": dl_lbl[2], "value": human_size(db_size) if db_size else "—"},
    {"label": dl_lbl[3], "value": str(config.SEED)},
    {"label": dl_lbl[4], "value": dt.date.today().strftime("%d.%m.%Y")},
])

style.section_head("CSV pro Tabelle" if LANG == "de" else "CSV per table",
                   count=(f"{len(csv_files)} Dateien" if LANG == "de"
                          else f"{len(csv_files)} files"))
if not csv_files:
    st.warning("CSV-Verzeichnis fehlt. Bitte `python scripts/generate.py` ausführen."
               if LANG == "de" else
               "CSV directory missing. Run `python scripts/generate.py`.")
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
            dl_label = (f"{p.name} herunterladen" if LANG == "de"
                        else f"Download {p.name}")
            st.download_button(
                label=dl_label,
                data=_read_bytes(str(p)),
                file_name=p.name,
                mime="text/csv",
                key=f"dl_{p.name}",
                use_container_width=True,
            )

style.section_head("Bundle · alle CSVs als ZIP" if LANG == "de"
                   else "Bundle · all CSVs as ZIP")
if csv_files:
    paths = tuple(sorted(str(p) for p in csv_files))
    cols = st.columns([2, 3])
    bundle_caption = (f"**{len(paths)} Dateien** · {human_size(total_csv)}" if LANG == "de"
                      else f"**{len(paths)} files** · {human_size(total_csv)}")
    cols[0].markdown(bundle_caption)
    zip_btn = "ZIP erstellen" if LANG == "de" else "Build ZIP"
    if cols[1].button(zip_btn, use_container_width=True):
        st.session_state["_zip_built"] = _build_csv_zip(paths)
    if "_zip_built" in st.session_state:
        zip_dl = ("kreditueberwachung_csv.zip herunterladen" if LANG == "de"
                  else "Download kreditueberwachung_csv.zip")
        st.download_button(
            label=zip_dl,
            data=st.session_state["_zip_built"],
            file_name=f"kreditueberwachung_csv_{dt.date.today().isoformat()}.zip",
            mime="application/zip", use_container_width=True,
        )

style.section_head("SQLite-Datenbank" if LANG == "de" else "SQLite database")
if DB_PATH.exists():
    tbls_lbl = "Tabellen" if LANG == "de" else "tables"
    st.markdown(
        f"""
<div class="ku-card">
  <div style="font-family:var(--mono);color:var(--ink);font-size:0.92rem">{DB_PATH}</div>
  <div style="color:var(--ink-3);font-size:0.82rem;margin-top:6px">
    {human_size(db_size)} · {len(csv_files)} {tbls_lbl}
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    if db_size < 500 * 1024 * 1024:
        dl_label = (f"{DB_PATH.name} herunterladen" if LANG == "de"
                    else f"Download {DB_PATH.name}")
        st.download_button(
            label=dl_label,
            data=_read_bytes(str(DB_PATH)),
            file_name=DB_PATH.name,
            mime="application/x-sqlite3",
            use_container_width=True,
        )
    else:
        info_msg = (f"DB ist {human_size(db_size)} – zu gross für Browser-Download. "
                    f"Direkt von der Festplatte kopieren:\n\n```bash\ncp {DB_PATH} ~/Downloads/\n```"
                    if LANG == "de" else
                    f"DB is {human_size(db_size)} — too large for a browser download. "
                    f"Copy directly from disk:\n\n```bash\ncp {DB_PATH} ~/Downloads/\n```")
        st.info(info_msg)

style.section_head("Individuelle Abfrage" if LANG == "de" else "Custom query")
default_sql = (
    "SELECT l.loan_id, c.last_name, a.canton, l.current_outstanding, l.ltv_pct, l.dsti_pct\n"
    "FROM loan l\n"
    "JOIN client   c ON c.client_id = l.primary_client_id\n"
    "JOIN property p USING(property_id)\n"
    "JOIN address  a ON a.address_id = p.address_id\n"
    "ORDER BY l.current_outstanding DESC LIMIT 1000"
)
sql_lbl = "SQL · nur Lesen" if LANG == "de" else "SQL · read-only"
sql = st.text_area(sql_lbl, default_sql, height=180)
exec_lbl = "Abfrage ausführen" if LANG == "de" else "Run query"
if st.button(exec_lbl, use_container_width=True):
    s = sql.strip().rstrip(";").lower()
    if not s.startswith("select"):
        st.error("Nur SELECT erlaubt." if LANG == "de" else "SELECT only.")
    elif any(b in s for b in (" insert ", " update ", " delete ", " drop ", " alter ", "pragma ")):
        st.error("Nur lesende Abfragen." if LANG == "de" else "Read-only queries.")
    else:
        try:
            df = data.query(sql)
            success_msg = (f"{len(df):,} Zeilen." if LANG == "de"
                           else f"{len(df):,} rows.").replace(",", "'")
            st.success(success_msg)
            st.dataframe(df.head(500), use_container_width=True, height=320, hide_index=True)
            dl_csv = "result.csv herunterladen" if LANG == "de" else "Download result.csv"
            st.download_button(
                label=dl_csv,
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="result.csv", mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            err = (f"Abfrage fehlgeschlagen: {e}" if LANG == "de"
                   else f"Query failed: {e}")
            st.error(err)

style.section_head("JSON · Kreditdossier" if LANG == "de" else "JSON · loan dossier")
lid_lbl = "Kredit-ID" if LANG == "de" else "Loan ID"
lid = st.number_input(lid_lbl, min_value=0, value=0, step=1, key="dl_loanid")
if lid:
    bundle = data.loan_full(int(lid))
    if bundle.get("loan", None) is None or bundle["loan"].empty:
        st.warning("Kredit nicht gefunden." if LANG == "de" else "Loan not found.")
    else:
        payload = {k: v.to_dict(orient="records") for k, v in bundle.items() if v is not None}
        dl_label = (f"dossier_loan_{int(lid)}.json herunterladen" if LANG == "de"
                    else f"Download dossier_loan_{int(lid)}.json")
        st.download_button(
            label=dl_label,
            data=json.dumps(payload, default=str, indent=2).encode("utf-8"),
            file_name=f"dossier_loan_{int(lid)}.json",
            mime="application/json",
            use_container_width=True,
        )

style.footer()
