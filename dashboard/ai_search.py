"""AI search · natural-language → SQL via Claude.

System prompt embeds the full schema so the model can write correct joins
straight out of the gate. Output is constrained to a single SELECT and
validated client-side before execution.
"""
from __future__ import annotations
import re

SYSTEM_PROMPT = """You generate read-only SQL queries against the Kreditüberwachung
mock dataset (Swiss mortgage credit-monitoring). Output ONLY a single SQL
statement. No prose, no markdown, no semicolons at the end. Use ANSI SQL that
runs on both SQLite and PostgreSQL (no PRAGMA, no INFORMATION_SCHEMA,
no double-quoted string literals — use single quotes).

Rules:
- Always START with SELECT. Never INSERT/UPDATE/DELETE/DROP/ALTER/CREATE.
- Cap results with LIMIT (max 200) unless the user asks for an aggregate.
- For German user input, return data with English-friendly column aliases when helpful.
- Prefer joining via the primary keys listed below, not via name matching.
- Use ROUND(CAST(x AS numeric), n) for numeric rounding (Postgres-strict).

Schema (selected columns; FKs marked with →):

client (client_id PK, first_name, last_name, birth_date, nationality,
  civil_status, segment, kyc_level, pep_flag, sanctions_flag,
  customer_since, address_id → address, noga_code, employer)

address (address_id PK, street, house_number, postal_code, city, canton,
  country)

household (household_id PK, household_type, total_persons)
client_household (client_id, household_id, role, share_pct)

property (property_id PK, object_type, sub_type, address_id → address,
  construction_year, last_renovation_year, living_area_sqm,
  plot_area_sqm, rooms, heating_type, geak_class,
  annual_rental_income_chf, commercial_use, region_code)

loan (loan_id PK, primary_client_id → client, household_id → household,
  property_id → property, origination_date, original_amount,
  current_outstanding, first_mortgage_amount, second_mortgage_amount,
  ltv_pct, dsti_pct, status, product_line)

tranche (tranche_id PK, loan_id → loan, tranche_type ('saron','fix'),
  amount, interest_rate_pct, reference_rate, maturity_date)

valuation (valuation_id PK, property_id → property, valuation_date,
  market_value, mortgage_lending_value, is_current)
v_current_valuation (property_id, market_value, ...) — only the latest valuation per property.

income (income_id PK, client_id → client, gross_salary, bonus_avg_3y,
  rental_income, dividend_income)

affordability_assessment (assessment_id PK, loan_id → loan, assessment_date,
  total_cost_yearly, household_income_used, income_basis,
  dsti_calculated, pass_fail ('pass','exception','fail'))

risk_metrics (metric_id PK, loan_id → loan, pd_1y, lgd, ead,
  expected_loss, rating_internal, watchlist_flag, npl_flag,
  forbearance_flag, days_past_due, covenant_breach_flag,
  ifrs9_stage (1/2/3), lifetime_el, ifrs9_sicr_reason)

event (event_id PK, loan_id → loan, client_id → client, event_type,
  severity ('info','low','medium','high','critical'), source,
  detected_at, sla_due_date, sla_basis, status
  ('open','in_progress','escalated','closed_resolved','waived'),
  assigned_to, title, description)

loan_case (case_id PK, case_type, loan_id → loan, opened_at, due_date,
  status, priority, assigned_officer)

dunning_step (dunning_id PK, loan_id → loan, step (1-4), step_label,
  issued_date, due_date, amount_overdue_chf, fee_chf,
  status ('open','paid','escalated','closed'))

portfolio (portfolio_id PK, client_id → client, strategy
  ('konservativ','vorsichtig','mittel','wachstum','aktien'), benchmark,
  inception_date, total_value_chf, cash_chf, ytd_return_pct,
  one_year_return_pct, custodian)

position (position_id PK, portfolio_id → portfolio, isin, name,
  asset_class ('bond','etf_bond','equity','etf_equity','cash'),
  market_value_chf, weight_pct)

account (account_id PK, client_id → client, iban,
  account_type ('salary','savings','mortgage_servicing','rental','joint'),
  current_balance_chf, avg_balance_12m_chf)

account_tx (tx_id PK, account_id → account, tx_date, amount_chf,
  category ('salary','mortgage_payment','rental_income',
  'standing_order','card_purchase','withdrawal','tax',
  '3a_contribution','transfer_in','transfer_out','third_pillar_payout'),
  counterparty, description)

stress_scenario, stress_loan_metrics, v_stress_loan_compare — stress-test tables

audit_log (audit_id PK, entity_type ('loan'/'client'/'property'),
  entity_id, field_name, old_value, new_value, changed_by, changed_at)

Examples
--------

Q: "Top 10 Kredite nach LTV"
A: SELECT l.loan_id, c.first_name, c.last_name, l.ltv_pct, l.current_outstanding FROM loan l JOIN client c ON c.client_id = l.primary_client_id ORDER BY l.ltv_pct DESC LIMIT 10

Q: "MFH in Zürich mit DSTI über 30"
A: SELECT l.loan_id, c.last_name, l.dsti_pct, l.current_outstanding, p.object_type, a.canton FROM loan l JOIN client c ON c.client_id = l.primary_client_id JOIN property p USING(property_id) JOIN address a ON a.address_id = p.address_id WHERE p.object_type = 'MFH' AND a.canton = 'ZH' AND l.dsti_pct > 30 ORDER BY l.dsti_pct DESC LIMIT 200

Q: "Wieviele Loans pro IFRS-9-Stage?"
A: SELECT ifrs9_stage, COUNT(*) AS n_loans, ROUND(CAST(SUM(lifetime_el)/1e6 AS numeric), 2) AS lifetime_el_mchf FROM risk_metrics WHERE ifrs9_stage IS NOT NULL GROUP BY ifrs9_stage ORDER BY ifrs9_stage

Q: "Kunden mit Lohnausfall in den letzten 6 Monaten"
A: SELECT DISTINCT a.client_id, c.first_name, c.last_name, MIN(at.tx_date) AS first_gap FROM account a JOIN client c ON c.client_id = a.client_id JOIN account_tx at ON at.account_id = a.account_id WHERE a.account_type = 'salary' AND at.tx_date >= '2025-11-06' AND NOT EXISTS (SELECT 1 FROM account_tx at2 WHERE at2.account_id = a.account_id AND at2.tx_date BETWEEN at.tx_date AND date(at.tx_date, '+45 days') AND at2.category = 'salary') GROUP BY a.client_id, c.first_name, c.last_name LIMIT 100
"""

ALLOWED_PREFIX = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|"
    r"PRAGMA|VACUUM|ATTACH|DETACH|REPLACE|EXEC)\b",
    re.IGNORECASE,
)


def is_safe_select(sql: str) -> tuple[bool, str]:
    """Return (ok, reason). Reject anything that's not a single read-only SELECT."""
    if not sql or not sql.strip():
        return False, "empty"
    s = sql.strip().rstrip(";")
    if not ALLOWED_PREFIX.match(s):
        return False, "must start with SELECT or WITH"
    if FORBIDDEN.search(s):
        return False, "contains forbidden keyword (write/DDL)"
    if ";" in s:
        return False, "no semicolons allowed (single statement only)"
    return True, ""


def generate_sql(question: str, api_key: str, model: str = "claude-haiku-4-5") -> str:
    """Call Claude and return the generated SQL."""
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    text_blocks = [b.text for b in msg.content if hasattr(b, "text")]
    sql = "\n".join(text_blocks).strip()
    # Trim Markdown fences if the model added them despite the instruction.
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```\s*$", "", sql)
    return sql.strip().rstrip(";")
