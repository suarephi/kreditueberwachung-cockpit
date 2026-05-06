-- 003_credit.sql -- Credit, valuation, risk.

CREATE TABLE valuation (
  valuation_id             INTEGER PRIMARY KEY,
  property_id              INTEGER NOT NULL REFERENCES property(property_id),
  valuation_date           TEXT NOT NULL,
  valuation_method         TEXT NOT NULL,            -- FPRE_AVM / internal_AVM / expert / comparison
  market_value             REAL NOT NULL,
  mortgage_lending_value   REAL NOT NULL,
  confidence_band_low      REAL,
  confidence_band_high     REAL,
  micro_score              REAL,
  macro_score              REAL,
  is_current               INTEGER NOT NULL DEFAULT 0,
  valuator_id              TEXT,
  valuator_name            TEXT,
  notes                    TEXT
);
CREATE INDEX ix_valuation_prop_cur ON valuation(property_id, is_current);

CREATE TABLE loan (
  loan_id                  INTEGER PRIMARY KEY,
  primary_client_id        INTEGER NOT NULL REFERENCES client(client_id),
  household_id             INTEGER NOT NULL REFERENCES household(household_id),
  property_id              INTEGER NOT NULL REFERENCES property(property_id),
  origination_date         TEXT NOT NULL,
  first_drawdown_date      TEXT,
  original_amount          REAL NOT NULL,
  current_outstanding      REAL NOT NULL,
  first_mortgage_amount    REAL NOT NULL,
  second_mortgage_amount   REAL NOT NULL DEFAULT 0,
  ltv_pct                  REAL NOT NULL,
  dsti_pct                 REAL NOT NULL,
  pillar2_pledge           REAL NOT NULL DEFAULT 0,
  pillar3a_pledge          REAL NOT NULL DEFAULT 0,
  pillar3a_indirect_amortization INTEGER NOT NULL DEFAULT 0,
  status                   TEXT NOT NULL DEFAULT 'active',
  product_line             TEXT,
  currency                 TEXT NOT NULL DEFAULT 'CHF',
  notes                    TEXT
);
CREATE INDEX ix_loan_client   ON loan(primary_client_id);
CREATE INDEX ix_loan_property ON loan(property_id);

CREATE TABLE tranche (
  tranche_id               INTEGER PRIMARY KEY,
  loan_id                  INTEGER NOT NULL REFERENCES loan(loan_id),
  tranche_type             TEXT NOT NULL CHECK (tranche_type IN ('fix','saron','variable')),
  amount                   REAL NOT NULL,
  interest_rate_pct        REAL NOT NULL,
  reference_rate           TEXT,
  margin_bp                INTEGER,
  rate_fixing_date         TEXT,
  rate_reset_date          TEXT,
  maturity_date            TEXT,
  amortization_type        TEXT NOT NULL DEFAULT 'indirect'
                              CHECK (amortization_type IN ('direct','indirect','none')),
  amortization_amount_yearly REAL NOT NULL DEFAULT 0,
  status                   TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX ix_tranche_loan ON tranche(loan_id);

CREATE TABLE income (
  income_id                INTEGER PRIMARY KEY,
  client_id                INTEGER NOT NULL REFERENCES client(client_id),
  reporting_year           INTEGER NOT NULL,
  gross_salary             REAL NOT NULL DEFAULT 0,
  bonus_avg_3y             REAL NOT NULL DEFAULT 0,
  variable_income          REAL NOT NULL DEFAULT 0,
  rental_income            REAL NOT NULL DEFAULT 0,
  dividend_income          REAL NOT NULL DEFAULT 0,
  pension_income           REAL NOT NULL DEFAULT 0,
  other_income             REAL NOT NULL DEFAULT 0,
  alimony_received         REAL NOT NULL DEFAULT 0,
  alimony_paid             REAL NOT NULL DEFAULT 0,
  existing_debt_payments   REAL NOT NULL DEFAULT 0,
  documented_via           TEXT,
  currency                 TEXT NOT NULL DEFAULT 'CHF',
  confidence               TEXT
);
CREATE INDEX ix_income_client ON income(client_id, reporting_year);

CREATE TABLE affordability_assessment (
  assessment_id            INTEGER PRIMARY KEY,
  loan_id                  INTEGER NOT NULL REFERENCES loan(loan_id),
  assessment_date          TEXT NOT NULL,
  imputed_interest_rate    REAL NOT NULL DEFAULT 5.0,
  maintenance_rate         REAL NOT NULL DEFAULT 1.0,
  amortization_required    REAL NOT NULL DEFAULT 0,
  total_cost_yearly        REAL NOT NULL,
  household_income_used    REAL NOT NULL,
  income_basis             TEXT,
  dsti_calculated          REAL NOT NULL,
  dsti_threshold           REAL NOT NULL DEFAULT 33.0,
  pass_fail                TEXT NOT NULL CHECK (pass_fail IN ('pass','fail','exception')),
  exception_approval_id    TEXT
);
CREATE INDEX ix_aff_loan ON affordability_assessment(loan_id, assessment_date);

CREATE TABLE risk_metrics (
  metric_id                INTEGER PRIMARY KEY,
  loan_id                  INTEGER NOT NULL REFERENCES loan(loan_id),
  as_of_date               TEXT NOT NULL,
  pd_1y                    REAL NOT NULL,
  lgd                      REAL NOT NULL,
  ead                      REAL NOT NULL,
  expected_loss            REAL NOT NULL,
  rating_internal          INTEGER NOT NULL,
  watchlist_flag           INTEGER NOT NULL DEFAULT 0,
  npl_flag                 INTEGER NOT NULL DEFAULT 0,
  forbearance_flag         INTEGER NOT NULL DEFAULT 0,
  days_past_due            INTEGER NOT NULL DEFAULT 0,
  covenant_breach_flag     INTEGER NOT NULL DEFAULT 0,
  ifrs9_stage              INTEGER,
  ifrs9_sicr_reason        TEXT,
  lifetime_el              REAL
);
CREATE INDEX ix_rm_loan ON risk_metrics(loan_id, as_of_date);
