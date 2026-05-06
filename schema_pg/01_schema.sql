-- Postgres schema (port of schema/001..006_*.sql).  Idempotent: drops then recreates.
-- Tables, indexes, views — no PRAGMA, no AUTOINCREMENT (we insert explicit ids).

-- ---------- DROP (reverse FK order) ----------
DROP VIEW  IF EXISTS v_stress_loan_compare       CASCADE;
DROP VIEW  IF EXISTS v_stress_summary            CASCADE;
DROP VIEW  IF EXISTS v_portfolio_kpis            CASCADE;
DROP VIEW  IF EXISTS v_watchlist                 CASCADE;
DROP VIEW  IF EXISTS v_open_events               CASCADE;
DROP VIEW  IF EXISTS v_loan_overview             CASCADE;
DROP VIEW  IF EXISTS v_current_valuation         CASCADE;

DROP TABLE IF EXISTS stress_portfolio_kpi        CASCADE;
DROP TABLE IF EXISTS stress_event                CASCADE;
DROP TABLE IF EXISTS stress_loan_metrics         CASCADE;
DROP TABLE IF EXISTS stress_property_value       CASCADE;
DROP TABLE IF EXISTS stress_macro_overlay        CASCADE;
DROP TABLE IF EXISTS stress_rate_overlay         CASCADE;
DROP TABLE IF EXISTS stress_index_overlay        CASCADE;
DROP TABLE IF EXISTS stress_scenario             CASCADE;

DROP TABLE IF EXISTS audit_log                   CASCADE;
DROP TABLE IF EXISTS document                    CASCADE;
DROP TABLE IF EXISTS loan_case                   CASCADE;
DROP TABLE IF EXISTS event                       CASCADE;

DROP TABLE IF EXISTS dunning_step                CASCADE;
DROP TABLE IF EXISTS account_tx                  CASCADE;
DROP TABLE IF EXISTS account                     CASCADE;
DROP TABLE IF EXISTS position                    CASCADE;
DROP TABLE IF EXISTS portfolio                   CASCADE;
DROP TABLE IF EXISTS risk_metrics                CASCADE;
DROP TABLE IF EXISTS affordability_assessment    CASCADE;
DROP TABLE IF EXISTS income                      CASCADE;
DROP TABLE IF EXISTS tranche                     CASCADE;
DROP TABLE IF EXISTS loan                        CASCADE;
DROP TABLE IF EXISTS valuation                   CASCADE;
DROP TABLE IF EXISTS property                    CASCADE;
DROP TABLE IF EXISTS client_household            CASCADE;
DROP TABLE IF EXISTS household                   CASCADE;
DROP TABLE IF EXISTS client                      CASCADE;
DROP TABLE IF EXISTS address                     CASCADE;

DROP TABLE IF EXISTS rate_history                CASCADE;
DROP TABLE IF EXISTS fpre_index_history          CASCADE;
DROP TABLE IF EXISTS noga                        CASCADE;
DROP TABLE IF EXISTS postal_code                 CASCADE;
DROP TABLE IF EXISTS canton                      CASCADE;

-- ---------- REFERENCE ----------
CREATE TABLE canton (
  canton_code              TEXT PRIMARY KEY,
  bfs_nr                   INTEGER NOT NULL,
  name_de                  TEXT NOT NULL,
  name_fr                  TEXT NOT NULL,
  name_it                  TEXT NOT NULL,
  language_main            TEXT NOT NULL,
  language_share_de        DOUBLE PRECISION NOT NULL,
  language_share_fr        DOUBLE PRECISION NOT NULL,
  language_share_it        DOUBLE PRECISION NOT NULL,
  population_share         DOUBLE PRECISION NOT NULL,
  base_chf_per_sqm_efh     DOUBLE PRECISION NOT NULL,
  base_chf_per_sqm_etw     DOUBLE PRECISION NOT NULL,
  base_chf_per_sqm_mfh     DOUBLE PRECISION NOT NULL,
  location_score_macro     DOUBLE PRECISION NOT NULL
);

