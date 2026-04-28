"""Client and household generation."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from stdnum.iban import format as iban_format
from stdnum.ch import vat as ch_vat                 # noqa: F401  (kept for stdnum availability)
from . import config, reference, geography, rng as rngmod


# ---------------------------------------------------------------------------
# AHV / IBAN helpers
# ---------------------------------------------------------------------------
def random_ahv(rng: np.random.Generator) -> str:
    """756.dddd.dddd.cc with EAN-13 check digit."""
    digits = [7, 5, 6] + [int(rng.integers(0, 10)) for _ in range(9)]
    s = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    check = (10 - (s % 10)) % 10
    full = digits + [check]
    return f"{full[0]}{full[1]}{full[2]}.{''.join(map(str, full[3:7]))}.{''.join(map(str, full[7:11]))}.{full[11]}{full[12]}"


def _iban_check(country_bban: str) -> str:
    rearr = country_bban[4:] + country_bban[:4]
    n = "".join(str(int(c, 36)) if c.isalpha() else c for c in rearr)
    return f"{98 - (int(n) % 97):02d}"


def random_iban_ch(rng: np.random.Generator) -> str:
    bank = f"{int(rng.integers(0, 100000)):05d}"
    acc  = f"{int(rng.integers(0, 10**12)):012d}"
    bban = bank + acc
    base = "CH00" + bban
    chk  = _iban_check(base)
    raw  = f"CH{chk}{bban}"
    try:
        return iban_format(raw)
    except Exception:                                          # pragma: no cover
        return raw


# ---------------------------------------------------------------------------
# Vectorised distributions
# ---------------------------------------------------------------------------
GENDERED_SALUTATIONS = {
    ("de", "M"): "Herr",     ("de", "F"): "Frau",
    ("fr", "M"): "Monsieur", ("fr", "F"): "Madame",
    ("it", "M"): "Signor",   ("it", "F"): "Signora",
}
DR_RATE = 0.03  # share of records where salutation is "Dr." instead of gendered form

CIVIL_STATUS    = ["single", "married", "divorced", "widowed", "registered_partnership", "separated"]
CIVIL_W         = [0.32, 0.51, 0.10, 0.04, 0.02, 0.01]
PROPERTY_REGIME = ["Errungenschaftsbeteiligung", "Gütergemeinschaft", "Gütertrennung", "n/a"]
PROPERTY_W      = [0.78, 0.05, 0.12, 0.05]
EDUCATION       = ["obligatorische_Schule", "Berufslehre", "Maturität", "Fachhochschule", "Universität", "Doktorat"]
EDU_W           = [0.05, 0.40, 0.10, 0.18, 0.22, 0.05]
EMPLOYMENT      = ["unbefristet", "befristet", "selbständig", "Pension", "Beamtenstatus"]
EMPLOY_W        = [0.78, 0.06, 0.07, 0.06, 0.03]
SEGMENT         = ["retail", "affluent", "private_banking", "business"]
SEGMENT_W       = [0.70, 0.20, 0.07, 0.03]
KYC_LEVEL       = ["standard", "enhanced"]
KYC_W           = [0.92, 0.08]
NATIONALITIES   = ["CH", "DE", "IT", "FR", "PT", "ES", "AT", "TR", "RS", "Other"]
NAT_W           = [0.74, 0.06, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01, 0.01, 0.02]
PERMIT_BY_NAT = {
    "CH": ("CH", 1.0),
    "Other": ("C", 0.55),
}


def generate_clients_and_addresses(n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate `n` clients with residential addresses; return (clients_df, addresses_df).

    Clients get sequential IDs 1..n; addresses 1..n (one per client; co-borrowers can share an
    address but we keep one per client for simplicity).
    """
    rng = rngmod.child_rng("clients")
    fakers = rngmod.fakers()
    plz_rows = geography.sample_postal_codes(rng, n).reset_index(drop=True)

    # Birth dates: age skewed toward 35–65.
    today = dt.date.today()
    age_mean, age_std = 48.0, 12.0
    ages = np.clip(rng.normal(age_mean, age_std, size=n), 25, 80).astype(int)
    birth_year = today.year - ages
    birth_month = rng.integers(1, 13, size=n)
    birth_day = rng.integers(1, 28, size=n)

    languages = np.array([
        rngmod.weighted_choice(rng,
            ["de", "fr", "it"],
            [reference.canton_lookup()[c]["language_share_de"],
             reference.canton_lookup()[c]["language_share_fr"],
             reference.canton_lookup()[c]["language_share_it"]])
        for c in plz_rows["canton_code"]
    ])

    # Pick a coarse gender per client, then derive name + matching salutation.
    # Salutation defaults to gender-correct; salutation_gender_mismatch
    # inconsistency injects a small share of swaps later.
    genders = rng.choice(["M", "F"], size=n).tolist()

    salutations: list[str] = []
    first_names, middle_names, last_names = [], [], []
    for lang, g in zip(languages, genders):
        f = fakers[lang]
        # First name from gendered Faker pool. Falls back to f.first_name()
        # if the locale doesn't expose a gendered helper.
        try:
            fn = f.first_name_male() if g == "M" else f.first_name_female()
        except Exception:
            fn = f.first_name()
        first_names.append(fn)
        if rng.random() < 0.07:
            try:
                mn = f.first_name_male() if g == "M" else f.first_name_female()
            except Exception:
                mn = f.first_name()
            middle_names.append(mn)
        else:
            middle_names.append(None)
        last_names.append(f.last_name())

        if rng.random() < DR_RATE:
            salutations.append("Dr.")
        else:
            salutations.append(GENDERED_SALUTATIONS[(lang, g)])

    civil   = rngmod.weighted_array(rng, CIVIL_STATUS, CIVIL_W, n)
    regimes = [
        rngmod.weighted_choice(rng, PROPERTY_REGIME, PROPERTY_W) if cs == "married" else "n/a"
        for cs in civil
    ]
    edu        = rngmod.weighted_array(rng, EDUCATION, EDU_W, n)
    employment = rngmod.weighted_array(rng, EMPLOYMENT, EMPLOY_W, n)
    segments   = rngmod.weighted_array(rng, SEGMENT, SEGMENT_W, n)
    kyc        = rngmod.weighted_array(rng, KYC_LEVEL, KYC_W, n)
    nationalities = rngmod.weighted_array(rng, NATIONALITIES, NAT_W, n)
    permits = []
    for nat in nationalities:
        if nat == "CH":
            permits.append("CH")
        else:
            r = rng.random()
            permits.append("C" if r < 0.55 else "B" if r < 0.85 else "L")

    pep = (rng.random(n) < 0.005).astype(int)
    sanc = (rng.random(n) < 0.0005).astype(int)

    noga_df = reference.noga()
    noga_codes = noga_df["noga_code"].sample(n=n, replace=True, random_state=int(rng.integers(0, 2**31))).values
    professions_by_lang = {
        "de": ["Ingenieur", "Lehrer", "Treuhänder", "Pflegefachperson", "Verkäufer",
               "Polizist", "IT-Specialist", "Architekt", "Bankangestellter", "Unternehmer",
               "Buchhalter", "Schreiner", "Elektriker", "Mediziner", "Wissenschaftler"],
        "fr": ["Ingénieur", "Enseignant", "Comptable", "Infirmier", "Vendeur",
               "Policier", "Spécialiste IT", "Architecte", "Banquier", "Entrepreneur",
               "Médecin", "Avocat", "Chercheur", "Designer", "Consultant"],
        "it": ["Ingegnere", "Insegnante", "Commercialista", "Infermiere", "Venditore",
               "Poliziotto", "Informatico", "Architetto", "Bancario", "Imprenditore",
               "Medico", "Avvocato", "Ricercatore", "Designer", "Consulente"],
    }
    professions = [professions_by_lang[lang][int(rng.integers(0, len(professions_by_lang[lang])))]
                   for lang in languages]
    employers = [fakers[lang].company() for lang in languages]

    customer_since = [
        (today - dt.timedelta(days=int(rng.integers(180, 365 * 25)))).isoformat()
        for _ in range(n)
    ]
    last_review = [
        (today - dt.timedelta(days=int(rng.integers(0, 365)))).isoformat()
        for _ in range(n)
    ]
    kyc_review = [
        (today + dt.timedelta(days=int(rng.integers(-180, 540)))).isoformat()
        for _ in range(n)
    ]
    sanctions_check = [
        (today - dt.timedelta(days=int(rng.integers(0, 365)))).isoformat()
        for _ in range(n)
    ]
    employment_since = [
        (today - dt.timedelta(days=int(rng.integers(180, 365 * 30)))).isoformat()
        for _ in range(n)
    ]

    rms = ["RM-" + str(i) for i in range(1, 81)]
    relationship_manager = [rms[int(rng.integers(0, len(rms)))] for _ in range(n)]

    emails = [
        f"{first_names[i].lower()}.{last_names[i].lower()}@{fakers['de'].free_email_domain()}"
        .replace(" ", "")
        for i in range(n)
    ]
    phones_mobile = [
        f"+41 {int(rng.integers(75, 80))} {int(rng.integers(100,1000))} {int(rng.integers(10,100))} {int(rng.integers(10,100))}"
        for _ in range(n)
    ]
    phones_landline = [
        f"+41 {int(rng.integers(21, 92))} {int(rng.integers(100,1000))} {int(rng.integers(10,100))} {int(rng.integers(10,100))}"
        if rng.random() < 0.6 else None
        for _ in range(n)
    ]
    ahvs  = [random_ahv(rng) for _ in range(n)]
    ibans = [random_iban_ch(rng) for _ in range(n)]

    addresses = pd.DataFrame({
        "address_id":     np.arange(1, n + 1),
        "street":         [geography.random_street(rng, lang) for lang in languages],
        "house_number":   [str(int(rng.integers(1, 200))) +
                           (chr(ord("a") + int(rng.integers(0, 4))) if rng.random() < 0.1 else "")
                           for _ in range(n)],
        "postal_code":    plz_rows["postal_code"].astype(str).values,
        "city":           plz_rows["city"].values,
        "canton":         plz_rows["canton_code"].values,
        "country":        "CH",
        "bfs_gemeinde_nr": plz_rows["bfs_gemeinde_nr"].values,
        "ms_region":      plz_rows["ms_region"].values,
        "address_type":   "residential",
        "valid_from":     [(today - dt.timedelta(days=int(rng.integers(60, 365*15)))).isoformat() for _ in range(n)],
        "valid_to":       None,
    })

    # Source of funds default by segment.
    sof_choices = ["Erwerbseinkommen", "Vermögen_Erbschaft", "Geschäftserlös",
                   "Pensionierung_Vorbezug", "Familie", "Verkauf_Immobilie"]
    sof_weights = [0.62, 0.13, 0.10, 0.06, 0.06, 0.03]
    source_of_funds = rngmod.weighted_array(rng, sof_choices, sof_weights, n)

    clients = pd.DataFrame({
        "client_id":              np.arange(1, n + 1),
        "external_ref":           [f"CRM-{int(rng.integers(10**6, 10**7-1))}" for _ in range(n)],
        "salutation":             salutations,
        "first_name":             first_names,
        "middle_name":            middle_names,
        "last_name":              last_names,
        "birth_name":             [last_names[i] if rng.random() > 0.06 else fakers[languages[i]].last_name()
                                   for i in range(n)],
        "birth_date":             [f"{birth_year[i]:04d}-{birth_month[i]:02d}-{birth_day[i]:02d}"
                                   for i in range(n)],
        "nationality":            nationalities,
        "second_nationality":     [None if rng.random() < 0.92 else
                                   rngmod.weighted_choice(rng, NATIONALITIES, NAT_W)
                                   for _ in range(n)],
        "residence_permit":       permits,
        "civil_status":           civil,
        "marital_property_regime": regimes,
        "language_correspondence": languages.tolist(),
        "ahv_number":             ahvs,
        "email":                  emails,
        "phone_mobile":           phones_mobile,
        "phone_landline":         phones_landline,
        "iban":                   ibans,
        "profession":             professions,
        "employer":               employers,
        "noga_code":              noga_codes,
        "employment_type":        employment,
        "employment_since":       employment_since,
        "education_level":        edu,
        "segment":                segments,
        "kyc_level":              kyc,
        "kyc_review_date":        kyc_review,
        "pep_flag":               pep,
        "sanctions_flag":         sanc,
        "sanctions_check_date":   sanctions_check,
        "source_of_funds":        source_of_funds,
        "customer_since":         customer_since,
        "address_id":             np.arange(1, n + 1),
        "relationship_manager":   relationship_manager,
        "created_at":             [today.isoformat()] * n,
        "updated_at":             [today.isoformat()] * n,
        "last_review_date":       last_review,
    })
    return clients, addresses


