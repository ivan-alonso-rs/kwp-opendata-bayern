"""Database connection helpers (PostgreSQL/PostGIS via SQLAlchemy).

Credentials are read from environment variables (PGHOST, PGPORT, PGDATABASE,
PGUSER, PGPASSWORD), normally loaded from the git-ignored .env file by
kwp.config.load_env(). Credentials are never written to logs.
"""

from __future__ import annotations

import os

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


def get_engine(echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for the PostGIS database defined in the environment."""
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD"),
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ.get("PGDATABASE", "waermeplanung"),
    )
    # pool_pre_ping avoids errors from stale connections in long notebook sessions
    return create_engine(url, echo=echo, pool_pre_ping=True)


def describe_target() -> str:
    """Human-readable connection target without the password (safe to print)."""
    return (
        f"{os.environ.get('PGUSER', 'postgres')}@{os.environ.get('PGHOST', 'localhost')}:"
        f"{os.environ.get('PGPORT', '5432')}/{os.environ.get('PGDATABASE', 'waermeplanung')}"
    )