CREATE TABLE postal_code (
  postal_code              TEXT NOT NULL,
  city                     TEXT NOT NULL,
  canton_code              TEXT NOT NULL REFERENCES canton(canton_code),
  bfs_gemeinde_nr          INTEGER NOT NULL,
  gemeinde_name            TEXT NOT NULL,
  urbanity                 TEXT NOT NULL CHECK (urbanity IN ('urban','suburban','rural')),
  ms_region                TEXT NOT NULL,
  location_score_micro     DOUBLE PRECISION NOT NULL,
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
  period                   TEXT NOT NULL,
  index_value              DOUBLE PRECISION NOT NULL,
  yoy_change               DOUBLE PRECISION,
  PRIMARY KEY (region_code, object_type, period)
);

CREATE TABLE rate_history (
  rate_date                TEXT NOT NULL,
  rate_name                TEXT NOT NULL,
  rate_pct                 DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (rate_date, rate_name)
);

-- ---------- CORE ----------
CREATE TABLE address (
  address_id               BIGINT PRIMARY KEY,
  street                   TEXT,
  house_number             TEXT,
  postal_code              TEXT,
  city                     TEXT,
  canton                   TEXT,
  country                  TEXT NOT NULL DEFAULT 'CH',
  bfs_gemeinde_nr          INTEGER,
  ms_region                TEXT,
  address_type             TEXT NOT NULL DEFAULT 'residential',
  valid_from               TEXT,
  valid_to                 TEXT
);

CREATE TABLE client (
  client_id                BIGINT PRIMARY KEY,
  external_ref             TEXT,
  salutation               TEXT,
  first_name               TEXT,
  middle_name              TEXT,
  last_name                TEXT,
  birth_name               TEXT,
  birth_date               TEXT,
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
  address_id               BIGINT REFERENCES address(address_id),
  relationship_manager     TEXT,
  created_at               TEXT,
  updated_at               TEXT,
  last_review_date         TEXT
);
CREATE INDEX ix_client_lastname  ON client(last_name);
CREATE INDEX ix_client_birthdate ON client(birth_date);

CREATE TABLE household (
  household_id             BIGINT PRIMARY KEY,
  household_type           TEXT,
  dependents_count         INTEGER,
  children_count           INTEGER,
  children_ages            TEXT,
  total_persons            INTEGER,
  notes                    TEXT
);

CREATE TABLE client_household (
  client_id                BIGINT NOT NULL REFERENCES client(client_id),
  household_id             BIGINT NOT NULL REFERENCES household(household_id),
  role                     TEXT NOT NULL CHECK (role IN ('primary_borrower','co_borrower','guarantor')),
  share_pct                DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (client_id, household_id)
);
CREATE INDEX ix_ch_household ON client_household(household_id);

CREATE TABLE property (
  property_id              BIGINT PRIMARY KEY,
  object_type              TEXT NOT NULL,
  sub_type                 TEXT,
  address_id               BIGINT NOT NULL REFERENCES address(address_id),
  egid                     BIGINT,
  ewid                     INTEGER,
  construction_year        INTEGER,
  last_renovation_year     INTEGER,
  living_area_sqm          DOUBLE PRECISION,
  plot_area_sqm            DOUBLE PRECISION,
  rooms                    DOUBLE PRECISION,
  bathrooms                INTEGER,
  floors_total             INTEGER,
  floor_unit               INTEGER,
  heating_type             TEXT,
  heating_year             INTEGER,
  geak_class               TEXT,
  building_insurance_value DOUBLE PRECISION,
  annual_rental_income_chf DOUBLE PRECISION,
  commercial_use           TEXT,
  usage                    TEXT,
  micro_location_score     DOUBLE PRECISION,
  macro_location_score     DOUBLE PRECISION,
  flood_zone               TEXT,
  noise_ruk                TEXT,
  seismic_zone             TEXT,
  purchase_price           DOUBLE PRECISION,
  purchase_date            TEXT,
  status                   TEXT NOT NULL DEFAULT 'active',
  region_code              TEXT,
  created_at               TEXT
);
CREATE INDEX ix_property_addr   ON property(address_id);
CREATE INDEX ix_property_region ON property(region_code, object_type);

