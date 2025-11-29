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
from fastapi import Depends, HTTPException
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import (
    DBAPIError,
    OperationalError,
    TimeoutError,  # noqa: A004
)
from sqlalchemy.orm import UOWTransaction, sessionmaker
from sqlmodel import Session, create_engine

app_logger = get_logger("app")
db_logger = get_logger("database")

if cfg.DEBUG:
    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

def _attach_statement_timeout(engine: Engine) -> None:
    """Attach a statement timeout listener to a SQLAlchemy engine.

    This is registered after the engine is created to avoid module import
    side-effects.
    """
    @event.listens_for(engine, "connect")
    def _set_statement_timeout(dbapi_conn, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET statement_timeout = {DB_STATEMENT_TIMEOUT}")
        cursor.close()
        
class DatabaseManager:
    """Manager for SQLAlchemy Engine and Session factory."""

    def __init__(self) -> None:  # noqa: D107
        self.engine: Engine = create_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"connect_timeout": DB_CONNECTION_TIMEOUT},
        )
        _attach_statement_timeout(self.engine)
        self.session_factory: sessionmaker = sessionmaker(bind=self.engine, class_=Session)
        # Verify connectivity eagerly
        self.verify_connection()

    def verify_connection(self) -> None:
        """Run a lightweight query to validate DB connectivity."""
        try:
            app_logger.debug("Checking database connection to %s", DATABASE_URL)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            app_logger.info("Database connection verified successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to database: {e}") from e



@lru_cache(maxsize=1)
def get_database_manager() -> DatabaseManager:
    """Return a cached DatabaseManager instance to avoid import-time side effects."""
    return DatabaseManager()

def SessionFactory() -> Session:
    """Compatibility wrapper returning a Session instance when called.

    Tests and other modules call `SessionFactory()` to get a new session.
    """
    return get_database_manager().session_factory()

async def session() -> AsyncGenerator[Session, None]:
    """Use as a dependency to provide a database session to the route"""
    session = SessionFactory()

    # Runs after session flush and retains the state of the objects
    # https://docs.sqlalchemy.org/en/20/orm/events.html#sqlalchemy.orm.SessionEvents.after_flush
    @event.listens_for(session, "after_flush")
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
        yield session
    except Exception as e:
        session.rollback()
        _handle_db_exception(e)
    finally:
        session.close()


def _handle_db_exception(e: Exception) -> None:
    """Handle database exceptions and raise appropriate HTTP exceptions"""
    # Pass through existing HTTP exceptions and AppExceptions
    if isinstance(e, (HTTPException, AppException)):
        raise e

    # Determine status code and message based on exception type
    status_code: int = 500  # Default to internal server error
    detail: str = "An unexpected database error occurred"

    # Query timeout (504 Gateway Timeout)
    if isinstance(e, TimeoutError):
        status_code = 504
        detail = "Database query timed out"
    # Check for statement_timeout in OperationalError (psycopg2 raises this for timeouts)
    elif isinstance(e, OperationalError) and "statement timeout" in str(e).lower():
        status_code = 504
        detail = "Database query timed out"
    # Database availability issues (503 Service Unavailable)
    elif isinstance(e, OperationalError):
        status_code = 503
        detail = "Database currently unavailable"
    # Client errors (400 Bad Request)
    elif isinstance(e, DBAPIError | ValueError):
        status_code = 400
        error_message = str(e).split('\n')[0]
        detail = f"Database constraint violation: {error_message}"

    # Log server errors for debugging
    if status_code >= 500:
        if DEBUG:
            raise e
        else:
            db_logger.error("Database error: %s", e, exc_info=True)

    raise HTTPException(status_code=status_code, detail=detail) from e


# Actual Dependency to use in endpoints
Database = Annotated[Session, Depends(session)]
