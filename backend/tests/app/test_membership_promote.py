"""Tests for membership promotion business logic.

Verifies that guest-to-permanent promotion works for other
members but is blocked when a user tries to promote themselves.
"""

from __future__ import annotations

import pytest
from core.app_exception import AppException
from factories import models as f
from models.enums import AppErrorCode, Permission
from models.tables import Membership
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession


async def _setup_group_with_sharelink(
    db: SQLModelAsyncSession,
) -> dict:
    """Create a group, owner, share link, and a guest admin via the link.

    The guest is given ADMINISTRATOR permissions through the share link
    so the permission guard would pass in a real request.  The tests
    invoke the core promotion logic directly.
    """
    owner = await db.run_sync(lambda s: f.UserFactory())
    guest = await db.run_sync(lambda s: f.UserFactory())
    group = await db.run_sync(lambda s: f.GroupFactory())

    await db.run_sync(
        lambda s: f.MembershipFactory(
            user=owner,
            group=group,
            is_owner=True,
            accepted=True,
        )
    )

    share_link = await db.run_sync(
        lambda s: f.ShareLinkFactory(
            group=group,
            created_by=owner,
            permissions=[Permission.ADMINISTRATOR],
        )
    )

    await db.run_sync(
        lambda s: f.MembershipFactory(
            user=guest,
            group=group,
            permissions=[Permission.ADMINISTRATOR],
            accepted=True,
            share_link=share_link,
        )
    )

    await db.flush()

    return {
        "owner": owner,
        "guest": guest,
        "group": group,
        "share_link": share_link,
    }


async def test_self_promotion_blocked(
    db: SQLModelAsyncSession,
) -> None:
    """A guest admin must not be able to promote themselves."""
    from api.routers.memberships import promote_guest_to_member

    data = await _setup_group_with_sharelink(db)

    with pytest.raises(AppException) as exc_info:
        await promote_guest_to_member(
            db=db,
            session_user=data["guest"],
            group=data["group"],
            member=data["guest"],
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == AppErrorCode.CANNOT_PROMOTE_SELF

    # Verify the membership still has the share link
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == data["group"].id,
            Membership.user_id == data["guest"].id,
        )
    )
    membership = result.first()
    assert membership is not None
    assert membership.sharelink_id == data["share_link"].id


async def test_promote_other_member_succeeds(
    db: SQLModelAsyncSession,
) -> None:
    """An admin should be able to promote another guest member."""
    from api.routers.memberships import promote_guest_to_member

    data = await _setup_group_with_sharelink(db)

    response = await promote_guest_to_member(
        db=db,
        session_user=data["owner"],
        group=data["group"],
        member=data["guest"],
    )

    assert response.status_code == 204

    # Verify the membership no longer has a share link
    await db.refresh(
        (
            await db.exec(
                select(Membership).where(
                    Membership.group_id == data["group"].id,
                    Membership.user_id == data["guest"].id,
                )
            )
        ).first()
    )
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == data["group"].id,
            Membership.user_id == data["guest"].id,
        )
    )
    membership = result.first()
    assert membership is not None
    assert membership.sharelink_id is None