-- ---------- CREDIT ----------
CREATE TABLE valuation (
  valuation_id             BIGINT PRIMARY KEY,
  property_id              BIGINT NOT NULL REFERENCES property(property_id),
  valuation_date           TEXT NOT NULL,
  valuation_method         TEXT NOT NULL,
  market_value             DOUBLE PRECISION NOT NULL,
  mortgage_lending_value   DOUBLE PRECISION NOT NULL,
  confidence_band_low      DOUBLE PRECISION,
  confidence_band_high     DOUBLE PRECISION,
  micro_score              DOUBLE PRECISION,
  macro_score              DOUBLE PRECISION,
  is_current               INTEGER NOT NULL DEFAULT 0,
  valuator_id              TEXT,
  valuator_name            TEXT,
  notes                    TEXT
);
CREATE INDEX ix_valuation_prop_cur ON valuation(property_id, is_current);

CREATE TABLE loan (
  loan_id                  BIGINT PRIMARY KEY,
  primary_client_id        BIGINT NOT NULL REFERENCES client(client_id),
  household_id             BIGINT NOT NULL REFERENCES household(household_id),
  property_id              BIGINT NOT NULL REFERENCES property(property_id),
  origination_date         TEXT NOT NULL,
  first_drawdown_date      TEXT,
  original_amount          DOUBLE PRECISION NOT NULL,
  current_outstanding      DOUBLE PRECISION NOT NULL,
  first_mortgage_amount    DOUBLE PRECISION NOT NULL,
  second_mortgage_amount   DOUBLE PRECISION NOT NULL DEFAULT 0,
  ltv_pct                  DOUBLE PRECISION NOT NULL,
  dsti_pct                 DOUBLE PRECISION NOT NULL,
  pillar2_pledge           DOUBLE PRECISION NOT NULL DEFAULT 0,
  pillar3a_pledge          DOUBLE PRECISION NOT NULL DEFAULT 0,
  pillar3a_indirect_amortization INTEGER NOT NULL DEFAULT 0,
  status                   TEXT NOT NULL DEFAULT 'active',
  product_line             TEXT,
  currency                 TEXT NOT NULL DEFAULT 'CHF',
  notes                    TEXT
);
CREATE INDEX ix_loan_client   ON loan(primary_client_id);
CREATE INDEX ix_loan_property ON loan(property_id);

