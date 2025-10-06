from collections.abc import AsyncGenerator
from typing import Annotated

import core.config as cfg
from core.config import DATABASE_URL, DEBUG
from core.logger import get_logger
from fastapi import Depends, HTTPException
from sqlalchemy import event
from sqlalchemy.exc import (
    DBAPIError,
    OperationalError,
)
from sqlalchemy.orm import UOWTransaction, sessionmaker
from sqlmodel import Session, create_engine

logger = get_logger("database")

if cfg.DEBUG:
    import logging
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    
# Create db connection
_engine = create_engine(
    DATABASE_URL,
    echo=DEBUG,
)

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
            logger.info(f"CREATE {obj.__class__.__name__}")
        for obj in deleted:
            logger.info(f"DELETE {obj.__class__.__name__}")
        for obj in modified:
            logger.info(f"UPDATE {obj.__class__.__name__}")

    try:
        yield session
    except Exception as e:
        session.rollback()
        _handle_db_exception(e)
    finally:
        session.close()


def _handle_db_exception(e: Exception) -> None:
    """Handle database exceptions and raise appropriate HTTP exceptions"""
    # Pass through existing HTTP exceptions
    if isinstance(e, HTTPException):
        raise e

    # Determine status code and message based on exception type
    status_code: int = 500  # Default to internal server error
    detail: str = "An unexpected database error occurred"

    # Client errors (400 Bad Request)
    if isinstance(e, DBAPIError | ValueError):
        status_code = 400
        error_message = str(e).split('\n')[0]
        detail = f"Database constraint violation: {error_message}"

    # Database availability issues (503 Service Unavailable)
    elif isinstance(e, OperationalError):
        status_code = 503
        detail = "Database currently unavailable"

    # Log server errors for debugging
    if status_code >= 500:
        if DEBUG:
            raise e
        else:
            logger.error(f"Database error: {e}")

    raise HTTPException(status_code=status_code, detail=detail) from e


# Actual Dependency to use in endpoints
Database = Annotated[Session, Depends(session)]
