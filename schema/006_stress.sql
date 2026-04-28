-- 006_stress.sql -- Stress-test overlay (additive layer over base tables).

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
  shock_pct                REAL NOT NULL,
  shocked_index_value      REAL NOT NULL,
  PRIMARY KEY (scenario_id, region_code, object_type, period)
);

CREATE TABLE stress_rate_overlay (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  period                   TEXT NOT NULL,
  rate_name                TEXT NOT NULL,
  shock_bp                 INTEGER NOT NULL,
  shocked_rate_pct         REAL NOT NULL,
  PRIMARY KEY (scenario_id, period, rate_name)
);

CREATE TABLE stress_macro_overlay (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  period                   TEXT NOT NULL,
  unemployment_pct         REAL,
  gdp_yoy_pct              REAL,
  income_shock_pct         REAL,
  PRIMARY KEY (scenario_id, period)
);

CREATE TABLE stress_property_value (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  property_id              INTEGER NOT NULL REFERENCES property(property_id),
  period                   TEXT NOT NULL,
  stressed_market_value    REAL NOT NULL,
  stressed_mlv             REAL NOT NULL,
  PRIMARY KEY (scenario_id, property_id, period)
);

CREATE TABLE stress_loan_metrics (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  loan_id                  INTEGER NOT NULL REFERENCES loan(loan_id),
  period                   TEXT NOT NULL,
  stressed_outstanding     REAL NOT NULL,
  stressed_ltv             REAL NOT NULL,
  stressed_dsti            REAL NOT NULL,
  stressed_pd_1y           REAL NOT NULL,
  stressed_lgd             REAL NOT NULL,
  stressed_ead             REAL NOT NULL,
  stressed_expected_loss   REAL NOT NULL,
  covenant_breach_flag     INTEGER NOT NULL,
  additional_collateral_required REAL NOT NULL,
  exposure_at_default_chf  REAL NOT NULL,
  PRIMARY KEY (scenario_id, loan_id, period)
);
CREATE INDEX ix_slm_loan ON stress_loan_metrics(loan_id, scenario_id);

CREATE TABLE stress_event (
  stress_event_id          INTEGER PRIMARY KEY,
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  loan_id                  INTEGER NOT NULL REFERENCES loan(loan_id),
  period                   TEXT NOT NULL,
  event_type               TEXT NOT NULL,
  severity                 TEXT,
  narrative                TEXT
);
CREATE INDEX ix_stress_event_sl ON stress_event(scenario_id, loan_id);

CREATE TABLE stress_portfolio_kpi (
  scenario_id              TEXT NOT NULL REFERENCES stress_scenario(scenario_id),
  period                   TEXT NOT NULL,
  total_exposure           REAL,
  weighted_avg_ltv         REAL,
  share_ltv_gt80           REAL,
  share_dsti_gt33          REAL,
  expected_loss_total      REAL,
  npl_share                REAL,
  capital_impact_chf       REAL,
  PRIMARY KEY (scenario_id, period)
);

CREATE VIEW v_stress_summary AS
  SELECT s.scenario_id, s.name, s.severity, k.period,
         k.total_exposure, k.expected_loss_total,
         k.share_ltv_gt80, k.share_dsti_gt33, k.npl_share
    FROM stress_scenario s
    JOIN stress_portfolio_kpi k ON k.scenario_id = s.scenario_id;

CREATE VIEW v_stress_loan_compare AS
  SELECT m.scenario_id, m.loan_id, m.period,
         l.ltv_pct                    AS base_ltv,
         m.stressed_ltv,
         l.dsti_pct                   AS base_dsti,
         m.stressed_dsti,
         IFNULL(rm.expected_loss, 0)  AS base_el,
         m.stressed_expected_loss,
         IFNULL(rm.covenant_breach_flag, 0) AS base_breach,
         m.covenant_breach_flag       AS stressed_breach
    FROM stress_loan_metrics m
    JOIN loan l ON l.loan_id = m.loan_id
    LEFT JOIN risk_metrics rm ON rm.loan_id = m.loan_id;
