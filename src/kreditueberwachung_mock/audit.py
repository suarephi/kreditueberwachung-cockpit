"""Audit log generation."""
from __future__ import annotations
import datetime as dt
import numpy as np
import pandas as pd
from . import config, rng as rngmod


FIELDS = [
    ("client", "phone_mobile"),
    ("client", "email"),
    ("client", "address_id"),
    ("client", "employer"),
    ("client", "civil_status"),
    ("loan",   "current_outstanding"),
    ("loan",   "ltv_pct"),
    ("loan",   "status"),
    ("property", "geak_class"),
    ("property", "last_renovation_year"),
]


def generate_audit_log(clients: pd.DataFrame) -> pd.DataFrame:
    rng = rngmod.child_rng("audit")
    today = dt.date.today()
    rows = []
    next_id = 1
    for c in clients.itertuples(index=False):
        n = int(rng.poisson(config.AUDIT_PER_CLIENT_MEAN))
        for _ in range(n):
            ent_type, field = FIELDS[int(rng.integers(0, len(FIELDS)))]
            ent_id = int(c.client_id) if ent_type == "client" else int(c.client_id)
            changed_at = today - dt.timedelta(days=int(rng.integers(1, 365 * 5)))
            rows.append({
                "audit_id":      next_id,
                "entity_type":   ent_type,
                "entity_id":     ent_id,
                "field_name":    field,
                "old_value":     "<old>",
                "new_value":     "<new>",
                "changed_by":    f"USER-{int(rng.integers(1, 80))}",
                "changed_at":    changed_at.isoformat(),
                "source_system": rng.choice(["CRM", "Avaloq", "FrontApp", "Manual"], p=[0.5, 0.3, 0.15, 0.05]),
            })
            next_id += 1
    return pd.DataFrame(rows)
