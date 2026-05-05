"""Bank accounts + 24-month transaction history.

For a configurable share of clients (`TX_FRAC`), generates:
  • a salary account (always)
  • a savings account (~70%)
  • a mortgage-servicing account (if the client has a loan)
  • a rental-income account (if the client owns MFH/Gewerbe)

Monthly cadence covers salary, 13th-salary, bonus, mortgage payment,
standing orders (insurance, telecom, health), card spend, ATM withdrawals,
quarterly tax instalments, annual 3a contribution.

About 7% of accounts get a *material change* event in the 24-month window
(salary jump, salary loss, employer change, 3a payout, inheritance, divorce
settlement) so the data isn't a clean treadmill.
"""
from __future__ import annotations
import calendar
import datetime as dt
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from . import config, rng as rngmod


@dataclass
class _AccountSpec:
    account_id: int
    client_id: int
    iban: str
    account_type: str
    opened_date: dt.date
    rows: list[dict] = field(default_factory=list)


def _iban(rng: np.random.Generator) -> str:
    bank = "00767"  # ZKB-style placeholder
    acct = "".join(str(int(rng.integers(0, 10))) for _ in range(12))
    cd = (98 - (int(bank + acct + "121700") % 97)) % 97  # rough mod-97; mock-grade
    return f"CH{cd:02d}{bank}{acct}"


def _month_iter(start: dt.date, end: dt.date):
    cur = dt.date(start.year, start.month, 1)
    while cur <= end:
        yield cur
        if cur.month == 12:
            cur = dt.date(cur.year + 1, 1, 1)
        else:
            cur = dt.date(cur.year, cur.month + 1, 1)


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _push(rows: list[dict], aid: int, day: dt.date, amount: float, category: str,
          counterparty: str = "", description: str = "", reference: str = ""):
    rows.append({
        "account_id":   aid,
        "tx_date":      day.isoformat(),
        "value_date":   day.isoformat(),
        "amount_chf":   round(float(amount), 2),
        "category":     category,
        "counterparty": counterparty,
        "description":  description,
        "reference":    reference,
    })


def _pick_material_change(rng: np.random.Generator) -> str | None:
    """Returns a tag for the change to inject, or None for a clean stream."""
    if rng.random() > 0.07:
        return None
    return str(rng.choice(
        ["salary_jump", "salary_loss", "employer_change",
         "3a_payout", "inheritance", "divorce"],
        p=[0.30, 0.25, 0.15, 0.10, 0.10, 0.10],
    ))


