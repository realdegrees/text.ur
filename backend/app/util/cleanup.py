"""Periodic cleanup tasks for GDPR-compliant data retention.

Runs as an asyncio background task spawned in the application
lifespan.  Handles:
- Log file retention (default 90 days)
- Abandoned guest account removal
- Unverified account removal
- Orphaned storage file removal

Each sub-task acquires its own PostgreSQL advisory lock so that
only one worker executes it at a time, while independent tasks
can run in parallel across different workers.

Advisory locks connect directly to PostgreSQL (bypassing
PgBouncer) via the dedicated engine in ``advisory_lock``.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime, timedelta

from core import config
from core.logger import get_logger
from util.advisory_lock import (
    LOCK_CLEANUP_GUESTS,
    LOCK_CLEANUP_LOGS,
    LOCK_CLEANUP_ORPHANED_FILES,
    LOCK_CLEANUP_UNVERIFIED,
    advisory_lock,
)

logger = get_logger("app")


async def _cleanup_old_logs() -> int:
    """Delete rotated log files older than ``LOG_RETENTION_DAYS``.

    Returns the number of files removed.
    """
    async with advisory_lock(LOCK_CLEANUP_LOGS) as acquired:
        if not acquired:
            return 0

        log_dir = config.LOG_FILE_DIR or os.path.join(config.backend_path, "logs")
        if not os.path.isdir(log_dir):
            return 0

        cutoff = time.time() - (config.LOG_RETENTION_DAYS * 86400)
        removed = 0

        for filename in os.listdir(log_dir):
            filepath = os.path.join(log_dir, filename)
            if not os.path.isfile(filepath):
                continue
            # Only touch .log files and their rotated backups
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
    async with advisory_lock(LOCK_CLEANUP_GUESTS) as acquired:
        if not acquired:
            return 0

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
    async with advisory_lock(LOCK_CLEANUP_UNVERIFIED) as acquired:
        if not acquired:
            return 0

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


async def _cleanup_orphaned_files() -> int:
    """Delete storage files that have no matching ``Document`` row.

    Only files whose modification time is older than 24 hours are
    considered orphaned — recently created files may belong to an
    in-flight upload that has not yet been committed to the DB.

    Returns the number of files removed.
    """
    async with advisory_lock(LOCK_CLEANUP_ORPHANED_FILES) as acquired:
        if not acquired:
            return 0

        from api.dependencies.database import SessionFactory
        from api.dependencies.storage import get_storage_manager
        from models.tables import Document
        from sqlmodel import select

        storage = get_storage_manager()
        cutoff = time.time() - 86400  # 24 hours ago

        # Collect all storage keys that exist in the database.
        async with SessionFactory() as db:
            result = await db.exec(select(Document.storage_key))
            known_keys: set[str] = set(result.all())

        removed = 0
        for key in storage.list_keys():
            if key in known_keys:
                continue

            # Only remove files older than the safety threshold
            # to avoid deleting in-flight uploads.
            file_path = storage._path(key)
            try:
                if os.path.getmtime(file_path) > cutoff:
                    continue
            except OSError:
                continue

            if storage.delete(key):
                removed += 1
                logger.info("[Cleanup] Deleted orphaned file: %s", key)

        return removed


async def periodic_cleanup_loop(
    interval_hours: float,
) -> None:
    """Run all cleanup tasks on a recurring interval.

    Executes immediately on first call, then sleeps for
    *interval_hours* between runs.  All exceptions are caught
    and logged so the loop never dies unexpectedly.

    Each sub-task acquires its own advisory lock so it runs in
    only one worker at a time.
    """
    while True:
        try:
            logger.info("[Cleanup] Starting periodic cleanup cycle")

            removed_logs = await _cleanup_old_logs()
            if removed_logs:
                logger.info(
                    "[Cleanup] Removed %d old log file(s)",
                    removed_logs,
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

            removed_orphans = await _cleanup_orphaned_files()
            if removed_orphans:
                logger.info(
                    "[Cleanup] Removed %d orphaned storage file(s)",
                    removed_orphans,
                )

            logger.info("[Cleanup] Cleanup cycle complete")

        except Exception:
            logger.exception("[Cleanup] Error during cleanup cycle")

        await asyncio.sleep(interval_hours * 3600)
