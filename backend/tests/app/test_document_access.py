from __future__ import annotations

import pytest
from factories import models as f
from models.enums import DocumentVisibility, Permission
from models.tables import Group
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession
from util.queries import Guard


@pytest.mark.parametrize(
    "require_permissions, is_owner, is_admin, has_required_perm, accepted, visibility, expected",
    [
        # No required permissions: PRIVATE (only owner/admin can access)
        (None, False, False, False, True, DocumentVisibility.PRIVATE, False),
        (None, True, False, False, True, DocumentVisibility.PRIVATE, True),
        (None, False, True, False, True, DocumentVisibility.PRIVATE, True),

        # No required permissions: PUBLIC (any accepted member can access)
        (None, False, False, False, True, DocumentVisibility.PUBLIC, True),
        (None, False, False, False, False, DocumentVisibility.PUBLIC, False),
        (None, False, False, True, True, DocumentVisibility.PUBLIC, True),  # has extra perm irrelevant when no require

        # With required permission (ADD_COMMENTS) on PUBLIC docs
        ({Permission.ADD_COMMENTS}, False, False, False, True, DocumentVisibility.PUBLIC, False),
        ({Permission.ADD_COMMENTS}, False, False, True, True, DocumentVisibility.PUBLIC, True),
        ({Permission.ADD_COMMENTS}, False, True, False, True, DocumentVisibility.PUBLIC, True),

        # With required permission on PRIVATE docs (only admin/owner)
        ({Permission.ADD_COMMENTS}, False, False, False, True, DocumentVisibility.PRIVATE, False),
        ({Permission.ADD_COMMENTS}, False, False, True, True, DocumentVisibility.PRIVATE, False),
        ({Permission.ADD_COMMENTS}, True, False, False, True, DocumentVisibility.PRIVATE, True),
        ({Permission.ADD_COMMENTS}, False, True, False, True, DocumentVisibility.PRIVATE, True),
    ],
)
async def test_document_access_predicate_and_sql(
    db: SQLModelAsyncSession,
    require_permissions: set[Permission] | None,
    is_owner: bool,
    is_admin: bool,
    has_required_perm: bool,
    accepted: bool,
    visibility: DocumentVisibility,
    expected: bool,
) -> None:
    """Test `Guard.document_access` predicate and SQL clause with a parameter matrix."""
    owner = await db.run_sync(lambda session: f.UserFactory())
    viewer = await db.run_sync(lambda session: f.UserFactory())

    group = await db.run_sync(lambda session: f.GroupFactory())
    document = await db.run_sync(
        lambda session: f.DocumentFactory(group=group, visibility=visibility)
    )

    await db.run_sync(
        lambda session: f.MembershipFactory(
            user=owner, group=group, is_owner=True, accepted=True
        )
    )

    perms = []
    if is_admin:
        perms.append(Permission.ADMINISTRATOR)
    if has_required_perm and require_permissions:
        perms.extend(list(require_permissions))

    await db.run_sync(
        lambda session: f.MembershipFactory(
            user=viewer,
            group=group,
            permissions=perms,
            accepted=accepted,
            is_owner=is_owner,
        )
    )

    from models.tables import Membership

    await db.flush()
    memberships = (
        await db.exec(select(Membership).where(Membership.group_id == group.id))
    ).all()
    group.memberships = list(memberships)
    document.group = group

    guard = Guard.document_access(
        require_permissions if require_permissions is None else set(require_permissions)
    )

    pred_result = guard.predicate(document, viewer)
    assert pred_result is expected

    clause = guard.clause(viewer, {"document_id": document.id}, multi=False)
    sql_result = (await db.exec(select(clause))).one()
    assert sql_result is expected