def generate_accounts_and_tx(
    clients: pd.DataFrame,
    incomes: pd.DataFrame,
    loans: pd.DataFrame,
    properties: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build account + account_tx DataFrames. Returns ([], []) when TX_FRAC == 0."""
    if config.TX_FRAC <= 0:
        return pd.DataFrame(), pd.DataFrame()

    rng = rngmod.child_rng("transactions")
    today = dt.date.today()
    start = (today.replace(day=1) - dt.timedelta(days=31 * config.TX_MONTHS)).replace(day=1)

    income_lookup = incomes.set_index("client_id")["gross_salary"].to_dict()
    bonus_lookup = incomes.set_index("client_id")["bonus_avg_3y"].to_dict()
    loans_by_client = loans.groupby("primary_client_id").agg(
        loan_id=("loan_id", "first"),
        outstanding=("current_outstanding", "sum"),
        property_id=("property_id", "first"),
    ).to_dict("index")
    prop_lookup = properties.set_index("property_id").to_dict("index") if not properties.empty else {}

    # Sample subset of clients
    n = len(clients)
    has_account = rng.random(n) < config.TX_FRAC
    sel = clients.loc[has_account, ["client_id"]].reset_index(drop=True)
    if sel.empty:
        return pd.DataFrame(), pd.DataFrame()

    accounts: list[dict] = []
    tx_rows: list[dict] = []
    next_aid = 1

    for _, c in sel.iterrows():
        cid = int(c["client_id"])
        gross_annual = float(income_lookup.get(cid, 90_000.0))
        bonus_annual = float(bonus_lookup.get(cid, 0.0))
        monthly_salary = gross_annual / 12.0
        change = _pick_material_change(rng)
        change_month_offset = int(rng.integers(3, max(4, config.TX_MONTHS - 3)))
        # Effective new salary multiplier kicks in after the change month.
        salary_factor = np.ones(config.TX_MONTHS + 1)
        skip_months: set[int] = set()
        if change == "salary_jump":
            salary_factor[change_month_offset:] = float(rng.uniform(1.15, 1.40))
        elif change == "salary_loss":
            gap = int(rng.integers(1, 7))
            for k in range(change_month_offset, min(config.TX_MONTHS + 1, change_month_offset + gap)):
                skip_months.add(k)
            salary_factor[change_month_offset + gap:] = float(rng.uniform(0.65, 0.95))
        elif change == "employer_change":
            salary_factor[change_month_offset:] = float(rng.uniform(0.92, 1.18))

        employer_old = f"AG-{int(rng.integers(1000, 9999))}"
        employer_new = f"AG-{int(rng.integers(1000, 9999))}"

        # ---- account: salary
        salary_aid = next_aid
        salary_iban = _iban(rng)
        accounts.append({
            "account_id": salary_aid, "client_id": cid, "iban": salary_iban,
            "account_type": "salary", "currency": "CHF",
            "opened_date": (start - dt.timedelta(days=int(rng.integers(0, 365 * 5)))).isoformat(),
            "current_balance_chf": 0.0, "avg_balance_12m_chf": 0.0, "status": "active",
        })
        next_aid += 1
        # ---- account: savings (70%)
        savings_aid = None
        if rng.random() < 0.70:
            savings_aid = next_aid
            accounts.append({
                "account_id": savings_aid, "client_id": cid, "iban": _iban(rng),
                "account_type": "savings", "currency": "CHF",
                "opened_date": (start - dt.timedelta(days=int(rng.integers(0, 365 * 5)))).isoformat(),
                "current_balance_chf": 0.0, "avg_balance_12m_chf": 0.0, "status": "active",
            })
            next_aid += 1
        # ---- account: mortgage_servicing (if client has loan)
        loan_info = loans_by_client.get(cid)
        mortgage_aid = None
        annual_mortgage_payment = 0.0
        if loan_info:
            mortgage_aid = next_aid
            accounts.append({
                "account_id": mortgage_aid, "client_id": cid, "iban": _iban(rng),
                "account_type": "mortgage_servicing", "currency": "CHF",
                "opened_date": (start - dt.timedelta(days=int(rng.integers(0, 365 * 5)))).isoformat(),
                "current_balance_chf": 0.0, "avg_balance_12m_chf": 0.0, "status": "active",
            })
            next_aid += 1
            outstanding = float(loan_info.get("outstanding", 0.0) or 0.0)
            annual_mortgage_payment = outstanding * 0.025  # interest+amort placeholder
        # ---- account: rental (if owns MFH/Gewerbe via this loan's property)
        rental_aid = None
        rental_monthly = 0.0
        if loan_info:
            pid = int(loan_info.get("property_id") or 0)
            prop = prop_lookup.get(pid, {})
            if prop.get("object_type") in ("MFH", "Gewerbe"):
                annual = prop.get("annual_rental_income_chf")
                if annual and not pd.isna(annual):
                    rental_aid = next_aid
                    accounts.append({
                        "account_id": rental_aid, "client_id": cid, "iban": _iban(rng),
                        "account_type": "rental", "currency": "CHF",
                        "opened_date": (start - dt.timedelta(days=int(rng.integers(0, 365 * 3)))).isoformat(),
                        "current_balance_chf": 0.0, "avg_balance_12m_chf": 0.0, "status": "active",
                    })
                    next_aid += 1
                    rental_monthly = float(annual) / 12.0

        # Standing orders (per-client, monthly)
        insurance_so = float(rng.uniform(180, 720))
        telecom_so   = float(rng.uniform(70, 180))
        health_so    = float(rng.uniform(310, 580))

        # Per-month transactions
        m_idx = -1
        for month_first in _month_iter(start, today):
            m_idx += 1
            if m_idx > config.TX_MONTHS:
                break
            mlen = _last_day(month_first.year, month_first.month)
            sal_day = month_first.replace(day=min(25, mlen))

            # Salary
            if m_idx not in skip_months:
                emp = employer_new if (change == "employer_change" and m_idx >= change_month_offset) else employer_old
                amt = monthly_salary * float(salary_factor[m_idx]) * float(rng.uniform(0.99, 1.01))
                _push(tx_rows, salary_aid, sal_day, +amt, "salary", emp, "Lohnzahlung")
            # 13th salary in December
            if month_first.month == 12 and m_idx not in skip_months:
                amt = monthly_salary * float(salary_factor[m_idx])
                _push(tx_rows, salary_aid, month_first.replace(day=min(20, mlen)),
                      +amt, "salary", "13. Monatslohn", "13. Monatslohn")
            # Bonus in March
            if month_first.month == 3 and bonus_annual > 0 and m_idx not in skip_months:
                _push(tx_rows, salary_aid, month_first.replace(day=15),
                      +bonus_annual * float(salary_factor[m_idx]), "salary",
                      "Bonus", "Jahresbonus")
            # Mortgage payment
            if mortgage_aid:
                pay_day = month_first.replace(day=min(5, mlen))
                amt = annual_mortgage_payment / 12.0
                _push(tx_rows, salary_aid, pay_day, -amt, "mortgage_payment",
                      "Bank intern", f"Hypothek (Kredit {loan_info.get('loan_id')})")
                _push(tx_rows, mortgage_aid, pay_day, +amt, "mortgage_payment",
                      "Bank intern", f"Hypothek (Kredit {loan_info.get('loan_id')})")
            # Rental income
            if rental_aid and rental_monthly > 0:
                _push(tx_rows, rental_aid, month_first.replace(day=min(2, mlen)),
                      +rental_monthly * float(rng.uniform(0.95, 1.0)),
                      "rental_income", "Mieter (div.)", "Mietzinseingang")
            # Standing orders (insurance, telecom, health)
            so_day = month_first.replace(day=min(3, mlen))
            _push(tx_rows, salary_aid, so_day, -insurance_so, "standing_order",
                  "Helvetia / Allianz", "Versicherung")
            _push(tx_rows, salary_aid, so_day, -telecom_so, "standing_order",
                  "Swisscom / Salt", "Telekom")
            _push(tx_rows, salary_aid, so_day, -health_so, "standing_order",
                  "Krankenkasse", "Krankenkassenprämie")
            # Card purchases (~22 per month, log-normal)
            n_card = int(rng.poisson(22))
            for _ in range(n_card):
                day = month_first + dt.timedelta(days=int(rng.integers(0, mlen)))
                amt = float(np.clip(rng.lognormal(3.6, 1.0), 5, 1500))
                _push(tx_rows, salary_aid, day, -amt, "card_purchase",
                      str(rng.choice(["Migros", "Coop", "SBB", "Apple Pay", "Amazon", "Restaurant", "Tankstelle"])),
                      "Karten-/POS-Buchung")
            # ATM withdrawals (~5/month)
            for _ in range(int(rng.poisson(5))):
                day = month_first + dt.timedelta(days=int(rng.integers(0, mlen)))
                amt = float(rng.choice([100, 200, 500]))
                _push(tx_rows, salary_aid, day, -amt, "withdrawal", "Bankomat", "Bargeldbezug")
            # Tax instalment (quarterly)
            if month_first.month in (3, 6, 9, 12):
                tax_amt = float(np.clip(monthly_salary * 0.6, 800, 12000))
                _push(tx_rows, salary_aid, month_first.replace(day=min(15, mlen)),
                      -tax_amt, "tax", "Steueramt", "Akontosteuer")
            # 3a contribution (Nov)
            if month_first.month == 11:
                amt = float(min(7056.0, monthly_salary * 1.2))
                _push(tx_rows, salary_aid, month_first.replace(day=min(20, mlen)),
                      -amt, "3a_contribution", "Säule 3a Stiftung", "3a Einzahlung")
                if savings_aid:
                    _push(tx_rows, savings_aid, month_first.replace(day=min(20, mlen)),
                          +amt, "transfer_in", "Säule 3a Stiftung", "3a Einzahlung")
            # Periodic transfer salary → savings
            if savings_aid and rng.random() < 0.7:
                amt = float(np.clip(rng.uniform(0.05, 0.25) * monthly_salary, 200, 5000))
                day = month_first.replace(day=min(28, mlen))
                _push(tx_rows, salary_aid, day, -amt, "transfer_out", "Eigenes Sparkonto", "Spar-Übertrag")
                _push(tx_rows, savings_aid, day, +amt, "transfer_in", "Eigenes Lohnkonto", "Spar-Übertrag")

            # Inject one-off material change in the change month
            if m_idx == change_month_offset:
                if change == "3a_payout":
                    amt = float(rng.uniform(50_000, 200_000))
                    _push(tx_rows, salary_aid, month_first.replace(day=min(10, mlen)),
                          +amt, "third_pillar_payout", "Säule 3a Stiftung", "3a-Bezug Vorbezug")
                elif change == "inheritance":
                    amt = float(rng.uniform(50_000, 500_000))
                    _push(tx_rows, salary_aid, month_first.replace(day=min(10, mlen)),
                          +amt, "transfer_in", "Notariat", "Erbschaft")
                elif change == "divorce":
                    amt = float(rng.uniform(20_000, 200_000))
                    _push(tx_rows, salary_aid, month_first.replace(day=min(15, mlen)),
                          -amt, "transfer_out", "Anwaltskanzlei", "Scheidungsausgleich")

    tx_df = pd.DataFrame(tx_rows)
    if not tx_df.empty:
        tx_df.insert(0, "tx_id", np.arange(1, len(tx_df) + 1))

    # Summarise per-account balance from the tx stream
    acc_df = pd.DataFrame(accounts)
    if not tx_df.empty and not acc_df.empty:
        cur_bal = tx_df.groupby("account_id")["amount_chf"].sum().to_dict()
        # Average monthly balance over last 12 months, very rough cumulative-mean approximation.
        last12_cut = (today - dt.timedelta(days=365)).isoformat()
        last12 = tx_df[tx_df["tx_date"] >= last12_cut]
        avg12 = last12.groupby("account_id")["amount_chf"].sum().to_dict()
        acc_df["current_balance_chf"] = acc_df["account_id"].map(cur_bal).fillna(0.0).round(2)
        # Use net-12m-flow / 2 as a stand-in for an average; keeps the column populated.
        acc_df["avg_balance_12m_chf"] = (acc_df["account_id"].map(avg12).fillna(0.0) / 2).round(2)

    return acc_df, tx_df
