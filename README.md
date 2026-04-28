# Kreditüberwachung mock dataset

Synthetic Swiss mortgage credit-monitoring dataset (default 100 000 clients) with end-to-end fields,
Fahrländer-style hedonic property valuation, event-based surveillance, an additive housing-price
stress-test overlay, and realistic human-error inconsistencies.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e .

# Base dataset (100k clients ~ 8–12 min)
.venv/bin/python scripts/generate.py

# Stress overlay (8 scenarios × 12 quarters)
.venv/bin/python scripts/run_stress.py --scenario all

# Smoke checks
.venv/bin/python scripts/verify.py

# Sample queries
sqlite3 output/kreditueberwachung.db < scripts/sample_queries.sql
sqlite3 output/kreditueberwachung.db < scripts/stress_queries.sql
```

Smaller run for development:
```bash
KU_N_CLIENTS=2000 .venv/bin/python scripts/generate.py
```

## Output

- `output/kreditueberwachung.db` — single SQLite file
- `output/csv/<table>.csv` — one CSV per table
- `output/data_quality_issues.md` — catalogue of intentional inconsistencies + counts
- `output/stats.md` — row counts and KPI snapshot
- `output/stress_test.md` — stress KPIs by scenario × period

## Schema

Reference: `canton`, `postal_code`, `noga`, `fpre_index_history`, `rate_history`.
Core: `address`, `client`, `household`, `client_household`, `property`.
Credit: `valuation`, `loan`, `tranche`, `income`, `affordability_assessment`, `risk_metrics`.
Surveillance: `event`, `loan_case`, `document`, `audit_log`.
Stress overlay: `stress_scenario`, `stress_index_overlay`, `stress_rate_overlay`,
`stress_macro_overlay`, `stress_property_value`, `stress_loan_metrics`,
`stress_event`, `stress_portfolio_kpi`.

Views: `v_current_valuation`, `v_loan_overview`, `v_open_events`, `v_watchlist`,
`v_portfolio_kpis`, `v_stress_summary`, `v_stress_loan_compare`.

## Knobs (env vars)

- `KU_N_CLIENTS` (default 100000)
- `KU_SEED` (default 42)
- `KU_STRESS_HORIZON_Q` (default 12)
- `KU_STRESS_SAMPLE_PCT` (default 1.0)

Loan financing ranges: house price 700 k–5.5 M, loan 300 k–4.5 M, LTV 30–110 % with bulk 60–80 %.

## Scenarios

- `baseline` — no shock
- `mild_correction_10` — −10 % linear
- `severe_correction_25` — −25 % frontloaded
- `gfc_2008_analogue` — −18 % u-shape, +50 bp, −3 % income
- `regional_zh_zg_ge` — −20 %, ZH/ZG/GE only
- `rates_plus_200bp` — flat +200 bp
- `combined_adverse` — −20 % + +200 bp + −5 % income
- `finma_adverse` — object-tilted −22 %, +180 bp, −4 % income

Add your own as `scenarios/<id>.yaml`; the runner picks them up automatically.
