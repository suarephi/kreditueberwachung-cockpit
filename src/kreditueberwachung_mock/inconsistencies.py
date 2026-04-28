"""Apply realistic, documented human-error inconsistencies to the generated data.

Each rule is gated by a rate in config.ERROR_RATES. Counts are written to
output/data_quality_issues.md after every run.
"""
from __future__ import annotations
import datetime as dt
import unicodedata
import numpy as np
import pandas as pd
from . import config, rng as rngmod


_LOG: dict[str, int] = {}


def _bump(rule: str, n: int) -> None:
    _LOG[rule] = _LOG.get(rule, 0) + int(n)


def _mask(rng: np.random.Generator, n: int, rate: float) -> np.ndarray:
    return rng.random(n) < rate


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def _name_umlaut(rng, s: str) -> str:
    repl = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"}
    if rng.random() < 0.5:
        for k, v in repl.items():
            s = s.replace(k, v)
    else:
        for k in repl:
            s = s.replace(k, k.replace("ä", "a").replace("ö", "o").replace("ü", "u")
                            .replace("Ä", "A").replace("Ö", "O").replace("Ü", "U"))
    return s


def _city_localization(rng, city: str, lang: str) -> str:
    aliases = {
        "Genève":         ["Geneva", "Genf", "Geneve"],
        "Zürich":         ["Zurich", "Zuerich"],
        "Neuchâtel":      ["Neuchatel", "Neuenburg"],
        "Biel/Bienne":    ["Biel", "Bienne"],
        "St. Gallen":     ["Sankt Gallen", "St.Gallen", "Saint-Gall"],
        "Lugano":         ["Lugano", "Lugano-TI"],
        "Lausanne":       ["Lausana"],
        "Basel":          ["Bâle", "Basilea"],
        "Bern":           ["Berne", "Berna"],
        "Sion":           ["Sitten"],
        "Fribourg":       ["Freiburg", "Friburgo"],
        "Carouge GE":     ["Carouge"],
        "Petit-Lancy":    ["Lancy"],
    }
    if city in aliases:
        opts = aliases[city]
        return opts[int(rng.integers(0, len(opts)))]
    return city


