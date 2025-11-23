from collections.abc import AsyncGenerator
from typing import Annotated

import core.config as cfg
from core.config import (
    DATABASE_URL,
    DB_CONNECTION_TIMEOUT,
    DB_STATEMENT_TIMEOUT,
    DEBUG,
)
from core.app_exception import AppException
from core.logger import get_logger
from fastapi import Depends, HTTPException
from sqlalchemy import event, text
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

# Create db connection with timeout settings
_engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=300,  # Recycle connections after 5 minutes
    connect_args={
        "connect_timeout": DB_CONNECTION_TIMEOUT,
    },
)


# Set statement_timeout when connection is checked out from pool
@event.listens_for(_engine, "connect")
def set_statement_timeout(dbapi_conn, connection_record) -> None:  # noqa: ANN001
    """Set statement timeout for each new database connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute(f"SET statement_timeout = {DB_STATEMENT_TIMEOUT}")
    cursor.close()


def verify_database_connection() -> None:
    """Verify database connection at startup. Raises exception if connection fails."""
    try:
        app_logger.debug("Checking database connection to %s", DATABASE_URL)
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        app_logger.info("Database connection verified successfully")
    except Exception as e:
        app_logger.error("Database connection failed: %s", e)
        raise RuntimeError(f"Failed to connect to database: {e}") from e


SessionFactory = sessionmaker(bind=_engine, class_=Session)

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
