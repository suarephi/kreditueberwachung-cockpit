"""Design system: bone + slate + slate-blue, per claude.ai/design handoff.

Tokens mirror the CSS variables in `designs/uebersicht.html` of the handoff.
Type stack: Source Serif 4 (headlines, KPI numerals), Inter Tight (UI/body),
JetBrains Mono (IDs, canton tags). Localised in German with Swiss number format.
"""
from __future__ import annotations
from urllib.parse import quote
import streamlit as st
import plotly.io as pio
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Tokens — verbatim from handoff
# ---------------------------------------------------------------------------
BG          = "#F2F1ED"
BG_ELEV     = "#F8F7F3"
SURFACE     = "#FFFFFF"
SURFACE_2   = "#F4F3EE"
LINE        = "#E2E0D9"
LINE_SOFT   = "#ECEAE3"
LINE_STRONG = "#CBC9C0"

INK         = "#1B1D20"
INK_2       = "#353840"
INK_3       = "#6A6E76"
INK_4       = "#9A9CA1"
INK_5       = "#BEC0C4"

# Slate-blue accent — using the ~equivalent hex of oklch(0.52 0.06 235)
ACCENT      = "#3B5874"
ACCENT_INK  = "#2B4256"
ACCENT_SOFT = "#EAEFF4"
ACCENT_LINE = "#C5D2DF"

SEV_RED          = "#B05541"
SEV_RED_SOFT     = "#F5E2DD"
SEV_AMBER        = "#C29447"
SEV_AMBER_SOFT   = "#F2E8D2"
SEV_GREEN        = "#5A8B5A"
SEV_GREEN_SOFT   = "#E1ECDF"
SEV_BLUE         = "#5A7AA0"
SEV_BLUE_SOFT    = "#E0E7F0"

# 5-stop neutral slate scale for choropleth
CHOROPLETH_STOPS = ["#ECEAE3", "#D6D5CC", "#A9ADB1", "#6E7782", "#3B4452"]

# Categorical chart palette
CHART_COLORWAY = [INK_2, "#4F535C", "#6A6E76", "#9A9CA1", ACCENT, SEV_RED, SEV_AMBER, SEV_GREEN]

SEVERITY_COLORS = {
    "info":     SEV_BLUE,
    "low":      SEV_GREEN,
    "medium":   SEV_AMBER,
    "high":     "#A04A28",
    "critical": SEV_RED,
}


# ---------------------------------------------------------------------------
# Top nav routing — order from handoff
# ---------------------------------------------------------------------------
# (de_label, href, i18n_key) — de_label is also the `active` value the page passes in.
NAV_ITEMS = [
    ("Übersicht",     "/",              "nav_overview"),
    ("Überwachung",   "/Überwachung",   "nav_monitoring"),
    ("Risikofälle",   "/Risikofälle",   "nav_risk_cases"),
    ("Kreditdossier", "/Kreditdossier", "nav_dossier"),
    ("Wertschriften", "/Wertschriften", "nav_securities"),
    ("Konten",        "/Konten",        "nav_accounts"),
    ("Stresstest",    "/Stresstest",    "nav_stress"),
    ("Datenqualität", "/Datenqualität", "nav_data_quality"),
    ("Datenprofil",   "/Datenprofil",   "nav_data_profile"),
    ("Downloads",     "/Downloads",     "nav_downloads"),
]


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def _css() -> str:
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&family=JetBrains+Mono:wght@400;500&display=swap">

<style>
:root {{
  --bg: {BG};
  --bg-elev: {BG_ELEV};
  --surface: {SURFACE};
  --surface-2: {SURFACE_2};
  --line: {LINE};
  --line-soft: {LINE_SOFT};
  --line-strong: {LINE_STRONG};
  --ink: {INK};
  --ink-2: {INK_2};
  --ink-3: {INK_3};
  --ink-4: {INK_4};
  --ink-5: {INK_5};
  --accent: {ACCENT};
  --accent-ink: {ACCENT_INK};
  --accent-soft: {ACCENT_SOFT};
  --accent-line: {ACCENT_LINE};
  --sev-red: {SEV_RED};
  --sev-red-soft: {SEV_RED_SOFT};
  --sev-amber: {SEV_AMBER};
  --sev-amber-soft: {SEV_AMBER_SOFT};
  --sev-green: {SEV_GREEN};
  --sev-green-soft: {SEV_GREEN_SOFT};
  --sev-blue: {SEV_BLUE};
  --sev-blue-soft: {SEV_BLUE_SOFT};
  --sans: "Inter Tight","Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --serif: "Source Serif 4","Source Serif Pro",Georgia,serif;
  --mono: "JetBrains Mono","SF Mono",Menlo,ui-monospace,monospace;
  --r-sm: 4px; --r: 6px; --r-md: 8px; --r-lg: 12px;
  --shadow-sm: 0 1px 0 rgba(31,27,22,0.04), 0 1px 2px rgba(31,27,22,0.04);
}}

