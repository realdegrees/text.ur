import asyncio

from api.dependencies.database import (
    get_database_manager,
)
from api.dependencies.events import get_event_manager
from api.dependencies.mail import get_mail_manager
from api.dependencies.s3 import get_s3_manager
from core.logger import get_logger

app_logger = get_logger("app")


 


async def verify_all_dependencies_async() -> dict:
    """Verify all critical external dependencies.

    Args:
        strict: If True, this function raises on diagnostic failures that
            should abort startup (DB/S3/Redis). The Mail dependency may
            return False for missing or debug-disabled SMTP; the function
            treats that as non-fatal unless it raises an exception.
        The function will create manager instances (e.g. S3Manager, EmailManager)
        and return them for reuse. If strict is True, any verification failure will
        raise and should abort startup.

    """
    # Database
    result: dict = {}
    try:
        # Instantiate DatabaseManager (ensures engine creation and verification)
        db_manager = get_database_manager()
        result["database_manager"] = db_manager
    except Exception:
        app_logger.error("Database verification failed")
        raise

    # S3
    try:
        result["s3_manager"] = get_s3_manager()
    except Exception:
        app_logger.error("S3 verification failed")
        raise

    # Mail
    try:
        result["mail_manager"] = get_mail_manager()
    except Exception:
        # If strict, treat mail verification failure as fatal; otherwise keep going
        app_logger.error("Mail verification failed")
        raise

    # Redis (Event manager)
    try:
        event_manager = get_event_manager()
        await event_manager.check_connection()
        result["event_manager"] = event_manager
    except Exception:
        app_logger.error("Redis verification failed")
        raise

    app_logger.info("All dependencies verified successfully")
    return result


def verify_all_dependencies() -> dict:
    """Run `verify_all_dependencies_async` synchronously and return the results."""
    return asyncio.run(verify_all_dependencies_async())