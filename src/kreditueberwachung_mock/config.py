"""Generator configuration.

All knobs in one place. Override via environment variables (KU_N_CLIENTS, KU_SEED, ...).
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT          = Path(__file__).resolve().parents[2]
REFERENCE_DIR = ROOT / "reference_data"
SCHEMA_DIR    = ROOT / "schema"
SCENARIOS_DIR = ROOT / "scenarios"

# Output paths. Override with KU_OUTPUT_DIR (e.g. for a separate demo dataset
# that doesn't clobber the local 100k).
_default_output = ROOT / "output"
OUTPUT_DIR    = Path(os.environ.get("KU_OUTPUT_DIR", str(_default_output)))
CSV_DIR       = OUTPUT_DIR / "csv"
DB_PATH       = Path(os.environ.get("KU_DB_PATH", str(OUTPUT_DIR / "kreditueberwachung.db")))


def _int(env: str, default: int) -> int:
    v = os.environ.get(env)
    return int(v) if v else default


def _float(env: str, default: float) -> float:
    v = os.environ.get(env)
    return float(v) if v else default


# ---------------------------------------------------------------------------
# Scale knobs
# ---------------------------------------------------------------------------
N_CLIENTS              = _int("KU_N_CLIENTS", 100_000)
SEED                   = _int("KU_SEED", 42)

# Derived volume ratios (set on top of N_CLIENTS).
SHARE_WITH_LOAN        = 0.95   # → ~95k loans
SHARE_JOINT_BORROWER   = 0.30   # → joint households
TRANCHES_PER_LOAN_MEAN = 1.6
VALUATIONS_PER_PROPERTY = 5     # initial + 4 quarterly/annual revaluations
EVENTS_PER_LOAN_MEAN   = 6.5    # over loan lifetime; capped 0..30
CASES_PER_LOAN_MEAN    = 1.9
DOCS_PER_CLIENT_MEAN   = 7.0
AUDIT_PER_CLIENT_MEAN  = 2.5

# ---------------------------------------------------------------------------
# Financing ranges (per project spec)
# ---------------------------------------------------------------------------
PRICE_MIN              = 700_000.0
PRICE_MAX              = 5_500_000.0
LOAN_MIN               = 300_000.0
LOAN_MAX               = 4_500_000.0

# LTV distribution mix.
# Bulk 60-80%, broad 50-80% across vintages; lower tail 30-50% (paid-down);
# upper tail 80-100% rare (Sonderfälle); 100-110% very rare (underwater).
LTV_MIX = [
    # (weight, low, high)
    (0.10,  30,  50),    # paid-down older loans
    (0.18,  50,  60),    # mid range
    (0.42,  60,  75),    # bulk
    (0.20,  75,  80),    # near regulatory limit
    (0.07,  80,  90),    # exception cases
    (0.025, 90, 100),    # rare exceptions
    (0.005,100, 110),    # underwater, very rare
]

# ---------------------------------------------------------------------------
# Affordability constants (Swiss bank standard).
# ---------------------------------------------------------------------------
IMPUTED_INTEREST_PCT   = 5.0
MAINTENANCE_PCT        = 1.0
AMORT_TARGET_LTV       = 65.0       # amortize 1st mortgage above this
AMORT_HORIZON_YEARS    = 15
DSTI_THRESHOLD_PCT     = 33.0
EXCEPTION_APPROVAL_RATE = 0.07      # 7 % of loans granted via exception

# ---------------------------------------------------------------------------
# Object-type mix.
# ---------------------------------------------------------------------------
OBJECT_TYPE_MIX = [
    ("EFH",            0.35),
    ("ETW",            0.45),
    ("MFH",            0.08),
    ("Ferienwohnung",  0.05),
    ("Gewerbe",        0.05),
    ("Bauland",        0.02),
]

PRUDENCE_HAIRCUT = {
    "EFH":           0.05,
    "ETW":           0.05,
    "MFH":           0.10,
    "Ferienwohnung": 0.10,
    "Gewerbe":       0.15,
    "Bauland":       0.20,
}

# Historical FPRE-style index: synthesize quarterly per region+object_type.
INDEX_BASE_YEAR        = 2010
INDEX_LAST_YEAR        = 2025
INDEX_GROWTH_TO_2022   = 0.27        # cumulative (~+27 % nationwide)
INDEX_CORRECTION_2022_2024 = -0.04   # mild correction

# Reference rates (2010-2025, per cent).
SARON_PATH = [
    (2010, 0.20), (2012, 0.05), (2015, -0.75),
    (2018, -0.74), (2021, -0.74), (2022, 0.50),
    (2023, 1.75), (2024, 1.25), (2025, 0.50),
]
FIX_5Y_BASE_SPREAD     = 1.10
FIX_10Y_BASE_SPREAD    = 1.30

# ---------------------------------------------------------------------------
# Inconsistency injection rates (fraction of rows affected per rule).
# Logged to output/data_quality_issues.md after every run.
# ---------------------------------------------------------------------------
ERROR_RATES = {
    "name_umlaut_variant":          0.030,   # Müller → Mueller / Muller
    "name_case_anomaly":            0.010,   # MÜLLER / müller
    "name_double_space":            0.008,
    "name_hyphen_variant":          0.010,
    "name_trailing_whitespace":     0.012,
    "salutation_variant":           0.025,
    "date_dotformat":               0.050,   # birth_date stored DD.MM.YYYY
    "date_2digit_year":             0.010,
    "phone_format_variant":         0.080,   # not really an "error", but format mix
    "email_whitespace":             0.020,
    "email_missing_tld":            0.005,
    "email_double_at":              0.003,
    "city_localization_variant":    0.020,   # Geneva/Genf/Genève
    "city_diacritic_drop":          0.015,
    "plz_canton_mismatch":          0.003,
    "canton_full_name":             0.030,   # full name vs 2-letter
    "iban_typo":                    0.010,
    "ahv_format_error":             0.005,
    "null_surrogate":               0.020,   # "-" / "N/A" / "unbekannt"
    "money_string":                 0.020,   # "1'200'000"
    "encoding_nfd":                 0.005,
    "near_duplicate_client":        0.002,
    "mixed_language_record":        0.010,
}

# ---------------------------------------------------------------------------
# Stress overlay defaults.
# ---------------------------------------------------------------------------
STRESS_HORIZON_Q       = _int("KU_STRESS_HORIZON_Q", 12)   # 3 years quarterly
STRESS_START_PERIOD    = "2025-Q2"
STRESS_SAMPLE_PCT      = _float("KU_STRESS_SAMPLE_PCT", 1.0)
STRESS_PROPERTY_SNAPSHOT_ONLY = False
