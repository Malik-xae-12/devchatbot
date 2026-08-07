"""
On-prem SQL Server connection layer.

Nothing here runs until app.config.settings.db_configured is True.
Fill in DB_SERVER / DB_NAME in your .env, then either:
  - set DB_USE_WINDOWS_AUTH=true to connect as whatever account is running
    this process (typical for a dev box on a domain-joined machine), or
  - set DB_USER / DB_PASSWORD for a SQL login.
This module will lazily create a pooled SQLAlchemy engine on first use.

Whichever auth method you use, the underlying account should be
READ-ONLY — the query validator assumes destructive statements are
already blocked at the DB permission level, not just in the generated SQL.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings

_engine: Engine | None = None


class DatabaseNotConfiguredError(Exception):
    """Raised when a DB operation is attempted before connection details are set."""


def get_engine() -> Engine:
    global _engine
    if not settings.db_configured:
        raise DatabaseNotConfiguredError(
            "DB connection not configured yet. Set DB_SERVER, DB_NAME in your "
            ".env file, plus either DB_USE_WINDOWS_AUTH=true, or DB_USER / "
            "DB_PASSWORD for a SQL login."
        )
    if _engine is None:
        _engine = create_engine(
            settings.sqlalchemy_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            connect_args={"timeout": settings.query_timeout_seconds},
        )
    return _engine


@contextmanager
def get_connection():
    engine = get_engine()
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def run_query(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a validated, read-only SQL statement and return rows as dicts."""
    with get_connection() as conn:
        result = conn.execute(text(sql), params or {})
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return rows


def test_connection() -> bool:
    try:
        with get_connection() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
