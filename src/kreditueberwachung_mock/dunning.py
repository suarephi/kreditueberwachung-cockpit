"""Mahnwesen / dunning steps.

Generates per-loan dunning escalation chains for delinquent loans, following
the typical Swiss workflow:
    Step 1: 1. Mahnung           (10–14 d after due-date)
    Step 2: 2. Mahnung            (~30 d after step 1)
    Step 3: Bonitätsentscheid     (~30 d after step 2, RM decision)
    Step 4: Verwertungsbegehren   (~60 d after step 3, escalation to legal)

Triggers a chain when the loan has either an open `payment_arrears` /
`payment_default` event, or `npl_flag = 1` in risk_metrics.
"""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd

from . import config, rng as rngmod


STEP_LABELS = {
    1: "1. Mahnung",
    2: "2. Mahnung",
    3: "Bonitätsentscheid",
    4: "Verwertungsbegehren",
}
STEP_FEES = {1: 30.0, 2: 60.0, 3: 0.0, 4: 0.0}


def generate_dunning_steps(loans: pd.DataFrame, events: pd.DataFrame,
                            risk: pd.DataFrame) -> pd.DataFrame:
    """Build dunning_step rows for the loans that look delinquent.

    Heuristic:
      - any loan with payment_arrears/payment_default event marked open|escalated
        → start a chain
      - any loan with npl_flag = 1 → start a chain (chain may extend to step 4)
    """
    rng = rngmod.child_rng("dunning")
    today = dt.date.today()

    arrears_loans = set()
    if not events.empty:
        mask = events["event_type"].isin(["payment_arrears", "payment_default"]) & \
               events["status"].isin(["open", "in_progress", "escalated"])
        arrears_loans = set(events.loc[mask, "loan_id"].astype(int).tolist())
    npl_loans = set()
    if not risk.empty:
        npl_loans = set(risk.loc[risk["npl_flag"] == 1, "loan_id"].astype(int).tolist())
    candidates = sorted(arrears_loans | npl_loans)
    if not candidates:
        return pd.DataFrame()

    loans_lookup = loans.set_index("loan_id")[["current_outstanding"]].to_dict("index")
    rows: list[dict] = []
    next_id = 1
    for loan_id in candidates:
        info = loans_lookup.get(int(loan_id), {})
        outstanding = float(info.get("current_outstanding", 0.0) or 0.0)
        if outstanding <= 0:
            continue
        # Monthly rate proxy ~ outstanding × 2.5 % / 12 (interest + amort placeholder)
        monthly_rate = outstanding * 0.025 / 12.0
        # How many steps do we reach? Most stop at 1, fewer at 2/3, very few 4.
        npl = loan_id in npl_loans
        if npl:
            r = rng.random()
            if r < 0.40:
                max_step = 4
            elif r < 0.75:
                max_step = 3
            else:
                max_step = 2
        else:
            r = rng.random()
            if r < 0.55:
                max_step = 1
            elif r < 0.85:
                max_step = 2
            elif r < 0.95:
                max_step = 3
            else:
                max_step = 4

        # First missed payment 30–180 days ago
        first_due = today - dt.timedelta(days=int(rng.integers(30, 181)))
        cur_date = first_due + dt.timedelta(days=int(rng.integers(10, 15)))  # step 1
        for step in range(1, max_step + 1):
            issue_date = cur_date
            due_date = issue_date + dt.timedelta(
                days={1: 14, 2: 21, 3: 30, 4: 45}[step]
            )
            n_overdue_months = step + int(rng.integers(0, 2))
            amount_overdue = round(monthly_rate * n_overdue_months, 0)
            # Status: latest step is open; earlier steps either paid or escalated.
            if step == max_step:
                status = "open"
                resolved_date = None
            else:
                # If we got escalated to a later step, this one is escalated.
                status = "escalated"
                resolved_date = (issue_date + dt.timedelta(
                    days=int(rng.integers(15, 30)))).isoformat()
            rows.append({
                "dunning_id":         next_id,
                "loan_id":            int(loan_id),
                "step":               step,
                "step_label":         STEP_LABELS[step],
                "issued_date":        issue_date.isoformat(),
                "due_date":           due_date.isoformat(),
                "amount_overdue_chf": amount_overdue,
                "fee_chf":            STEP_FEES[step],
                "status":             status,
                "resolved_date":      resolved_date,
                "assigned_officer":   f"OFFICER-{(int(loan_id) % 60) + 1}",
                "reference":          f"MA-{int(loan_id):06d}-{step}",
            })
            next_id += 1
            # Next step happens 30 d (step1→2), 30 d (step2→3), 60 d (step3→4) later
            gap = {1: 30, 2: 30, 3: 60}.get(step, 30)
            cur_date = cur_date + dt.timedelta(days=gap)

    return pd.DataFrame(rows)
