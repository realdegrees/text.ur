"""Periodic cleanup tasks for GDPR-compliant data retention.

Runs as an asyncio background task spawned in the application
lifespan.  Handles:
- Log file retention (default 90 days)
- Abandoned guest account removal
- Unverified account removal
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime, timedelta

from core import config
from core.logger import get_logger

logger = get_logger("app")


def _cleanup_old_logs() -> int:
    """Delete rotated log files older than ``LOG_RETENTION_DAYS``.

    Returns the number of files removed.
    """
    log_dir = config.LOG_FILE_DIR or os.path.join(config.backend_path, "logs")
    if not os.path.isdir(log_dir):
        return 0

    cutoff = time.time() - (config.LOG_RETENTION_DAYS * 86400)
    removed = 0

    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir, filename)
        if not os.path.isfile(filepath):
            continue
        # Only touch .log files and their rotated backups (.log.1 etc.)
        if not filename.endswith(".log") and ".log." not in filename:
            continue
        try:
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                removed += 1
        except OSError:
            logger.warning("Failed to remove old log file: %s", filepath)

    return removed


async def _cleanup_abandoned_guests() -> int:
    """Delete guest accounts older than ``GUEST_ACCOUNT_TTL_DAYS``.

    Once the refresh-token cookie expires the account is
    permanently inaccessible.  CASCADE deletes handle related rows.

    Returns the number of accounts removed.
    """
    # Lazy imports to avoid circular dependencies at module load time
    from api.dependencies.database import SessionFactory
    from models.tables import User
    from sqlmodel import select

    cutoff = datetime.now(UTC) - timedelta(
        days=config.GUEST_ACCOUNT_TTL_DAYS,
    )

    async with SessionFactory() as db:
        result = await db.exec(
            select(User).where(
                User.is_guest.is_(True),
                User.created_at < cutoff,
            )
        )
        guests = list(result.all())

        for guest in guests:
            await db.delete(guest)

        if guests:
            await db.commit()

    return len(guests)


async def _cleanup_unverified_accounts() -> int:
    """Delete non-guest accounts that were never verified.

    Accounts older than ``REGISTER_LINK_EXPIRY_DAYS`` whose email
    was never confirmed are abandoned registrations.

    Returns the number of accounts removed.
    """
    from api.dependencies.database import SessionFactory
    from models.tables import User
    from sqlmodel import select

    cutoff = datetime.now(UTC) - timedelta(
        days=config.REGISTER_LINK_EXPIRY_DAYS,
    )

    async with SessionFactory() as db:
        result = await db.exec(
            select(User).where(
                User.verified.is_(False),
                User.is_guest.is_(False),
                User.created_at < cutoff,
            )
        )
        users = list(result.all())

        for user in users:
            await db.delete(user)

        if users:
            await db.commit()

    return len(users)


async def periodic_cleanup_loop(
    interval_hours: float,
) -> None:
    """Run all cleanup tasks on a recurring interval.

    Executes immediately on first call, then sleeps for
    *interval_hours* between runs.  All exceptions are caught
    and logged so the loop never dies unexpectedly.
    """
    while True:
        try:
            logger.info("[Cleanup] Starting periodic cleanup cycle")

            removed_logs = _cleanup_old_logs()
            if removed_logs:
                logger.info(
                    "[Cleanup] Removed %d old log file(s)", removed_logs
                )

            removed_guests = await _cleanup_abandoned_guests()
            if removed_guests:
                logger.info(
                    "[Cleanup] Removed %d abandoned guest account(s)",
                    removed_guests,
                )

            removed_unverified = await _cleanup_unverified_accounts()
            if removed_unverified:
                logger.info(
                    "[Cleanup] Removed %d unverified account(s)",
                    removed_unverified,
                )

            logger.info("[Cleanup] Cleanup cycle complete")

        except Exception:
            logger.exception("[Cleanup] Error during cleanup cycle")

        await asyncio.sleep(interval_hours * 3600)
