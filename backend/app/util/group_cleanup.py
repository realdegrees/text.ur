"""Helpers for deleting a group and cleaning up its S3 objects.

Shared by the group-deletion and user-deletion endpoints so the
logic isn't duplicated.
"""

from logging import Logger

from api.dependencies.s3 import S3Manager
from models.tables import Document, Group
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


async def prepare_group_deletion(
    db: AsyncSession,
    group_id: int,
) -> list[str]:
    """Stage a group for deletion and return its S3 keys.

    Collects every ``Document.s3_key`` that belongs to *group_id*,
    then marks the :class:`Group` for deletion on the current
    session.  The caller is responsible for calling ``db.commit()``
    at the appropriate time.

    Returns the list of S3 object keys that should be removed
    **after** the commit succeeds.
    """
    result = await db.exec(
        select(Document.s3_key).where(
            Document.group_id == group_id
        )
    )
    s3_keys: list[str] = list(result.all())

    result = await db.exec(
        select(Group).where(Group.id == group_id)
    )
    group = result.one()
    await db.delete(group)

    return s3_keys


def cleanup_s3_keys(
    s3: S3Manager,
    keys: list[str],
    logger: Logger,
    context: str,
) -> None:
    """Best-effort removal of S3 objects after a successful commit.

    *context* is a human-readable label included in warning messages
    (e.g. ``"group 42"`` or ``"user 7 account deletion"``).
    """
    for key in keys:
        if not s3.delete(key):
            logger.warning(
                "Failed to delete S3 object %s during %s",
                key,
                context,
            )
