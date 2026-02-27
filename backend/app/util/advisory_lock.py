"""PostgreSQL advisory lock helpers.

Provides both async and sync context managers so the same
locking pattern can be used from:

- **Gunicorn master** (sync) — e.g. database migrations in
  ``on_starting``.
- **Async worker tasks** — e.g. periodic cleanup jobs running
  inside the FastAPI event loop.

Each action that should run on only one process at a time gets
its own lock ID so independent actions can execute in parallel.

Advisory locks MUST bypass PgBouncer (``POOL_MODE: transaction``
multiplexes backend connections, breaking session-level locks).
All connections here use ``DIRECT_DATABASE_URL`` which targets
PostgreSQL directly.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator, Generator
from functools import lru_cache

import psycopg2
from core.logger import get_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)

logger = get_logger("app")

# ── Lock IDs ────────────────────────────────────────────────
# Each constant identifies a distinct action.  Values are
# arbitrary but must be unique across the application and
# stable across releases.
LOCK_MIGRATION: int = 100_001
LOCK_CLEANUP_LOGS: int = 100_002
LOCK_CLEANUP_GUESTS: int = 100_003
LOCK_CLEANUP_UNVERIFIED: int = 100_004


# ── Direct-connect engine (bypasses PgBouncer) ─────────────
@lru_cache(maxsize=1)
def _get_direct_engine() -> AsyncEngine:
    """Create a small async engine connected directly to Postgres.

    Uses ``AUTOCOMMIT`` isolation so advisory lock statements
    do not leave an idle open transaction (SQLAlchemy's
    autobegin would otherwise start one on the first
    ``execute``).
    """
    from core.config import DIRECT_DATABASE_URL

    return create_async_engine(
        DIRECT_DATABASE_URL,
        isolation_level="AUTOCOMMIT",
        pool_size=2,
        max_overflow=2,
        pool_pre_ping=True,
    )


async def dispose_direct_engine() -> None:
    """Dispose the direct engine on application shutdown."""
    if _get_direct_engine.cache_info().currsize:
        await _get_direct_engine().dispose()


# ── Async context manager (for worker tasks) ────────────────
@contextlib.asynccontextmanager
async def advisory_lock(
    lock_id: int,
) -> AsyncGenerator[bool, None]:
    """Try to acquire a Postgres advisory lock (non-blocking).

    Yields ``True`` if the lock was acquired, ``False`` if
    another session already holds it.  The lock is released
    when the context exits (or when the connection closes).

    Connects directly to PostgreSQL (bypassing PgBouncer)
    so session-level locks work correctly.
    """
    engine = _get_direct_engine()
    async with engine.connect() as conn:
        row = await conn.execute(
            text("SELECT pg_try_advisory_lock(:id)"),
            {"id": lock_id},
        )
        acquired: bool = row.scalar_one()
        try:
            yield acquired
        finally:
            if acquired:
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:id)"),
                    {"id": lock_id},
                )


# ── Sync context manager (for gunicorn master) ──────────────
@contextlib.contextmanager
def advisory_lock_sync(
    lock_id: int,
) -> Generator[bool, None, None]:
    """Acquire a Postgres advisory lock synchronously via psycopg2.

    Builds a direct-to-Postgres DSN from config (bypassing
    PgBouncer).  Uses ``autocommit`` mode so advisory lock
    statements execute outside a transaction.

    Yields ``True`` if acquired, ``False`` otherwise.
    """
    from core.config import (
        POSTGRES_DB,
        POSTGRES_HOST,
        POSTGRES_PASSWORD,
        POSTGRES_PORT,
        POSTGRES_USER,
    )

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_try_advisory_lock(%s)", (lock_id,)
            )
            acquired: bool = cur.fetchone()[0]
        try:
            yield acquired
        finally:
            if acquired:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT pg_advisory_unlock(%s)",
                        (lock_id,),
                    )
    finally:
        conn.close()
