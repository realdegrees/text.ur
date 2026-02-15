import asyncio

import psycopg2
import redis
from api.dependencies.database import get_database_manager
from api.dependencies.events import get_event_manager
from api.dependencies.mail import get_mail_manager
from api.dependencies.s3 import get_s3_manager
from core import config as cfg
from core.logger import get_logger

app_logger = get_logger("app")


def verify_all_dependencies_sync() -> None:
    """Verify critical dependencies using synchronous operations.
    
    This function is designed to run in the Gunicorn master process before
    forking workers. It performs lightweight checks to ensure critical services
    are reachable without creating async event loops that would conflict with
    worker event loops.
    """
    # Database - use psycopg2 for synchronous connection test
    try:
        app_logger.debug("Checking database connection (sync)")
        conn = psycopg2.connect(
            host=cfg.PGBOUNCER_HOST or cfg.POSTGRES_HOST,
            port=cfg.PGBOUNCER_PORT or cfg.POSTGRES_PORT,
            user=cfg.POSTGRES_USER,
            password=cfg.POSTGRES_PASSWORD,
            database=cfg.POSTGRES_DB,
            connect_timeout=5,
        )
        conn.close()
        app_logger.info("Database connection verified (sync)")
    except Exception as e:
        app_logger.error("Database verification failed (sync): %s", e)
        raise RuntimeError(f"Failed to connect to database: {e}") from e

    # Redis - use sync redis client
    try:
        app_logger.debug("Checking Redis connection (sync)")
        r = redis.Redis(
            host=cfg.REDIS_HOST,
            port=cfg.REDIS_PORT,
            password=cfg.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        r.ping()
        app_logger.info("Redis connection verified (sync)")
    except Exception as e:
        app_logger.error("Redis verification failed (sync): %s", e)
        raise RuntimeError(f"Failed to connect to Redis: {e}") from e

    # S3 - just validate configuration by instantiating
    try:
        app_logger.debug("Validating S3 configuration")
        get_s3_manager()
        app_logger.info("S3 configuration validated")
    except Exception as e:
        app_logger.error("S3 configuration validation failed: %s", e)
        raise RuntimeError(f"S3 configuration invalid: {e}") from e

    # Mail - just validate configuration by instantiating
    try:
        app_logger.debug("Validating Mail configuration")
        get_mail_manager()
        app_logger.info("Mail configuration validated")
    except Exception as e:
        app_logger.error("Mail configuration validation failed: %s", e)
        raise RuntimeError(f"Mail configuration invalid: {e}") from e

    app_logger.info("All dependencies verified successfully (sync)")


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
        await db_manager.verify_connection()
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