"""Case / dossier generation."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from . import config, rng as rngmod


CASE_TYPE_W = {
    "annual_review":   0.55,
    "event_review":    0.25,
    "renewal":         0.10,
    "restructuring":   0.04,
    "forbearance":     0.04,
    "recovery":        0.02,
}
TEAMS = ["KMU-Team-A", "Retail-Team-1", "Retail-Team-2", "PrivateBanking", "WorkOut", "Special-Credit"]


def generate_cases(loans: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    rng = rngmod.child_rng("cases")
    today = dt.date.today()
    n_loans = len(loans)
    expected_cases = int(n_loans * config.CASES_PER_LOAN_MEAN)
    rows = []

    types  = list(CASE_TYPE_W.keys())
    weights = np.array(list(CASE_TYPE_W.values()))
    weights = weights / weights.sum()

    loan_ids = loans["loan_id"].values
    client_ids = loans["primary_client_id"].values
    origin_dates = [dt.date.fromisoformat(d) for d in loans["origination_date"].values]

    for _ in range(expected_cases):
        i = int(rng.integers(0, n_loans))
        ctype = types[int(rng.choice(len(types), p=weights))]
        life_days = max(61, (today - origin_dates[i]).days)
        opened = origin_dates[i] + dt.timedelta(days=int(rng.integers(60, life_days)))
        if ctype == "annual_review":
            due = opened + dt.timedelta(days=30)
            closed = opened + dt.timedelta(days=int(rng.integers(7, 30)))
            decision, status = "approve", "closed"
        elif ctype == "event_review":
            due = opened + dt.timedelta(days=21)
            r = rng.random()
            if r < 0.65:
                closed = opened + dt.timedelta(days=int(rng.integers(2, 21)))
                decision, status = "approve", "closed"
            elif r < 0.85:
                closed = opened + dt.timedelta(days=int(rng.integers(2, 21)))
                decision, status = "waive", "closed"
            else:
                closed = None
                decision, status = "escalate", "open"
        elif ctype == "renewal":
            due = opened + dt.timedelta(days=60)
            closed = opened + dt.timedelta(days=int(rng.integers(20, 60)))
            decision, status = "approve", "closed"
        elif ctype == "restructuring":
            due = opened + dt.timedelta(days=90)
            closed = opened + dt.timedelta(days=int(rng.integers(45, 90))) if rng.random() < 0.7 else None
            decision = "restructure" if closed else None
            status = "closed" if closed else "open"
        elif ctype == "forbearance":
            due = opened + dt.timedelta(days=120)
            closed = opened + dt.timedelta(days=int(rng.integers(30, 120))) if rng.random() < 0.6 else None
            decision = "approve" if closed else None
            status = "closed" if closed else "open"
        else:  # recovery
            due = opened + dt.timedelta(days=365)
            closed = None
            decision = None
            status = "open"

        rows.append({
            "case_id":          len(rows) + 1,
            "case_type":        ctype,
            "loan_id":          int(loan_ids[i]),
            "client_id":        int(client_ids[i]),
            "opened_at":        opened.isoformat(),
            "due_date":         due.isoformat(),
            "closed_at":        closed.isoformat() if closed else None,
            "status":           status,
            "priority":         rng.choice(["low", "normal", "high"], p=[0.3, 0.6, 0.1]),
            "assigned_team":    TEAMS[int(rng.integers(0, len(TEAMS)))],
            "assigned_officer": f"OFFICER-{int(rng.integers(1, 60))}",
            "decision":         decision,
            "decision_at":      closed.isoformat() if closed else None,
            "decided_by":       f"OFFICER-{int(rng.integers(1, 60))}" if closed else None,
            "notes":            None,
        })
    return pd.DataFrame(rows)
