"""DB engine factory.

Returns:
    - PostgreSQL engine if `DATABASE_URL` env var or `st.secrets["database"]["url"]`
      is set (production / Streamlit Cloud).
    - SQLite engine pointing at the local generated DB otherwise (local dev).

Streamlit `@st.cache_resource` keeps a single engine alive across reruns.
"""
from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

import streamlit as st

from kreditueberwachung_mock import config


def _resolve_url() -> tuple[str, str]:
    """Return (sqlalchemy_url, dialect) — 'postgres' or 'sqlite'."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            url = st.secrets["database"]["url"]
        except Exception:
            url = None
    if url:
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url, "postgres"
    return f"sqlite:///{config.DB_PATH}", "sqlite"


@st.cache_resource(show_spinner=False)
def engine() -> Engine:
    url, dial = _resolve_url()
    if dial == "postgres":
        # Use NullPool so we don't hold connections across HTTP requests:
        # Supabase's PgBouncer in transaction-pool mode closes connections
        # after each transaction, which fights with SQLAlchemy's QueuePool.
        # NullPool simply opens + closes per query, letting PgBouncer pool
        # for us.
        return create_engine(
            url,
            poolclass=NullPool,
            future=True,
            connect_args={"connect_timeout": 15, "sslmode": "require"},
        )
    return create_engine(url, future=True)


def dialect() -> str:
    return _resolve_url()[1]


def is_postgres() -> bool:
    return dialect() == "postgres"