def _drop_diacritic(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _to_dotdate(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
        return d.strftime("%d.%m.%Y")
    except Exception:
        return iso


def _to_2digit_year(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
        return d.strftime("%d.%m.%y")
    except Exception:
        return iso


def _phone_variant(rng, phone: str) -> str:
    if not isinstance(phone, str) or not phone:
        return phone
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        return phone
    last10 = digits[-10:] if digits.startswith("41") else digits[-9:]
    formats = [
        f"+41 {last10[1:3]} {last10[3:6]} {last10[6:8]} {last10[8:10]}",
        f"0{last10[1:3]} {last10[3:6]} {last10[6:8]} {last10[8:10]}",
        f"0{last10[1:3]}{last10[3:6]}{last10[6:8]}{last10[8:10]}",
        f"+41(0){last10[1:3]} {last10[3:10]}",
    ]
    return formats[int(rng.integers(0, len(formats)))]


def _money_string(v: float) -> str:
    return f"{int(v):,}".replace(",", "'")


def _iban_typo(rng, iban: str) -> str:
    if not isinstance(iban, str) or len(iban) < 8:
        return iban
    pos = int(rng.integers(8, len(iban) - 1))
    digit = iban[pos]
    if digit.isdigit():
        new_digit = str((int(digit) + 1) % 10)
        return iban[:pos] + new_digit + iban[pos + 1 :]
    return iban


def _ahv_format_error(rng, ahv: str) -> str:
    if not isinstance(ahv, str) or "." not in ahv:
        return ahv
    return ahv.replace(".", "")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def apply_inconsistencies(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    rng = rngmod.child_rng("inconsistencies")
    clients = tables["client"]
    addresses = tables["address"]

    n_c = len(clients)

    # --- Names ---
    m = _mask(rng, n_c, config.ERROR_RATES["name_umlaut_variant"])
    if m.any():
        clients.loc[m, "last_name"] = clients.loc[m, "last_name"].apply(lambda s: _name_umlaut(rng, str(s)))
        _bump("name_umlaut_variant", m.sum())

    m = _mask(rng, n_c, config.ERROR_RATES["name_case_anomaly"])
    if m.any():
        flip = rng.random(m.sum()) < 0.5
        idx = clients.index[m]
        for k, i in enumerate(idx):
            v = str(clients.at[i, "last_name"])
            clients.at[i, "last_name"] = v.upper() if flip[k] else v.lower()
        _bump("name_case_anomaly", m.sum())

    m = _mask(rng, n_c, config.ERROR_RATES["name_double_space"])
    if m.any():
        clients.loc[m, "first_name"] = clients.loc[m, "first_name"].astype(str) + "  " + clients.loc[m, "last_name"].astype(str).str[:0]
        _bump("name_double_space", m.sum())

    m = _mask(rng, n_c, config.ERROR_RATES["name_hyphen_variant"])
    if m.any():
        clients.loc[m, "last_name"] = clients.loc[m, "last_name"].astype(str).apply(
            lambda s: s.replace("-", " ") if "-" in s else (s if rng.random() > 0.5 else s + "-Schmid")
        )
        _bump("name_hyphen_variant", m.sum())

    m = _mask(rng, n_c, config.ERROR_RATES["name_trailing_whitespace"])
    if m.any():
        clients.loc[m, "last_name"] = clients.loc[m, "last_name"].astype(str) + " "
        _bump("name_trailing_whitespace", m.sum())

    # --- Salutation variants ---
    m = _mask(rng, n_c, config.ERROR_RATES["salutation_variant"])
    if m.any():
        sal_map = {"Herr": "Hr.", "Frau": "Fr.", "Monsieur": "M.", "Madame": "Mme",
                   "Signor": "Sig.", "Signora": "Sig.ra", "Dr.": "Dott."}
        clients.loc[m, "salutation"] = clients.loc[m, "salutation"].map(sal_map).fillna(clients.loc[m, "salutation"])
        _bump("salutation_variant", m.sum())

    # --- Salutation gender mismatch (Herr↔Frau, etc.) ---
    m = _mask(rng, n_c, config.ERROR_RATES["salutation_gender_mismatch"])
    if m.any():
        gender_flip = {
            "Herr":     "Frau",     "Frau":     "Herr",
            "Monsieur": "Madame",   "Madame":   "Monsieur",
            "Signor":   "Signora",  "Signora":  "Signor",
        }
        clients.loc[m, "salutation"] = clients.loc[m, "salutation"].map(
            lambda s: gender_flip.get(s, s)
        )
        _bump("salutation_gender_mismatch", m.sum())

    # --- Date of birth: dot format / 2-digit year ---
    m = _mask(rng, n_c, config.ERROR_RATES["date_dotformat"])
    if m.any():
        clients.loc[m, "birth_date"] = clients.loc[m, "birth_date"].astype(str).apply(_to_dotdate)
        _bump("date_dotformat", m.sum())

    m = _mask(rng, n_c, config.ERROR_RATES["date_2digit_year"])
    if m.any():
        clients.loc[m, "birth_date"] = clients.loc[m, "birth_date"].astype(str).apply(_to_2digit_year)
        _bump("date_2digit_year", m.sum())

    # --- Phone variants ---
    m = _mask(rng, n_c, config.ERROR_RATES["phone_format_variant"])
    if m.any():
        clients.loc[m, "phone_mobile"] = clients.loc[m, "phone_mobile"].astype(str).apply(lambda s: _phone_variant(rng, s))
        _bump("phone_format_variant", m.sum())

    # --- Email mishaps ---
    m = _mask(rng, n_c, config.ERROR_RATES["email_whitespace"])
    if m.any():
        clients.loc[m, "email"] = " " + clients.loc[m, "email"].astype(str) + " "
        _bump("email_whitespace", m.sum())

    m = _mask(rng, n_c, config.ERROR_RATES["email_missing_tld"])
    if m.any():
        clients.loc[m, "email"] = clients.loc[m, "email"].astype(str).apply(
            lambda s: s.split(".")[0] + "@" + s.split("@")[1].split(".")[0] if "@" in s and "." in s.split("@")[1] else s
        )
        _bump("email_missing_tld", m.sum())

    m = _mask(rng, n_c, config.ERROR_RATES["email_double_at"])
    if m.any():
        clients.loc[m, "email"] = clients.loc[m, "email"].astype(str).str.replace("@", "@@", n=1, regex=False)
        _bump("email_double_at", m.sum())

    # --- City localization variants on residential addresses ---
    n_a = len(addresses)
    m = _mask(rng, n_a, config.ERROR_RATES["city_localization_variant"])
    if m.any():
        cm = clients.set_index("address_id")["language_correspondence"].to_dict()
        addresses.loc[m, "city"] = addresses.loc[m].apply(
            lambda r: _city_localization(rng, str(r["city"]), cm.get(r["address_id"], "de")), axis=1
        )
        _bump("city_localization_variant", m.sum())

    m = _mask(rng, n_a, config.ERROR_RATES["city_diacritic_drop"])
    if m.any():
        addresses.loc[m, "city"] = addresses.loc[m, "city"].astype(str).apply(_drop_diacritic)
        _bump("city_diacritic_drop", m.sum())

    # --- PLZ ↔ canton mismatch (intentional) ---
    m = _mask(rng, n_a, config.ERROR_RATES["plz_canton_mismatch"])
    if m.any():
        wrong = rng.choice(["ZH", "BE", "VD", "GE", "AG"], size=m.sum())
        addresses.loc[m, "canton"] = wrong
        _bump("plz_canton_mismatch", m.sum())

    # --- Canton stored as full name vs 2-letter ---
    m = _mask(rng, n_a, config.ERROR_RATES["canton_full_name"])
    if m.any():
        from .reference import canton_lookup
        cl = canton_lookup()
        addresses.loc[m, "canton"] = addresses.loc[m, "canton"].astype(str).map(
            lambda c: cl[c]["name_de"] if c in cl else c
        )
        _bump("canton_full_name", m.sum())

    # --- IBAN typos ---
    m = _mask(rng, n_c, config.ERROR_RATES["iban_typo"])
    if m.any():
        clients.loc[m, "iban"] = clients.loc[m, "iban"].astype(str).apply(lambda s: _iban_typo(rng, s))
        _bump("iban_typo", m.sum())

    # --- AHV format errors ---
    m = _mask(rng, n_c, config.ERROR_RATES["ahv_format_error"])
    if m.any():
        clients.loc[m, "ahv_number"] = clients.loc[m, "ahv_number"].astype(str).apply(lambda s: _ahv_format_error(rng, s))
        _bump("ahv_format_error", m.sum())

    # --- NULL surrogates in optional fields ---
    m = _mask(rng, n_c, config.ERROR_RATES["null_surrogate"])
    if m.any():
        opts = ["-", "N/A", "unbekannt", "tbd", ""]
        chosen = [opts[int(rng.integers(0, len(opts)))] for _ in range(m.sum())]
        clients.loc[m, "phone_landline"] = chosen
        _bump("null_surrogate", m.sum())

    # --- Money as formatted strings on income.gross_salary (just doc-only; we leave numbers numeric) ---
    if "income" in tables:
        income = tables["income"]
        m = _mask(rng, len(income), config.ERROR_RATES["money_string"])
        # Note: in our SQLite schema gross_salary is REAL — we keep the column numeric, but expose
        # a text-formatted variant in `documented_via` for visibility.
        if m.any():
            income.loc[m, "documented_via"] = income.loc[m, "gross_salary"].astype(float).apply(
                lambda v: f"Lohnausweis: {_money_string(v)}"
            )
            _bump("money_string", m.sum())

    # --- Encoding NFD on first names ---
    m = _mask(rng, n_c, config.ERROR_RATES["encoding_nfd"])
    if m.any():
        clients.loc[m, "first_name"] = clients.loc[m, "first_name"].astype(str).apply(
            lambda s: unicodedata.normalize("NFD", s)
        )
        _bump("encoding_nfd", m.sum())

    # --- Mixed-language record (Romand client with German salutation, etc.) ---
    m = _mask(rng, n_c, config.ERROR_RATES["mixed_language_record"])
    if m.any():
        swap = {"Herr": "Monsieur", "Frau": "Madame", "Monsieur": "Herr", "Madame": "Frau",
                "Signor": "Herr", "Signora": "Frau", "Hr.": "M.", "Fr.": "Mme"}
        clients.loc[m, "salutation"] = clients.loc[m, "salutation"].map(swap).fillna(clients.loc[m, "salutation"])
        _bump("mixed_language_record", m.sum())

    return tables


def write_catalog(out_path) -> None:
    """Dump the actual rule counts vs. configured rates."""
    lines = ["# Data quality issues — intentional inconsistencies\n",
             "Synthetic but representative of real Swiss bank data after years of hand-typed input.\n",
             "Counts below come from the latest generator run.\n",
             "| Rule | Configured rate | Rows affected |", "|---|---:|---:|"]
    for k, v in config.ERROR_RATES.items():
        n = _LOG.get(k, 0)
        lines.append(f"| `{k}` | {v:.3%} | {n:,} |")
    lines += [
        "",
        "## How to find them",
        "",
        "```sql",
        "-- Salutation that doesn't match the language of correspondence",
        "SELECT client_id, salutation, language_correspondence",
        "FROM client",
        "WHERE (language_correspondence='de' AND salutation IN ('Monsieur','Madame','Signor','Signora','M.','Mme'))",
        "   OR (language_correspondence='fr' AND salutation IN ('Herr','Frau','Hr.','Fr.'))",
        "LIMIT 20;",
        "",
        "-- PLZ vs canton mismatch (compare against postal_code reference)",
        "SELECT a.address_id, a.postal_code, a.city, a.canton, pc.canton_code",
        "FROM address a",
        "JOIN postal_code pc ON pc.postal_code = a.postal_code",
        "WHERE a.canton <> pc.canton_code AND length(a.canton)=2",
        "LIMIT 20;",
        "",
        "-- Date of birth in dot format (data quality)",
        "SELECT client_id, birth_date FROM client",
        "WHERE birth_date LIKE '%.%' LIMIT 20;",
        "",
        "-- Email anomalies",
        "SELECT client_id, email FROM client",
        "WHERE email LIKE '% %' OR email LIKE '%@@%'",
        "LIMIT 20;",
        "```",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def reset_log() -> None:
    _LOG.clear()