CREATE TABLE tranche (
  tranche_id               BIGINT PRIMARY KEY,
  loan_id                  BIGINT NOT NULL REFERENCES loan(loan_id),
  tranche_type             TEXT NOT NULL CHECK (tranche_type IN ('fix','saron','variable')),
  amount                   DOUBLE PRECISION NOT NULL,
  interest_rate_pct        DOUBLE PRECISION NOT NULL,
  reference_rate           TEXT,
  margin_bp                INTEGER,
  rate_fixing_date         TEXT,
  rate_reset_date          TEXT,
  maturity_date            TEXT,
  amortization_type        TEXT NOT NULL DEFAULT 'indirect'
                              CHECK (amortization_type IN ('direct','indirect','none')),
  amortization_amount_yearly DOUBLE PRECISION NOT NULL DEFAULT 0,
  status                   TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX ix_tranche_loan ON tranche(loan_id);

CREATE TABLE income (
  income_id                BIGINT PRIMARY KEY,
  client_id                BIGINT NOT NULL REFERENCES client(client_id),
  reporting_year           INTEGER NOT NULL,
  gross_salary             DOUBLE PRECISION NOT NULL DEFAULT 0,
  bonus_avg_3y             DOUBLE PRECISION NOT NULL DEFAULT 0,
  variable_income          DOUBLE PRECISION NOT NULL DEFAULT 0,
  rental_income            DOUBLE PRECISION NOT NULL DEFAULT 0,
  dividend_income          DOUBLE PRECISION NOT NULL DEFAULT 0,
  pension_income           DOUBLE PRECISION NOT NULL DEFAULT 0,
  other_income             DOUBLE PRECISION NOT NULL DEFAULT 0,
  alimony_received         DOUBLE PRECISION NOT NULL DEFAULT 0,
  alimony_paid             DOUBLE PRECISION NOT NULL DEFAULT 0,
  existing_debt_payments   DOUBLE PRECISION NOT NULL DEFAULT 0,
  documented_via           TEXT,
  currency                 TEXT NOT NULL DEFAULT 'CHF',
  confidence               TEXT
);
CREATE INDEX ix_income_client ON income(client_id, reporting_year);

CREATE TABLE affordability_assessment (
  assessment_id            BIGINT PRIMARY KEY,
  loan_id                  BIGINT NOT NULL REFERENCES loan(loan_id),
  assessment_date          TEXT NOT NULL,
  imputed_interest_rate    DOUBLE PRECISION NOT NULL DEFAULT 5.0,
  maintenance_rate         DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  amortization_required    DOUBLE PRECISION NOT NULL DEFAULT 0,
  total_cost_yearly        DOUBLE PRECISION NOT NULL,
  household_income_used    DOUBLE PRECISION NOT NULL,
  income_basis             TEXT,
  dsti_calculated          DOUBLE PRECISION NOT NULL,
  dsti_threshold           DOUBLE PRECISION NOT NULL DEFAULT 33.0,
  pass_fail                TEXT NOT NULL CHECK (pass_fail IN ('pass','fail','exception')),
  exception_approval_id    TEXT
);
CREATE INDEX ix_aff_loan ON affordability_assessment(loan_id, assessment_date);

CREATE TABLE risk_metrics (
  metric_id                BIGINT PRIMARY KEY,
  loan_id                  BIGINT NOT NULL REFERENCES loan(loan_id),
  as_of_date               TEXT NOT NULL,
  pd_1y                    DOUBLE PRECISION NOT NULL,
  lgd                      DOUBLE PRECISION NOT NULL,
  ead                      DOUBLE PRECISION NOT NULL,
  expected_loss            DOUBLE PRECISION NOT NULL,
  rating_internal          INTEGER NOT NULL,
  watchlist_flag           INTEGER NOT NULL DEFAULT 0,
  npl_flag                 INTEGER NOT NULL DEFAULT 0,
  forbearance_flag         INTEGER NOT NULL DEFAULT 0,
  days_past_due            INTEGER NOT NULL DEFAULT 0,
  covenant_breach_flag     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_rm_loan ON risk_metrics(loan_id, as_of_date);

-- ---------- WERTSCHRIFTEN (Cross-Sell-Sicht) ----------
CREATE TABLE portfolio (
  portfolio_id            BIGINT PRIMARY KEY,
  client_id               BIGINT NOT NULL REFERENCES client(client_id),
  strategy                TEXT NOT NULL CHECK (strategy IN
                              ('konservativ','vorsichtig','mittel','wachstum','aktien')),
  benchmark               TEXT,
  inception_date          TEXT NOT NULL,
  total_value_chf         DOUBLE PRECISION NOT NULL,
  cash_chf                DOUBLE PRECISION NOT NULL,
  ytd_return_pct          DOUBLE PRECISION,
  one_year_return_pct     DOUBLE PRECISION,
  custodian               TEXT,
  fee_model               TEXT,
  last_review_date        TEXT
);
CREATE INDEX ix_portfolio_client   ON portfolio(client_id);
CREATE INDEX ix_portfolio_strategy ON portfolio(strategy);

CREATE TABLE position (
  position_id             BIGINT PRIMARY KEY,
  portfolio_id            BIGINT NOT NULL REFERENCES portfolio(portfolio_id),
  isin                    TEXT NOT NULL,
  name                    TEXT NOT NULL,
  asset_class             TEXT NOT NULL CHECK (asset_class IN
                              ('bond','equity','etf_bond','etf_equity','cash','alternative')),
  currency                TEXT NOT NULL,
  quantity                DOUBLE PRECISION NOT NULL,
  avg_cost_chf            DOUBLE PRECISION,
  market_price_chf        DOUBLE PRECISION NOT NULL,
  market_value_chf        DOUBLE PRECISION NOT NULL,
  unrealized_pnl_chf      DOUBLE PRECISION,
  weight_pct              DOUBLE PRECISION,
  last_price_date         TEXT
);
CREATE INDEX ix_position_portfolio ON position(portfolio_id);
CREATE INDEX ix_position_isin      ON position(isin);

-- ---------- KONTEN + TRANSAKTIONEN (Bewegungsanalyse) ----------
CREATE TABLE account (
  account_id          BIGINT PRIMARY KEY,
  client_id           BIGINT NOT NULL REFERENCES client(client_id),
  iban                TEXT NOT NULL,
  account_type        TEXT NOT NULL CHECK (account_type IN
                          ('salary','savings','mortgage_servicing','rental','joint')),
  currency            TEXT NOT NULL DEFAULT 'CHF',
  opened_date         TEXT NOT NULL,
  current_balance_chf DOUBLE PRECISION NOT NULL,
  avg_balance_12m_chf DOUBLE PRECISION,
  status              TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX ix_account_client ON account(client_id);

CREATE TABLE account_tx (
  tx_id               BIGINT PRIMARY KEY,
  account_id          BIGINT NOT NULL REFERENCES account(account_id),
  tx_date             TEXT NOT NULL,
  value_date          TEXT NOT NULL,
  amount_chf          DOUBLE PRECISION NOT NULL,
  category            TEXT NOT NULL,
  counterparty        TEXT,
  description         TEXT,
  reference           TEXT
);
CREATE INDEX ix_tx_account_date ON account_tx(account_id, tx_date);
CREATE INDEX ix_tx_category     ON account_tx(category);

-- ---------- MAHNWESEN (Swiss banking workflow) ----------
CREATE TABLE dunning_step (
  dunning_id              BIGINT PRIMARY KEY,
  loan_id                 BIGINT NOT NULL REFERENCES loan(loan_id),
  step                    INTEGER NOT NULL CHECK (step BETWEEN 1 AND 4),
  step_label              TEXT NOT NULL,
  issued_date             TEXT NOT NULL,
  due_date                TEXT NOT NULL,
  amount_overdue_chf      DOUBLE PRECISION NOT NULL,
  fee_chf                 DOUBLE PRECISION NOT NULL DEFAULT 0,
  status                  TEXT NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open','paid','escalated','closed')),
  resolved_date           TEXT,
  assigned_officer        TEXT,
  reference               TEXT
);
CREATE INDEX ix_dunning_loan ON dunning_step(loan_id, step);
CREATE INDEX ix_dunning_status ON dunning_step(status);

-- ---------- SURVEILLANCE ----------
CREATE TABLE event (
  event_id                 BIGINT PRIMARY KEY,
  loan_id                  BIGINT REFERENCES loan(loan_id),
  client_id                BIGINT REFERENCES client(client_id),
  property_id              BIGINT REFERENCES property(property_id),
  event_type               TEXT NOT NULL,
  event_subtype            TEXT,
  severity                 TEXT NOT NULL CHECK (severity IN ('info','low','medium','high','critical')),
  source                   TEXT NOT NULL,
  detected_at              TEXT NOT NULL,
  occurred_at              TEXT,
  title                    TEXT,
  description              TEXT,
  status                   TEXT NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open','in_progress','waived','closed_resolved','escalated')),
  assigned_to              TEXT,
  resolved_at              TEXT,
  sla_due_date             TEXT,
  sla_basis                TEXT,
  linked_case_id           BIGINT
);
CREATE INDEX ix_event_loan       ON event(loan_id);
CREATE INDEX ix_event_status_sev ON event(status, severity);
CREATE INDEX ix_event_type       ON event(event_type);
CREATE INDEX ix_event_detected   ON event(detected_at);
CREATE INDEX ix_event_sla        ON event(sla_due_date);

CREATE TABLE loan_case (
  case_id                  BIGINT PRIMARY KEY,
  case_type                TEXT NOT NULL,
  loan_id                  BIGINT REFERENCES loan(loan_id),
  client_id                BIGINT REFERENCES client(client_id),
  opened_at                TEXT NOT NULL,
  due_date                 TEXT,
  closed_at                TEXT,
  status                   TEXT NOT NULL DEFAULT 'open',
  priority                 TEXT NOT NULL DEFAULT 'normal',
  assigned_team            TEXT,
  assigned_officer         TEXT,
  decision                 TEXT,
  decision_at              TEXT,
  decided_by               TEXT,
  notes                    TEXT
);
CREATE INDEX ix_case_loan ON loan_case(loan_id);

CREATE TABLE document (
  document_id              BIGINT PRIMARY KEY,
  parent_type              TEXT NOT NULL CHECK (parent_type IN ('client','loan','property','case','event')),
  parent_id                BIGINT NOT NULL,
  doc_type                 TEXT NOT NULL,
  filename                 TEXT,
  upload_date              TEXT,
  expiry_date              TEXT,
  status                   TEXT NOT NULL CHECK (status IN ('valid','expired','missing','superseded')),
  hash                     TEXT
);
CREATE INDEX ix_doc_parent ON document(parent_type, parent_id);

CREATE TABLE audit_log (
  audit_id                 BIGINT PRIMARY KEY,
  entity_type              TEXT NOT NULL,
  entity_id                BIGINT NOT NULL,
  field_name               TEXT NOT NULL,
  old_value                TEXT,
  new_value                TEXT,
  changed_by               TEXT,
  changed_at               TEXT NOT NULL,
  source_system            TEXT
);
CREATE INDEX ix_audit_entity ON audit_log(entity_type, entity_id);

-- ---------- STRESS ----------
CREATE TABLE stress_scenario (
  scenario_id              TEXT PRIMARY KEY,
  name                     TEXT NOT NULL,
  description              TEXT,
  severity                 TEXT NOT NULL CHECK (severity IN ('baseline','mild','moderate','severe','extreme')),
  horizon_quarters         INTEGER NOT NULL,
  start_period             TEXT NOT NULL,
  narrative                TEXT,
  source                   TEXT,
  seed                     INTEGER NOT NULL,
  yaml_hash                TEXT,
  created_at               TEXT NOT NULL
);

CREATE TABLE stress_index_overlay (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  region_code              TEXT NOT NULL,
  object_type              TEXT NOT NULL,
  period                   TEXT NOT NULL,
  shock_pct                DOUBLE PRECISION NOT NULL,
  shocked_index_value      DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (scenario_id, region_code, object_type, period)
);

CREATE TABLE stress_rate_overlay (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  period                   TEXT NOT NULL,
  rate_name                TEXT NOT NULL,
  shock_bp                 INTEGER NOT NULL,
  shocked_rate_pct         DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (scenario_id, period, rate_name)
);

CREATE TABLE stress_macro_overlay (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  period                   TEXT NOT NULL,
  unemployment_pct         DOUBLE PRECISION,
  gdp_yoy_pct              DOUBLE PRECISION,
  income_shock_pct         DOUBLE PRECISION,
  PRIMARY KEY (scenario_id, period)
);

CREATE TABLE stress_property_value (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  property_id              BIGINT NOT NULL REFERENCES property(property_id),
  period                   TEXT NOT NULL,
  stressed_market_value    DOUBLE PRECISION NOT NULL,
  stressed_mlv             DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (scenario_id, property_id, period)
);

CREATE TABLE stress_loan_metrics (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  loan_id                  BIGINT NOT NULL REFERENCES loan(loan_id),
  period                   TEXT NOT NULL,
  stressed_outstanding     DOUBLE PRECISION NOT NULL,
  stressed_ltv             DOUBLE PRECISION NOT NULL,
  stressed_dsti            DOUBLE PRECISION NOT NULL,
  stressed_pd_1y           DOUBLE PRECISION NOT NULL,
  stressed_lgd             DOUBLE PRECISION NOT NULL,
  stressed_ead             DOUBLE PRECISION NOT NULL,
  stressed_expected_loss   DOUBLE PRECISION NOT NULL,
  covenant_breach_flag     INTEGER NOT NULL,
  additional_collateral_required DOUBLE PRECISION NOT NULL,
  exposure_at_default_chf  DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (scenario_id, loan_id, period)
);
CREATE INDEX ix_slm_loan ON stress_loan_metrics(loan_id, scenario_id);

CREATE TABLE stress_event (
  stress_event_id          BIGINT PRIMARY KEY,
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  loan_id                  BIGINT NOT NULL REFERENCES loan(loan_id),
  period                   TEXT NOT NULL,
  event_type               TEXT NOT NULL,
  severity                 TEXT,
  narrative                TEXT
);
CREATE INDEX ix_stress_event_sl ON stress_event(scenario_id, loan_id);

CREATE TABLE stress_portfolio_kpi (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  period                   TEXT NOT NULL,
  total_exposure           DOUBLE PRECISION,
  weighted_avg_ltv         DOUBLE PRECISION,
  share_ltv_gt80           DOUBLE PRECISION,
  share_dsti_gt33          DOUBLE PRECISION,
  expected_loss_total      DOUBLE PRECISION,
  npl_share                DOUBLE PRECISION,
  capital_impact_chf       DOUBLE PRECISION,
  PRIMARY KEY (scenario_id, period)
);

-- ---------- VIEWS ----------
CREATE VIEW v_current_valuation AS
  SELECT * FROM valuation WHERE is_current = 1;

CREATE VIEW v_loan_overview AS
  SELECT l.loan_id,
         c.client_id,
         c.first_name || ' ' || c.last_name AS client_name,
         a.canton, a.city,
         p.object_type, p.living_area_sqm,
         vc.market_value, vc.mortgage_lending_value,
         l.current_outstanding, l.ltv_pct, l.dsti_pct,
         l.status            AS loan_status,
         rm.rating_internal, rm.watchlist_flag, rm.npl_flag, rm.expected_loss
    FROM loan l
    JOIN client   c  ON c.client_id    = l.primary_client_id
    JOIN property p  ON p.property_id  = l.property_id
    JOIN address  a  ON a.address_id   = p.address_id
    LEFT JOIN v_current_valuation vc ON vc.property_id = p.property_id
    LEFT JOIN risk_metrics rm        ON rm.loan_id     = l.loan_id;

CREATE VIEW v_open_events AS
  SELECT e.event_id, e.event_type, e.severity, e.status, e.detected_at,
         e.sla_due_date, e.assigned_to, e.title,
         e.loan_id, e.client_id, e.property_id
    FROM event e
   WHERE e.status IN ('open','in_progress','escalated');

CREATE VIEW v_watchlist AS
  SELECT l.loan_id, c.last_name, c.first_name, l.ltv_pct, l.dsti_pct,
         rm.expected_loss, rm.rating_internal, rm.npl_flag, rm.forbearance_flag
    FROM loan l
    JOIN client c   ON c.client_id = l.primary_client_id
    JOIN risk_metrics rm ON rm.loan_id = l.loan_id
   WHERE rm.watchlist_flag = 1 OR rm.npl_flag = 1;

CREATE VIEW v_portfolio_kpis AS
  SELECT COUNT(*)                                                   AS n_loans,
         ROUND((SUM(current_outstanding)/1e6)::numeric, 1)          AS total_outstanding_mchf,
         ROUND(AVG(ltv_pct)::numeric, 2)                            AS avg_ltv,
         ROUND(AVG(dsti_pct)::numeric, 2)                           AS avg_dsti,
         SUM(CASE WHEN ltv_pct > 80 THEN 1 ELSE 0 END)*1.0/COUNT(*) AS share_ltv_gt80,
         SUM(CASE WHEN dsti_pct > 33 THEN 1 ELSE 0 END)*1.0/COUNT(*) AS share_dsti_gt33
    FROM loan;

CREATE VIEW v_stress_summary AS
  SELECT s.scenario_id, s.name, s.severity, k.period,
         k.total_exposure, k.expected_loss_total,
         k.share_ltv_gt80, k.share_dsti_gt33, k.npl_share
    FROM stress_scenario s
    JOIN stress_portfolio_kpi k ON k.scenario_id = s.scenario_id;

CREATE VIEW v_stress_loan_compare AS
  SELECT m.scenario_id, m.loan_id, m.period,
         l.ltv_pct                                AS base_ltv,
         m.stressed_ltv,
         l.dsti_pct                               AS base_dsti,
         m.stressed_dsti,
         COALESCE(rm.expected_loss, 0)            AS base_el,
         m.stressed_expected_loss,
         COALESCE(rm.covenant_breach_flag, 0)     AS base_breach,
         m.covenant_breach_flag                   AS stressed_breach
    FROM stress_loan_metrics m
    JOIN loan l ON l.loan_id = m.loan_id
    LEFT JOIN risk_metrics rm ON rm.loan_id = m.loan_id;
