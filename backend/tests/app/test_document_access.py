from __future__ import annotations

import pytest
from factories import models as f
from models.enums import Permission, Visibility
from models.tables import Group
from sqlmodel import Session
from util.queries import Guard


@pytest.mark.parametrize(
    "require_permissions, is_owner, is_admin, has_view_restricted, has_required_perm, accepted, visibility, expected",
    [
        # No required permissions: PRIVATE
        (None, False, False, False, False, True, Visibility.PRIVATE, False),
        (None, True, False, False, False, True, Visibility.PRIVATE, True),
        (None, False, True, False, False, True, Visibility.PRIVATE, True),

        # No required permissions: RESTRICTED
        (None, False, False, False, False, True, Visibility.RESTRICTED, False),
        (None, False, False, True, False, True, Visibility.RESTRICTED, True),
        (None, True, False, False, False, True, Visibility.RESTRICTED, True),
        (None, False, True, False, False, True, Visibility.RESTRICTED, True),
        # Not accepted members shouldn't gain access to restricted docs even if they have perm
        (None, False, False, True, False, False, Visibility.RESTRICTED, False),

        # No required permissions: PUBLIC
        (None, False, False, False, False, True, Visibility.PUBLIC, True),
        (None, False, False, False, False, False, Visibility.PUBLIC, False),
        (None, False, False, False, True, True, Visibility.PUBLIC, True),  # has extra perm irrelevant when no require

        # With required permission (ADD_DOCUMENTS)
        ({Permission.ADD_DOCUMENTS}, False, False, False, False, True, Visibility.PUBLIC, False),
        ({Permission.ADD_DOCUMENTS}, False, False, False, True, True, Visibility.PUBLIC, True),
        ({Permission.ADD_DOCUMENTS}, False, True, False, False, True, Visibility.PUBLIC, True),

        # With required permission: RESTRICTED
        ({Permission.ADD_DOCUMENTS}, False, False, False, False, True, Visibility.RESTRICTED, False),
        ({Permission.ADD_DOCUMENTS}, False, False, False, True, True, Visibility.RESTRICTED, False),
            # If ADD_DOCUMENTS is required, VIEW_RESTRICTED_DOCUMENTS alone should not grant access
            ({Permission.ADD_DOCUMENTS}, False, False, True, False, True, Visibility.RESTRICTED, False),
        ({Permission.ADD_DOCUMENTS}, True, False, False, False, True, Visibility.RESTRICTED, True),
        ({Permission.ADD_DOCUMENTS}, False, True, False, False, True, Visibility.RESTRICTED, True),
        # With required permission (ADD_COMMENTS) - ensure behaviour matches expectations for comments
        ({Permission.ADD_COMMENTS}, False, False, False, False, True, Visibility.PUBLIC, False),
        ({Permission.ADD_COMMENTS}, False, False, False, True, True, Visibility.PUBLIC, True),
        ({Permission.ADD_COMMENTS}, False, True, False, False, True, Visibility.PUBLIC, True),

        # With required permission (ADD_COMMENTS): RESTRICTED
        ({Permission.ADD_COMMENTS}, False, False, False, False, True, Visibility.RESTRICTED, False),
        ({Permission.ADD_COMMENTS}, False, False, False, True, True, Visibility.RESTRICTED, False),
        # If ADD_COMMENTS is required, VIEW_RESTRICTED_DOCUMENTS alone should not grant access
        ({Permission.ADD_COMMENTS}, False, False, True, False, True, Visibility.RESTRICTED, False),
            # With require_permissions = VIEW_RESTRICTED_DOCUMENTS
            ({Permission.VIEW_RESTRICTED_DOCUMENTS}, False, False, True, False, True, Visibility.RESTRICTED, True),
            ({Permission.VIEW_RESTRICTED_DOCUMENTS}, False, False, False, False, True, Visibility.RESTRICTED, False),
        ({Permission.ADD_COMMENTS}, True, False, False, False, True, Visibility.RESTRICTED, True),
        ({Permission.ADD_COMMENTS}, False, True, False, False, True, Visibility.RESTRICTED, True),
    ],
)
def test_document_access_predicate_and_sql(db: Session, require_permissions: set[Permission] | None, is_owner: bool, is_admin: bool, has_view_restricted: bool, has_required_perm: bool, accepted: bool, visibility: Visibility, expected: bool) -> None:
    """Test `Guard.document_access` predicate and SQL clause with a parameter matrix.

    This mirrors the structure of `test_comment_access.py` using factories and
    verifying both the Python predicate and the SQLAlchemy clause.
    """
    # Create users
    owner = f.UserFactory()
    viewer = f.UserFactory()

    # Create group and document
    group = f.GroupFactory()
    document = f.DocumentFactory(group=group, visibility=visibility)

    # Create ownership/membership for owner and viewer
    # Owner membership: ensure the owner has a membership and is_owner flag
    f.MembershipFactory(user=owner, group=group, is_owner=True, accepted=True)

    # Build viewer permissions
    perms = []
    if is_admin:
        perms.append(Permission.ADMINISTRATOR)
    if has_view_restricted:
        perms.append(Permission.VIEW_RESTRICTED_DOCUMENTS)
    if has_required_perm:
        # When we're indicating the test subject has the required permission,
        # add whichever permission(s) are in `require_permissions` to the
        # membership; otherwise fall back to ADD_DOCUMENTS for older test rows
        if require_permissions:
            perms.extend(list(require_permissions))
        else:
            perms.append(Permission.ADD_DOCUMENTS)

    # Create viewer membership (respect the paramized is_owner flag)
    f.MembershipFactory(user=viewer, group=group, permissions=perms, accepted=accepted, is_owner=is_owner)

    # Assign group memberships/relationships for predicate
    from models.tables import Membership
    from sqlmodel import select

    db.flush()
    memberships = db.exec(select(Membership).where(Membership.group_id == group.id)).all()
    group.memberships = list(memberships)
    document.group = group

    guard = Guard.document_access(require_permissions if require_permissions is None else set(require_permissions))

    # Predicate test
    pred_result = guard.predicate(document, viewer)
    assert pred_result is expected

    # SQL test (clause executed against db)
    clause = guard.clause(viewer, {"document_id": document.id}, multi=False)
    sql_result = db.exec(__import__("sqlmodel").select(clause)).one()
    assert sql_result is expected
