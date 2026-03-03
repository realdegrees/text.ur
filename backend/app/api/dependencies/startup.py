import asyncio

import psycopg2
import redis
import redis.asyncio as aioredis
from api.dependencies.database import get_database_manager
from api.dependencies.events import get_event_manager
from api.dependencies.mail import get_mail_manager
from api.dependencies.storage import get_storage_manager
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

    # Redis - verify all three databases (0=events, 1=rate-limit, 2=cache)
    redis_dbs = {0: "events", 1: "rate-limit", 2: "cache"}
    for db_num, db_label in redis_dbs.items():
        try:
            app_logger.debug(
                "Checking Redis db %d (%s) connection (sync)",
                db_num,
                db_label,
            )
            r = redis.Redis(
                host=cfg.REDIS_HOST,
                port=cfg.REDIS_PORT,
                password=cfg.REDIS_PASSWORD,
                db=db_num,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            r.ping()
            r.close()
            app_logger.info(
                "Redis db %d (%s) verified (sync)", db_num, db_label
            )
        except Exception as e:
            app_logger.error(
                "Redis db %d (%s) verification failed (sync): %s",
                db_num,
                db_label,
                e,
            )
            raise RuntimeError(
                f"Failed to connect to Redis db {db_num}"
                f" ({db_label}): {e}"
            ) from e

    # Storage - validate configuration by instantiating
    try:
        app_logger.debug("Validating storage configuration")
        get_storage_manager()
        app_logger.info("Storage configuration validated")
    except Exception as e:
        app_logger.error("Storage configuration validation failed: %s", e)
        raise RuntimeError(f"Storage configuration invalid: {e}") from e

    # Mail - validate configuration, then attempt connection
    # Config errors (missing vars, bad credentials) are fatal.
    # Network errors (SMTP port blocked) are non-fatal — the app
    # boots and email content is logged on send attempts.
    try:
        app_logger.debug("Validating Mail configuration")
        mail_manager = get_mail_manager()
        app_logger.info("Mail configuration validated")
    except Exception as e:
        app_logger.error("Mail configuration validation failed: %s", e)
        raise RuntimeError(f"Mail configuration invalid: {e}") from e

    if not mail_manager.verify_connection():
        app_logger.warning(
            "SMTP server unreachable — email sending will"
            " be unavailable. Email content will be logged"
            " on send attempts for manual recovery."
        )

    app_logger.info("All dependencies verified successfully (sync)")


async def verify_all_dependencies_async() -> dict:
    """Verify all critical external dependencies.

    Args:
        strict: If True, this function raises on diagnostic failures that
            should abort startup (DB/Storage/Redis). The Mail dependency
            may return False for missing or debug-disabled SMTP; the
            function treats that as non-fatal unless it raises an
            exception.
        The function will create manager instances (e.g. StorageManager,
        EmailManager) and return them for reuse. If strict is True, any
        verification failure will raise and should abort startup.

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

    # Storage
    try:
        result["storage_manager"] = get_storage_manager()
    except Exception:
        app_logger.error("Storage verification failed")
        raise

    # Mail
    try:
        result["mail_manager"] = get_mail_manager()
    except Exception:
        # If strict, treat mail verification failure as fatal; otherwise keep going
        app_logger.error("Mail verification failed")
        raise

    # Redis (Event manager — db 0)
    try:
        event_manager = get_event_manager()
        await event_manager.check_connection()
        result["event_manager"] = event_manager
    except Exception:
        app_logger.error("Redis db 0 (events) verification failed")
        raise

    # Redis — verify db 1 (rate-limit) and db 2 (cache)
    for db_num, db_label in {1: "rate-limit", 2: "cache"}.items():
        try:
            r = aioredis.Redis(
                host=cfg.REDIS_HOST,
                port=cfg.REDIS_PORT,
                password=cfg.REDIS_PASSWORD,
                db=db_num,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await r.ping()
            await r.aclose()
            app_logger.info(
                "Redis db %d (%s) verified", db_num, db_label
            )
        except Exception:
            app_logger.error(
                "Redis db %d (%s) verification failed",
                db_num,
                db_label,
            )
            raise

    app_logger.info("All dependencies verified successfully")
    return result


def verify_all_dependencies() -> dict:
    """Run `verify_all_dependencies_async` synchronously and return the results."""
    return asyncio.run(verify_all_dependencies_async())