html, body, .stApp, [class*="css"], .stMarkdown, .stText {{
  font-family: var(--sans) !important;
  color: var(--ink);
  font-feature-settings: "ss01" on, "tnum" 0;
}}
.stApp {{ background: var(--bg); }}

/* Hide Streamlit's default chrome and sidebar */
header[data-testid="stHeader"] {{ display: none; }}
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{
  display: none !important;
}}
section[data-testid="stSidebar"] {{ width: 0 !important; }}

/* Page padding */
.block-container {{
  padding-top: 0 !important;
  padding-left: 32px !important;
  padding-right: 32px !important;
  padding-bottom: 48px !important;
  max-width: 1500px !important;
}}

/* Numerals */
.tnum, .num {{ font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }}

/* Headlines: serif */
h1, h2, h3, h4 {{
  font-family: var(--serif) !important;
  font-weight: 500 !important;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin: 0;
}}
h1 {{ font-size: 36px !important; line-height: 1.15 !important; letter-spacing: -0.02em !important; }}
h2 {{ font-size: 22px !important; line-height: 1.2 !important; }}
h3 {{ font-size: 17px !important; line-height: 1.25 !important; }}

/* Eyebrow */
.ku-eyebrow {{
  font-family: var(--sans);
  font-size: 11px; font-weight: 500; letter-spacing: 0.10em;
  text-transform: uppercase; color: var(--ink-3);
}}

/* ===== TOP NAV ===== */
.ku-topbar {{
  background: var(--bg-elev);
  border-bottom: 1px solid var(--line);
  position: sticky; top: 0; z-index: 50;
  backdrop-filter: blur(8px);
  margin: -2rem -32px 0 -32px;
  padding: 0 32px;
}}
.ku-topbar-inner {{
  height: 60px; max-width: 1500px; margin: 0 auto;
  display: flex; align-items: center; gap: 28px;
}}
.ku-brand {{
  display: flex; align-items: center; gap: 10px;
  font-family: var(--serif); font-size: 17px; font-weight: 500;
  letter-spacing: -0.01em; color: var(--ink);
}}
.ku-brand-mark {{
  width: 26px; height: 26px; border-radius: 6px;
  background: var(--ink); color: var(--bg-elev);
  display: grid; place-items: center;
  font-family: var(--serif); font-size: 14px; font-weight: 500;
}}
.ku-brand small {{
  font-family: var(--sans); font-size: 11px; font-weight: 400;
  color: var(--ink-3); margin-left: 4px;
  text-transform: uppercase; letter-spacing: 0.08em;
}}
.ku-nav {{ display: flex; align-items: center; gap: 2px; margin-left: 4px; }}
.ku-nav a {{
  padding: 8px 12px; border-radius: var(--r);
  font-size: 13.5px; font-weight: 500;
  color: var(--ink-3); position: relative;
  text-decoration: none !important;
  transition: color .15s, background .15s;
}}
.ku-nav a:hover {{ color: var(--ink); background: var(--surface-2); }}
.ku-nav a.active {{ color: var(--ink); }}
.ku-nav a.active::after {{
  content: ""; position: absolute; left: 12px; right: 12px; bottom: -16px;
  height: 2px; background: var(--accent); border-radius: 2px;
}}
.ku-topbar-right {{
  margin-left: auto; display: flex; align-items: center; gap: 12px;
}}
.ku-search {{
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; background: var(--surface);
  border: 1px solid var(--line); border-radius: var(--r);
  font-size: 12.5px; color: var(--ink-3); width: 240px;
}}
.ku-search input {{
  border: 0; background: transparent; outline: none;
  font: inherit; color: var(--ink); flex: 1;
}}
.ku-search kbd {{
  font-family: var(--mono); font-size: 10.5px; padding: 1px 5px;
  border: 1px solid var(--line); border-radius: 3px;
  color: var(--ink-3); background: var(--bg);
}}
.ku-userchip {{
  display: flex; align-items: center; gap: 8px;
  padding: 4px 10px 4px 4px; border-radius: 999px;
  background: var(--surface); border: 1px solid var(--line);
  font-size: 12.5px;
}}
.ku-avatar {{
  width: 24px; height: 24px; border-radius: 999px;
  background: var(--accent-soft); color: var(--accent-ink);
  display: grid; place-items: center;
  font-size: 11px; font-weight: 600;
}}

