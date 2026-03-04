from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

import core.config as cfg
from core.app_exception import AppException
from core.config import (
    DATABASE_URL,
    DB_CONNECTION_TIMEOUT,
    DB_STATEMENT_TIMEOUT,
    DEBUG,
)
from core.logger import get_logger
from fastapi import Depends
from models.enums import AppErrorCode
from sqlalchemy import event, text
from sqlalchemy.exc import (
    DBAPIError,
    OperationalError,
    TimeoutError,  # noqa: A004
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import UOWTransaction, sessionmaker
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

db_logger = get_logger("database")

if cfg.DEBUG:
    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def _attach_statement_timeout(engine: AsyncEngine) -> None:
    """Attach a statement timeout listener to a SQLAlchemy async engine.

    This is registered after the engine is created to avoid module import
    side-effects.
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _set_statement_timeout(dbapi_conn, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET statement_timeout = {DB_STATEMENT_TIMEOUT}")
        cursor.close()


class DatabaseManager:
    """Manager for SQLAlchemy AsyncEngine and AsyncSession factory."""

    def __init__(self) -> None:  # noqa: D107
        self.engine: AsyncEngine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=cfg.DB_POOL_SIZE,
            max_overflow=cfg.DB_MAX_OVERFLOW,
            connect_args={
                "timeout": DB_CONNECTION_TIMEOUT,
                "statement_cache_size": 0,
            },
        )
        _attach_statement_timeout(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=SQLModelAsyncSession,
            expire_on_commit=False,
        )

    async def verify_connection(self) -> None:
        """Run a lightweight query to validate DB connectivity."""
        try:
            db_logger.debug("Checking database connection")
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            db_logger.info("Connection verified successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to database: {e}") from e


@lru_cache(maxsize=1)
def get_database_manager() -> DatabaseManager:
    """Return a cached DatabaseManager instance to avoid import-time side effects."""
    return DatabaseManager()


def SessionFactory() -> SQLModelAsyncSession:
    """Compatibility wrapper returning an AsyncSession instance when called.

    Tests and other modules call `SessionFactory()` to get a new session.
    """
    return get_database_manager().session_factory()


async def session() -> AsyncGenerator[SQLModelAsyncSession, None]:
    """Use as a dependency to provide an async database session to the route"""
    async_session = SessionFactory()

    # Runs after session flush and retains the state of the objects
    # https://docs.sqlalchemy.org/en/20/orm/events.html#sqlalchemy.orm.SessionEvents.after_flush
    @event.listens_for(async_session.sync_session, "after_flush")
    def after_flush(session: Session, _flushcontext: UOWTransaction) -> None:
        added = session.new
        deleted = session.deleted
        modified = session.dirty

        for obj in added:
            db_logger.info("CREATE %s", obj.__class__.__name__)
        for obj in deleted:
            db_logger.info("DELETE %s", obj.__class__.__name__)
        for obj in modified:
            db_logger.info("UPDATE %s", obj.__class__.__name__)

    try:
        yield async_session
    except Exception as e:
        await async_session.rollback()
        _handle_db_exception(e)
    finally:
        await async_session.close()


def _handle_db_exception(e: Exception) -> None:
    """Handle database exceptions and raise appropriate HTTP exceptions"""
    # Pass through existing AppExceptions
    if isinstance(e, AppException):
        raise e

    # Query timeout (504 Gateway Timeout)
    if isinstance(e, TimeoutError) or (isinstance(e, OperationalError) and "statement timeout" in str(e).lower()):
        db_logger.error("Database query timed out: %s", e, exc_info=True)
        raise AppException(
            status_code=504,
            error_code=AppErrorCode.DATABASE_TIMEOUT,
            detail="Database query timed out",
        ) from e

    # Database availability issues (503 Service Unavailable)
    if isinstance(e, OperationalError):
        db_logger.error("Database unavailable: %s", e, exc_info=True)
        raise AppException(
            status_code=503,
            error_code=AppErrorCode.DATABASE_UNAVAILABLE,
            detail="Database currently unavailable",
        ) from e

    # Client errors (400 Bad Request) — do NOT leak raw
    # constraint names or column details to the client.
    if isinstance(e, DBAPIError | ValueError):
        db_logger.warning("Database constraint violation: %s", e)
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.INVALID_INPUT,
            detail="Invalid data: a database constraint was violated",
        ) from e

    # Unexpected errors
    if DEBUG:
        raise e

    db_logger.error("Database error: %s", e, exc_info=True)
    raise AppException(
        status_code=500,
        error_code=AppErrorCode.INTERNAL_ERROR,
        detail="An unexpected database error occurred",
    ) from e


# Actual Dependency to use in endpoints
Database = Annotated[SQLModelAsyncSession, Depends(session)]
