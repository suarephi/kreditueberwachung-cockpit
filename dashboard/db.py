"""DB engine factory.

Returns:
    - PostgreSQL engine if `DATABASE_URL` env var or `st.secrets["database"]["url"]`
      is set (production / Streamlit Cloud).
    - SQLite engine pointing at the local generated DB otherwise (local dev).

Streamlit `@st.cache_resource` keeps a single engine alive across reruns.
"""
from __future__ import annotations
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

import streamlit as st

from kreditueberwachung_mock import config


def _resolve_url() -> tuple[str, str]:
    """Return (sqlalchemy_url, dialect) — 'postgres' or 'sqlite'."""
    # Highest priority: environment variable (used by migrate script).
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            url = st.secrets["database"]["url"]      # Streamlit Cloud secrets
        except Exception:
            url = None
    if url:
        # Normalise legacy `postgres://` scheme to `postgresql+psycopg2://`.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url, "postgres"
    return f"sqlite:///{config.DB_PATH}", "sqlite"


@st.cache_resource(show_spinner=False)
def engine() -> Engine:
    url, _ = _resolve_url()
    eng = create_engine(url, pool_pre_ping=True, future=True)
    return eng


def dialect() -> str:
    return _resolve_url()[1]


def is_postgres() -> bool:
    return dialect() == "postgres"