/* ===== PAGE HEAD ===== */
.ku-pagehead {{
  padding: 28px 0 20px; display: flex; align-items: flex-end;
  justify-content: space-between; gap: 32px;
}}
.ku-crumb {{
  display: flex; align-items: center; gap: 8px;
  color: var(--ink-3); font-size: 12px; margin-bottom: 8px;
}}
.ku-crumb .sep {{ color: var(--ink-5); }}
.ku-pagehead h1 {{ font-size: 36px !important; }}
.ku-pagehead p {{
  margin: 8px 0 0; color: var(--ink-3);
  font-size: 14px; max-width: 580px; line-height: 1.55;
}}
.ku-pagemeta {{
  display: flex; align-items: center; gap: 16px;
  color: var(--ink-3); font-size: 12.5px;
}}
.ku-pulse {{
  width: 7px; height: 7px; border-radius: 999px;
  background: var(--sev-green);
  box-shadow: 0 0 0 4px rgba(90,139,90,0.18);
}}

/* ===== SECTION HEAD ===== */
.ku-sectionhead {{
  display: flex; align-items: baseline; justify-content: space-between;
  margin: 28px 0 14px; gap: 16px;
}}
.ku-sectionhead .left {{ display: flex; align-items: baseline; gap: 12px; }}
.ku-sectionhead h2 {{ font-size: 20px !important; }}
.ku-sectionhead .count {{
  color: var(--ink-3); font-size: 13px;
  font-variant-numeric: tabular-nums;
}}

/* ===== CARDS ===== */
.ku-card {{
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r-md); padding: 20px; position: relative;
}}
.ku-card-flush {{ padding: 0; }}
.ku-cardhead {{
  display: flex; align-items: baseline; justify-content: space-between;
  margin-bottom: 16px; gap: 16px;
}}
.ku-cardtitle {{
  font-family: var(--serif); font-size: 16px; font-weight: 500;
  letter-spacing: -0.01em; color: var(--ink);
}}
.ku-cardsub {{ color: var(--ink-3); font-size: 12px; margin-top: 2px; }}

/* Streamlit native containers — make them blend */
[data-testid="stPlotlyChart"] {{
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r-md); padding: 8px;
}}
[data-testid="stDataFrame"] {{
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r-md); overflow: hidden;
}}
[data-testid="stMetric"] {{
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r-md); padding: 16px 18px !important;
}}
[data-testid="stMetricLabel"] {{
  color: var(--ink-3) !important; font-weight: 500 !important;
  font-size: 11.5px !important; text-transform: uppercase;
  letter-spacing: 0.06em;
}}
[data-testid="stMetricValue"] {{
  font-family: var(--serif) !important; font-weight: 400 !important;
  color: var(--ink) !important; font-size: 28px !important;
  letter-spacing: -0.015em; font-variant-numeric: tabular-nums;
}}
[data-testid="stMetricDelta"] {{ font-size: 12px !important; color: var(--ink-3) !important; }}
[data-testid="stMetricDelta"] svg {{ display: none; }}

/* ===== KPI STRIP (custom) ===== */
.ku-kpistrip {{
  display: grid; grid-template-columns: repeat(5, 1fr);
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r-md); overflow: hidden;
}}
.ku-kpi {{ padding: 18px 20px 16px; border-right: 1px solid var(--line-soft); position: relative; }}
.ku-kpi:last-child {{ border-right: 0; }}
.ku-kpi-label {{
  font-size: 11.5px; font-weight: 500; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--ink-3);
}}
.ku-kpi-value {{
  font-family: var(--serif); font-size: 28px; font-weight: 400;
  margin-top: 6px; letter-spacing: -0.015em; color: var(--ink);
  font-variant-numeric: tabular-nums;
}}
.ku-kpi-value .unit {{
  font-family: var(--sans); font-size: 13px; color: var(--ink-3);
  font-weight: 500; margin-left: 4px; letter-spacing: 0;
}}
.ku-kpi-foot {{
  margin-top: 10px; display: flex; align-items: center;
  justify-content: space-between; gap: 8px;
}}
.ku-delta {{
  font-size: 12px; display: inline-flex; align-items: center; gap: 3px;
  font-variant-numeric: tabular-nums; font-weight: 500;
}}
.ku-delta.up.good, .ku-delta.down.good {{ color: var(--sev-green); }}
.ku-delta.up.bad, .ku-delta.down.bad   {{ color: var(--sev-red); }}
.ku-delta.flat                          {{ color: var(--ink-3); }}
.ku-delta-meta {{ color: var(--ink-4); font-weight: 400; margin-left: 4px; }}

