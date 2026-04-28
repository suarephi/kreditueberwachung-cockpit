-- 001_reference.sql -- Reference data tables.

PRAGMA foreign_keys = ON;

CREATE TABLE canton (
  canton_code              TEXT PRIMARY KEY,
  bfs_nr                   INTEGER NOT NULL,
  name_de                  TEXT NOT NULL,
  name_fr                  TEXT NOT NULL,
  name_it                  TEXT NOT NULL,
  language_main            TEXT NOT NULL,
  language_share_de        REAL NOT NULL,
  language_share_fr        REAL NOT NULL,
  language_share_it        REAL NOT NULL,
  population_share         REAL NOT NULL,
  base_chf_per_sqm_efh     REAL NOT NULL,
  base_chf_per_sqm_etw     REAL NOT NULL,
  base_chf_per_sqm_mfh     REAL NOT NULL,
  location_score_macro     REAL NOT NULL
);

CREATE TABLE postal_code (
  postal_code              TEXT NOT NULL,
  city                     TEXT NOT NULL,
  canton_code              TEXT NOT NULL REFERENCES canton(canton_code),
  bfs_gemeinde_nr          INTEGER NOT NULL,
  gemeinde_name            TEXT NOT NULL,
  urbanity                 TEXT NOT NULL CHECK (urbanity IN ('urban','suburban','rural')),
  ms_region                TEXT NOT NULL,
  location_score_micro     REAL NOT NULL,
  PRIMARY KEY (postal_code, city)
);

CREATE TABLE noga (
  noga_code                TEXT PRIMARY KEY,
  industry_de              TEXT NOT NULL,
  industry_fr              TEXT NOT NULL,
  industry_it              TEXT NOT NULL,
  sector                   TEXT NOT NULL,
  risk_class               TEXT NOT NULL
);

CREATE TABLE fpre_index_history (
  region_code              TEXT NOT NULL,
  object_type              TEXT NOT NULL,
  period                   TEXT NOT NULL,            -- YYYY-Qn
  index_value              REAL NOT NULL,
  yoy_change               REAL,
  PRIMARY KEY (region_code, object_type, period)
);

CREATE TABLE rate_history (
  rate_date                TEXT NOT NULL,            -- ISO date
  rate_name                TEXT NOT NULL,            -- SARON_3M / SARON_COMP / FIX_5Y / FIX_10Y
  rate_pct                 REAL NOT NULL,
  PRIMARY KEY (rate_date, rate_name)
);
