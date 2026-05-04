-- 002_core.sql -- Core entities.

CREATE TABLE address (
  address_id               INTEGER PRIMARY KEY,
  street                   TEXT,
  house_number             TEXT,
  postal_code              TEXT,                     -- string, may carry typos / canton mismatch
  city                     TEXT,
  canton                   TEXT,
  country                  TEXT NOT NULL DEFAULT 'CH',
  bfs_gemeinde_nr          INTEGER,
  ms_region                TEXT,
  address_type             TEXT NOT NULL DEFAULT 'residential'
                              CHECK (address_type IN ('residential','billing','work','property')),
  valid_from               TEXT,
  valid_to                 TEXT
);

CREATE TABLE client (
  client_id                INTEGER PRIMARY KEY,
  external_ref             TEXT,
  salutation               TEXT,
  first_name               TEXT,
  middle_name              TEXT,
  last_name                TEXT,
  birth_name               TEXT,
  birth_date               TEXT,                     -- nominally ISO; some rows DD.MM.YYYY (data quality)
  nationality              TEXT,
  second_nationality       TEXT,
  residence_permit         TEXT,
  civil_status             TEXT,
  marital_property_regime  TEXT,
  language_correspondence  TEXT,
  ahv_number               TEXT,
  email                    TEXT,
  phone_mobile             TEXT,
  phone_landline           TEXT,
  iban                     TEXT,
  profession               TEXT,
  employer                 TEXT,
  noga_code                TEXT,
  employment_type          TEXT,
  employment_since         TEXT,
  education_level          TEXT,
  segment                  TEXT,
  kyc_level                TEXT,
  kyc_review_date          TEXT,
  pep_flag                 INTEGER NOT NULL DEFAULT 0,
  sanctions_flag           INTEGER NOT NULL DEFAULT 0,
  sanctions_check_date     TEXT,
  source_of_funds          TEXT,
  customer_since           TEXT,
  address_id               INTEGER REFERENCES address(address_id),
  relationship_manager     TEXT,
  created_at               TEXT,
  updated_at               TEXT,
  last_review_date         TEXT
);
CREATE INDEX ix_client_lastname  ON client(last_name);
CREATE INDEX ix_client_birthdate ON client(birth_date);

CREATE TABLE household (
  household_id             INTEGER PRIMARY KEY,
  household_type           TEXT,
  dependents_count         INTEGER,
  children_count           INTEGER,
  children_ages            TEXT,
  total_persons            INTEGER,
  notes                    TEXT
);

CREATE TABLE client_household (
  client_id                INTEGER NOT NULL REFERENCES client(client_id),
  household_id             INTEGER NOT NULL REFERENCES household(household_id),
  role                     TEXT NOT NULL CHECK (role IN ('primary_borrower','co_borrower','guarantor')),
  share_pct                REAL NOT NULL,
  PRIMARY KEY (client_id, household_id)
);
CREATE INDEX ix_ch_household ON client_household(household_id);

CREATE TABLE property (
  property_id              INTEGER PRIMARY KEY,
  object_type              TEXT NOT NULL,
  sub_type                 TEXT,
  address_id               INTEGER NOT NULL REFERENCES address(address_id),
  egid                     INTEGER,
  ewid                     INTEGER,
  construction_year        INTEGER,
  last_renovation_year     INTEGER,
  living_area_sqm          REAL,
  plot_area_sqm            REAL,
  rooms                    REAL,
  bathrooms                INTEGER,
  floors_total             INTEGER,
  floor_unit               INTEGER,
  heating_type             TEXT,
  heating_year             INTEGER,
  geak_class               TEXT,
  building_insurance_value REAL,
  annual_rental_income_chf REAL,
  commercial_use           TEXT,
  usage                    TEXT,
  micro_location_score     REAL,
  macro_location_score     REAL,
  flood_zone               TEXT,
  noise_ruk                TEXT,
  seismic_zone             TEXT,
  purchase_price           REAL,
  purchase_date            TEXT,
  status                   TEXT NOT NULL DEFAULT 'active',
  region_code              TEXT,
  created_at               TEXT
);
CREATE INDEX ix_property_addr   ON property(address_id);
CREATE INDEX ix_property_region ON property(region_code, object_type);