# ---------------------------------------------------------------------------
# Households
# ---------------------------------------------------------------------------
def generate_households(clients: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build households: ~70 % single-borrower, ~30 % joint with a synthetic co-borrower already in the
    `clients` table (we re-use existing clients as co-borrowers via random pairing)."""
    rng = rngmod.child_rng("households")
    n = len(clients)

    # Decide which client is primary borrower (everyone is) and who has a co-borrower.
    has_co_b = rng.random(n) < config.SHARE_JOINT_BORROWER
    co_indices = np.where(has_co_b)[0]
    # Pair co-borrower clients: pick another client at random.
    co_partner = rng.choice(np.arange(n), size=co_indices.size, replace=True)

    children_count = np.maximum(0, np.round(rng.normal(0.9, 1.0, size=n)).astype(int))
    children_count[~has_co_b] = np.maximum(0, np.round(rng.normal(0.3, 0.8, size=(~has_co_b).sum())).astype(int))
    dependents = children_count + (rng.random(n) < 0.04).astype(int)
    total_persons = 1 + has_co_b.astype(int) + children_count

    children_ages_str = []
    for cnt in children_count:
        if cnt <= 0:
            children_ages_str.append(None)
        else:
            ages = sorted([int(rng.integers(0, 25)) for _ in range(cnt)])
            children_ages_str.append(",".join(map(str, ages)))

    households = pd.DataFrame({
        "household_id":      np.arange(1, n + 1),
        "household_type":    np.where(has_co_b,
                                np.where(children_count > 0, "family", "couple"),
                                np.where(children_count > 0, "single_parent", "single")),
        "dependents_count":  dependents,
        "children_count":    children_count,
        "children_ages":     children_ages_str,
        "total_persons":     total_persons,
        "notes":             None,
    })

    rows = []
    for hh_id in range(1, n + 1):
        rows.append({
            "client_id":    int(clients.iloc[hh_id - 1]["client_id"]),
            "household_id": hh_id,
            "role":         "primary_borrower",
            "share_pct":    100.0 if not has_co_b[hh_id - 1] else 60.0,
        })
    for k, idx in enumerate(co_indices):
        partner = co_partner[k]
        if partner == idx:
            partner = (partner + 1) % n
        rows.append({
            "client_id":    int(clients.iloc[partner]["client_id"]),
            "household_id": int(idx + 1),
            "role":         "co_borrower",
            "share_pct":    40.0,
        })
    client_household = pd.DataFrame(rows)

    return households, client_household