/* ===== CHIPS ===== */
.ku-chip {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 9px; border-radius: 999px;
  font-size: 11.5px; font-weight: 500;
  background: var(--surface-2); color: var(--ink-2);
  border: 1px solid var(--line); white-space: nowrap;
}}
.ku-chip .dot {{ width: 6px; height: 6px; border-radius: 999px; background: var(--ink-4); }}
.ku-chip.red    {{ background: var(--sev-red-soft);   color: #7A2718; border-color: #E8C8C0; }}
.ku-chip.red    .dot {{ background: var(--sev-red); }}
.ku-chip.amber  {{ background: var(--sev-amber-soft); color: #6E4F12; border-color: #DCC59A; }}
.ku-chip.amber  .dot {{ background: var(--sev-amber); }}
.ku-chip.green  {{ background: var(--sev-green-soft); color: #2F5F2F; border-color: #BBD0BB; }}
.ku-chip.green  .dot {{ background: var(--sev-green); }}
.ku-chip.blue   {{ background: var(--sev-blue-soft);  color: #2C4A6E; border-color: #B6C8DB; }}
.ku-chip.blue   .dot {{ background: var(--sev-blue); }}

/* Canton tag */
.ku-tag {{
  font-family: var(--mono); font-size: 10.5px; font-weight: 600;
  padding: 2px 5px; background: var(--bg);
  border: 1px solid var(--line); border-radius: 3px;
  color: var(--ink-2); letter-spacing: 0.04em;
}}

/* ===== NAV CARDS ===== */
.ku-navcards {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
}}
.ku-navcard {{
  display: flex; align-items: flex-start; gap: 16px;
  padding: 20px; background: var(--surface);
  border: 1px solid var(--line); border-radius: var(--r-md);
  transition: border-color .15s, transform .15s, box-shadow .15s;
  text-decoration: none !important; color: inherit;
}}
.ku-navcard:hover {{
  border-color: var(--line-strong); transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}}
.ku-nc-num {{
  font-family: var(--serif); font-size: 32px; font-weight: 400;
  color: var(--ink-4); letter-spacing: -0.02em;
  width: 44px; line-height: 1;
}}
.ku-nc-body {{ flex: 1; }}
.ku-nc-title {{ font-family: var(--serif); font-size: 17px; font-weight: 500; letter-spacing: -0.01em; }}
.ku-nc-sub {{ color: var(--ink-3); font-size: 12.5px; margin-top: 4px; line-height: 1.5; }}
.ku-nc-meta {{ font-size: 11.5px; color: var(--ink-4); margin-top: 10px; font-variant-numeric: tabular-nums; }}
.ku-nc-arr {{ color: var(--ink-4); margin-top: 6px; transition: transform .15s, color .15s; font-size: 16px; }}
.ku-navcard:hover .ku-nc-arr {{ color: var(--accent); transform: translateX(2px); }}

@media (max-width: 1280px) {{
  .ku-navcards {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* ===== Stress tile (action centre) ===== */
.ku-stress-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }}
.ku-stress-tile {{
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--r); padding: 8px 10px;
  font-size: 10.5px; color: var(--ink-3);
  letter-spacing: 0.04em; text-transform: uppercase; line-height: 1.35;
}}
.ku-stress-tile strong {{
  display: block; font-family: var(--serif); font-size: 18px; font-weight: 500;
  color: var(--ink); margin-top: 4px; letter-spacing: -0.01em;
  text-transform: none; font-variant-numeric: tabular-nums;
}}
.ku-stress-tile.severe {{ background: var(--sev-red-soft); border-color: #E8C8C0; }}
.ku-stress-tile.severe strong {{ color: var(--sev-red); }}

/* DQ row */
.ku-dq-row {{
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 8px 0; border-bottom: 1px dashed var(--line-soft); font-size: 13px;
}}
.ku-dq-row:last-child {{ border-bottom: 0; }}
.ku-dq-row span {{ color: var(--ink-2); }}
.ku-dq-row strong {{
  font-variant-numeric: tabular-nums;
  font-family: var(--serif); font-weight: 500; font-size: 15px; color: var(--ink);
}}

/* ===== FOOTER ===== */
.ku-footer {{
  margin-top: 48px; padding: 20px 0 32px;
  border-top: 1px solid var(--line);
  color: var(--ink-3); font-size: 12px;
  display: flex; justify-content: space-between; align-items: center;
}}

/* ===== TABS ===== */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
  background: transparent; border-bottom: 1px solid var(--line);
  gap: 0; margin-bottom: 16px;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
  padding: 8px 14px !important; font-size: 13px !important;
  font-weight: 500 !important; color: var(--ink-3) !important;
  background: transparent !important;
  border-radius: 0 !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
  color: var(--ink) !important; background: transparent !important;
  border-bottom: 2px solid var(--accent) !important;
}}

/* Inputs */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"] > div {{
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
}}
[data-baseweb="select"] > div:focus-within, [data-baseweb="input"] > div:focus-within {{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(59,88,116,0.10) !important;
}}

/* Buttons */
.stButton > button, .stDownloadButton > button {{
  background: var(--ink); color: var(--bg-elev);
  border: 1px solid var(--ink); border-radius: var(--r);
  font-size: 12.5px; font-weight: 500; padding: 7px 14px;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{ background: var(--ink-2); }}

/* Alert blocks */
[data-testid="stAlert"] {{
  border-radius: var(--r-md); border: 1px solid var(--line);
  background: var(--surface);
}}

/* ----------------------------------------------------------------------
   Loading indicators — top-of-page progress bar + branded native spinner
   ---------------------------------------------------------------------- */
.stApp::before {{
  content: ""; position: fixed; top: 0; left: 0; right: 0; height: 2px;
  z-index: 1000; pointer-events: none;
  background: linear-gradient(90deg,
      transparent 0%, var(--accent-line) 30%, var(--accent) 50%,
      var(--accent-line) 70%, transparent 100%);
  background-size: 220% 100%;
  opacity: 0;
  transition: opacity 200ms ease-out;
}}
.stApp[data-test-script-state="running"]::before,
.stApp[data-test-script-state="rerunning"]::before {{
  opacity: 1;
  animation: ku-loadbar 1.1s linear infinite;
}}
@keyframes ku-loadbar {{
  0%   {{ background-position: 100% 0%; }}
  100% {{ background-position: -120% 0%; }}
}}

/* Streamlit native running indicator (top-right) → olive instead of red */
[data-testid="stStatusWidget"] {{
  background: var(--surface) !important;
  border: 1px solid var(--accent-line) !important;
  color: var(--accent) !important;
}}

/* Native st.spinner() inline blocks — branded olive ring + cream label card */
[data-testid="stSpinner"] {{
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  padding: 14px 18px;
  display: inline-flex; align-items: center; gap: 12px;
  color: var(--ink-2);
  font-size: 13px; font-weight: 500;
  letter-spacing: 0.01em;
}}
[data-testid="stSpinner"] > div:first-child,
[data-testid="stSpinner"] svg {{
  border-color: var(--accent-soft) !important;
  border-top-color: var(--accent) !important;
  color: var(--accent) !important;
  stroke: var(--accent) !important;
}}

/* Language toggle in topnav (DE | EN) */
.ku-langtoggle {{
  display: inline-flex; align-items: center; gap: 4px;
  font-family: var(--mono); font-size: 11px; font-weight: 600;
  letter-spacing: 0.06em; padding: 4px 8px;
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 6px;
}}
.ku-langtoggle .ku-lang-on {{
  color: var(--accent); padding: 2px 4px;
}}
.ku-langtoggle .ku-lang-off {{
  color: var(--ink-4); padding: 2px 4px; text-decoration: none;
  border-left: 1px solid var(--line);
}}
.ku-langtoggle .ku-lang-off:hover {{
  color: var(--ink); background: var(--surface-2); border-radius: 3px;
}}

/* Skeleton-pulse for cached dataframes during initial load */
[data-testid="stDataFrame"][aria-busy="true"] {{
  background: linear-gradient(90deg,
      var(--surface) 0%, var(--surface-2) 50%, var(--surface) 100%);
  background-size: 200% 100%;
  animation: ku-shimmer 1.4s ease-in-out infinite;
  border-radius: var(--r-md);
}}
@keyframes ku-shimmer {{
  0%   {{ background-position: 100% 0%; }}
  100% {{ background-position: -100% 0%; }}
}}
</style>
"""


# ---------------------------------------------------------------------------
# Plotly template
# ---------------------------------------------------------------------------
def _register_template() -> None:
    pio.templates["ku_slate"] = go.layout.Template(
        layout=dict(
            font=dict(
                family='"Inter Tight",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
                size=12, color=INK_2),
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            colorway=CHART_COLORWAY,
            xaxis=dict(gridcolor=LINE_SOFT, zerolinecolor=LINE,
                       linecolor=LINE, tickcolor=LINE,
                       tickfont=dict(color=INK_4, family="JetBrains Mono", size=10)),
            yaxis=dict(gridcolor=LINE_SOFT, zerolinecolor=LINE,
                       linecolor=LINE, tickcolor=LINE,
                       tickfont=dict(color=INK_4, family="JetBrains Mono", size=10)),
            margin=dict(l=8, r=8, t=8, b=22),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=INK_2, size=11)),
            hoverlabel=dict(bgcolor=SURFACE, bordercolor=LINE,
                            font=dict(family='"JetBrains Mono", monospace',
                                      color=INK_2, size=12)),
            hovermode="closest",
        )
    )
    pio.templates.default = "ku_slate"


_register_template()


# ---------------------------------------------------------------------------
# Reusable components
# ---------------------------------------------------------------------------
def apply_style() -> None:
    st.markdown(_css(), unsafe_allow_html=True)


def topnav(active: str = "Übersicht") -> None:
    """Sticky top nav with brand mark + 8 links + search + lang toggle + user chip."""
    from . import i18n  # local import — module imports streamlit
    lang = i18n.current_lang()
    qp_parts = []
    if auth_token():
        qp_parts.append(f"k={auth_token()}")
    qp_parts.append(f"lang={lang}")
    suffix = "?" + "&".join(qp_parts)

    links = []
    for de_label, href, key in NAV_ITEMS:
        cls = "active" if de_label == active else ""
        url = "/" if href == "/" else "/" + quote(href.lstrip("/"))
        display = i18n.t(key)
        links.append(f'<a class="{cls}" href="{url}{suffix}" target="_self">{display}</a>')

    # Lang toggle: build a URL that flips ?lang= but preserves k= and the page.
    other_lang = "en" if lang == "de" else "de"
    toggle_qp = []
    if auth_token():
        toggle_qp.append(f"k={auth_token()}")
    toggle_qp.append(f"lang={other_lang}")
    # Re-use NAV_ITEMS to get the current page's href — no manual encoding.
    here_href = next((h for lbl, h, _k in NAV_ITEMS if lbl == active), "/")
    here_path = "/" if here_href == "/" else "/" + quote(here_href.lstrip("/"))
    toggle_url = f"{here_path}?{'&'.join(toggle_qp)}"
    lang_html = (
        '<div class="ku-langtoggle">'
        f'<span class="ku-lang-on">{lang.upper()}</span>'
        f'<a class="ku-lang-off" href="{toggle_url}" target="_self" '
        f'title="Switch to {other_lang.upper()}">{other_lang.upper()}</a>'
        '</div>'
    )

    search_placeholder = i18n.t("search_placeholder")
    html = (
        '<div class="ku-topbar"><div class="ku-topbar-inner">'
        '<div class="ku-brand"><div class="ku-brand-mark">K</div>'
        'Kreditüberwachung <small>Cockpit</small></div>'
        f'<nav class="ku-nav" aria-label="Hauptnavigation">{"".join(links)}</nav>'
        '<div class="ku-topbar-right">'
        f'{lang_html}'
        f'<label class="ku-search"><span style="opacity:0.6">⌕</span>'
        f'<input placeholder="{search_placeholder}" disabled>'
        '<kbd>⌘K</kbd></label>'
        '<div class="ku-userchip"><div class="ku-avatar">ES</div>'
        '<span>E. Schärli</span></div>'
        '</div></div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def page_head(crumb: str, title: str, subtitle: str | None = None,
              meta_html: str | None = None) -> None:
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    meta = meta_html or (
        '<span class="ku-pulse" aria-hidden="true"></span>'
        '<span><strong style="color:var(--ink-2);font-weight:600">Live</strong> · '
        '28. April 2026, 08:14</span>'
    )
    html = (
        '<section class="ku-pagehead"><div>'
        '<div class="ku-crumb"><span>Cockpit</span>'
        f'<span class="sep">/</span><span>{crumb}</span></div>'
        f'<h1>{title}</h1>{sub}</div>'
        f'<div class="ku-pagemeta">{meta}</div></section>'
    )
    st.markdown(html, unsafe_allow_html=True)


def section_head(title: str, count: str | None = None, right_html: str = "") -> None:
    cnt = f'<span class="count">{count}</span>' if count else ""
    html = (
        '<div class="ku-sectionhead"><div class="left">'
        f'<h2>{title}</h2>{cnt}</div>'
        f'<div>{right_html}</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def chip(text: str, kind: str = "", tooltip: str = "") -> str:
    """Return an HTML pill (use inside st.markdown)."""
    cls = f"ku-chip {kind}" if kind else "ku-chip"
    tip = f' title="{_html_escape(tooltip)}"' if tooltip else ""
    cursor = ' style="cursor:help"' if tooltip else ""
    return f'<span class="{cls}"{tip}{cursor}><span class="dot"></span>{text}</span>'


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace('"', "&quot;")
             .replace("<", "&lt;").replace(">", "&gt;"))


def tag_canton(code: str) -> str:
    return f'<span class="ku-tag">{code}</span>'


def footer() -> None:
    from . import i18n
    html = (
        '<div class="ku-footer">'
        f'<span>{i18n.t("footer_left")}</span>'
        f'<span>{i18n.t("footer_right").replace("&", "&amp;")}</span>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Password gate
#
# Streamlit creates a new session per HTTP page load, so `st.session_state`
# alone doesn't survive plain `<a href>` navigation. We mint an opaque session
# token on successful login, persist it in the URL query (`?k=<token>`), and
# every nav link in `topnav()` carries it forward — so one password unlocks
# the whole cockpit for the rest of the visit.
# ---------------------------------------------------------------------------
PASSWORD = "ilovekpmg"
import hashlib as _hashlib
AUTH_TOKEN = _hashlib.sha256(("kreditueberwachung:" + PASSWORD).encode()).hexdigest()[:24]


def auth_token() -> str:
    """Return the current URL auth token if the visitor is authenticated."""
    if st.session_state.get("_authed"):
        return AUTH_TOKEN
    return ""


def require_password() -> None:
    """Block page rendering until the visitor enters the correct password."""
    # Already authed in this session
    if st.session_state.get("_authed"):
        return
    # URL-based persistence (carried across pages via topnav links)
    if st.query_params.get("k") == AUTH_TOKEN:
        st.session_state["_authed"] = True
        return

    st.markdown(
        '<div style="max-width:420px;margin:90px auto 0 auto">'
        '<div class="ku-card" style="padding:32px">'
        '<div class="ku-eyebrow" style="margin-bottom:8px">Zugang</div>'
        '<div style="font-family:var(--serif);font-size:24px;font-weight:500;'
        'letter-spacing:-0.018em;margin-bottom:6px">Kreditüberwachung Cockpit</div>'
        '<div style="color:var(--ink-3);font-size:13px;margin-bottom:18px;line-height:1.5">'
        'Geschützter Bereich. Bitte Passwort eingeben.'
        '</div></div></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns([1, 2, 1])
    with cols[1]:
        pwd = st.text_input("Passwort", type="password",
                            placeholder="••••••••",
                            label_visibility="collapsed",
                            key="_pwd_input")
        if pwd:
            if pwd == PASSWORD:
                st.session_state["_authed"] = True
                st.query_params["k"] = AUTH_TOKEN
                st.rerun()
            else:
                st.error("Falsches Passwort.")
    st.stop()


# ---------------------------------------------------------------------------
# Sparkline (inline SVG)
# ---------------------------------------------------------------------------
def sparkline(points: list[float], width: int = 88, height: int = 22,
              color: str | None = None, fill: bool = True) -> str:
    if not points:
        return ""
    color = color or ACCENT_INK
    pad = 1.5
    mn, mx = min(points), max(points)
    rng = mx - mn or 1.0
    sx = (width - pad * 2) / max(len(points) - 1, 1)
    parts = []
    for i, v in enumerate(points):
        x = pad + i * sx
        y = pad + (height - pad * 2) * (1 - (v - mn) / rng)
        parts.append(f"{'M' if i == 0 else 'L'}{x:.2f},{y:.2f}")
    path = " ".join(parts)
    last_x = pad + (len(points) - 1) * sx
    fill_path = f"{path} L{last_x:.2f},{height-pad} L{pad:.2f},{height-pad} Z"
    fill_svg = (f'<path d="{fill_path}" fill="{color}" fill-opacity="0.08"/>'
                if fill else "")
    return (f'<svg viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" '
            f'style="width:{width}px;height:{height}px">'
            f'{fill_svg}'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.25" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>')


# ---------------------------------------------------------------------------
# Swiss-German number formatting
# ---------------------------------------------------------------------------
def _ch_thousands(x: float, decimals: int = 0) -> str:
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "'")


def fmt_chf(v) -> str:
    if v is None or v != v:
        return "–"
    v = float(v)
    if abs(v) >= 1e9:
        return f"{_ch_thousands(v/1e9, 2)} Mrd. CHF"
    if abs(v) >= 1e6:
        return f"{_ch_thousands(v/1e6, 1)} Mio. CHF"
    if abs(v) >= 1e3:
        return f"{_ch_thousands(v/1e3, 0)} Tsd. CHF"
    return f"{_ch_thousands(v, 0)} CHF"


def fmt_pct(v, decimals: int = 1) -> str:
    if v is None:
        return "–"
    return f"{float(v):.{decimals}f}%"


def fmt_int(v) -> str:
    if v is None:
        return "–"
    return _ch_thousands(int(v), 0)


def fmt_compact(v) -> tuple[str, str]:
    """Return (number_str, unit_suffix) for a KPI value display."""
    if v is None:
        return ("–", "")
    v = float(v)
    if abs(v) >= 1e9:
        return (_ch_thousands(v/1e9, 2), "Mrd. CHF")
    if abs(v) >= 1e6:
        return (_ch_thousands(v/1e6, 1), "Mio. CHF")
    if abs(v) >= 1e3:
        return (_ch_thousands(v/1e3, 0), "Tsd. CHF")
    return (_ch_thousands(v, 0), "")


# ---------------------------------------------------------------------------
# KPI strip (5 cells in one bordered card)
# ---------------------------------------------------------------------------
def kpi_strip(items: list[dict]) -> None:
    """Render an N-cell KPI strip in one bordered card with internal dividers."""
    cells = []
    for it in items:
        label = it.get("label", "")
        value = it.get("value", "–")
        unit  = it.get("unit", "")
        unit_html = f'<span class="unit">{unit}</span>' if unit else ""
        right = it.get("foot_right_html", "")
        if not right and it.get("sparkline"):
            right = sparkline(it["sparkline"])
        left = it.get("delta_html", "")
        help_text = it.get("help", "")
        cell_attr = (f' title="{_html_escape(help_text)}" style="cursor:help"'
                     if help_text else "")
        label_hint = ' <span style="opacity:0.55;font-size:11px">ⓘ</span>' if help_text else ""
        cells.append(
            f'<div class="ku-kpi"{cell_attr}>'
            f'<div class="ku-kpi-label">{label}{label_hint}</div>'
            f'<div class="ku-kpi-value">{value}{unit_html}</div>'
            f'<div class="ku-kpi-foot">{left}<span>{right}</span></div>'
            '</div>'
        )
    st.markdown(
        f'<section class="ku-kpistrip">{"".join(cells)}</section>',
        unsafe_allow_html=True,
    )


def delta(value: str, meta: str = "", direction: str = "up", flavour: str = "good") -> str:
    """Render a delta string, e.g. '▲ 0.42%' with optional muted meta line."""
    arrow = {"up": "▲", "down": "▼", "flat": "−"}[direction]
    meta_html = f'<span class="ku-delta-meta">{meta}</span>' if meta else ""
    return (f'<span class="ku-delta {direction} {flavour}">{arrow} {value}'
            f'{meta_html}</span>')


# ---------------------------------------------------------------------------
# Nav cards (6-tile grid linking into the cockpit pages)
# ---------------------------------------------------------------------------
def nav_cards(items: list[dict]) -> None:
    """Each item: {num, title, sub, meta, href}."""
    suffix = f"?k={auth_token()}" if auth_token() else ""
    parts = []
    for it in items:
        href = it.get("href", "#")
        url = ("/" if href == "/" else ("/" + quote(href.lstrip("/")))) + suffix
        parts.append(
            f'<a class="ku-navcard" href="{url}" target="_self">'
            f'<div class="ku-nc-num">{it.get("num","")}</div>'
            f'<div class="ku-nc-body">'
            f'<div class="ku-nc-title">{it.get("title","")}</div>'
            f'<div class="ku-nc-sub">{it.get("sub","")}</div>'
            f'<div class="ku-nc-meta">{it.get("meta","")}</div>'
            f'</div><div class="ku-nc-arr">→</div></a>'
        )
    st.markdown(
        f'<div class="ku-navcards">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )
