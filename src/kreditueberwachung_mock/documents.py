"""Document metadata generation."""
from __future__ import annotations
import datetime as dt
import hashlib
import numpy as np
import pandas as pd
from . import config, rng as rngmod


CLIENT_DOCS = ["ID", "Lohnausweis", "Steuererklärung", "Betreibungsauszug", "AHV-Ausweis"]
LOAN_DOCS   = ["Kreditvertrag", "Pfandvertrag", "Vollmacht"]
PROP_DOCS   = ["Grundbuchauszug", "Schätzungsgutachten", "Versicherungspolice", "Energieausweis"]


def generate_documents(clients: pd.DataFrame, loans: pd.DataFrame,
                       properties: pd.DataFrame) -> pd.DataFrame:
    rng = rngmod.child_rng("documents")
    today = dt.date.today()
    rows = []
    next_id = 1

    def emit(parent_type, parent_id, doc_type, valid_years=2):
        nonlocal next_id
        upload = today - dt.timedelta(days=int(rng.integers(30, 365 * 4)))
        expiry = upload + dt.timedelta(days=int(365 * valid_years))
        r = rng.random()
        if r < 0.85:
            status = "valid" if expiry >= today else "expired"
        elif r < 0.95:
            status = "superseded"
        else:
            status = "missing"
        h = hashlib.sha1(f"{parent_type}-{parent_id}-{doc_type}-{upload}".encode()).hexdigest()[:16]
        rows.append({
            "document_id": next_id,
            "parent_type": parent_type,
            "parent_id":   parent_id,
            "doc_type":    doc_type,
            "filename":    f"{doc_type}_{parent_id}.pdf",
            "upload_date": upload.isoformat(),
            "expiry_date": expiry.isoformat(),
            "status":      status,
            "hash":        h,
        })
        next_id += 1

    for c in clients.itertuples(index=False):
        for d in CLIENT_DOCS:
            emit("client", int(c.client_id), d, valid_years=int(np.clip(rng.normal(2, 0.5), 1, 4)))

    for ln in loans.itertuples(index=False):
        for d in LOAN_DOCS:
            emit("loan", int(ln.loan_id), d, valid_years=20)

    for p in properties.itertuples(index=False):
        for d in PROP_DOCS:
            emit("property", int(p.property_id), d, valid_years=int(np.clip(rng.normal(5, 1.5), 1, 10)))

    return pd.DataFrame(rows)
