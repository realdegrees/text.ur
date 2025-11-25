from __future__ import annotations

from typing import Any

import pytest
from factories import models as f
from models.enums import Permission, ViewMode, Visibility
from models.tables import Group
from sqlmodel import Session
from util.queries import Guard


@pytest.mark.parametrize(
    "user_has_perm, view_mode, comment_visibility, is_author, expected",
    [
        # user_has_perm False, document view_mode public
        (False, ViewMode.PUBLIC, Visibility.PUBLIC, False, True),
        (False, ViewMode.PUBLIC, Visibility.PUBLIC, True, True),
        (False, ViewMode.PUBLIC, Visibility.RESTRICTED, False, False),
        (False, ViewMode.PUBLIC, Visibility.RESTRICTED, True, True),
        (False, ViewMode.PUBLIC, Visibility.PRIVATE, False, False),
        (False, ViewMode.PUBLIC, Visibility.PRIVATE, True, True),

        # user_has_perm False, document view_mode restricted
        (False, ViewMode.RESTRICTED, Visibility.PUBLIC, False, False),
        (False, ViewMode.RESTRICTED, Visibility.PUBLIC, True, True),
        (False, ViewMode.RESTRICTED, Visibility.RESTRICTED, False, False),
        (False, ViewMode.RESTRICTED, Visibility.RESTRICTED, True, True),
        (False, ViewMode.RESTRICTED, Visibility.PRIVATE, False, False),
        (False, ViewMode.RESTRICTED, Visibility.PRIVATE, True, True),

        # user_has_perm True, document view_mode public
        (True, ViewMode.PUBLIC, Visibility.PUBLIC, False, True),
        (True, ViewMode.PUBLIC, Visibility.PUBLIC, True, True),
        (True, ViewMode.PUBLIC, Visibility.RESTRICTED, False, True),
        (True, ViewMode.PUBLIC, Visibility.RESTRICTED, True, True),
        (True, ViewMode.PUBLIC, Visibility.PRIVATE, False, False),
        (True, ViewMode.PUBLIC, Visibility.PRIVATE, True, True),

        # user_has_perm True, document view_mode restricted
        (True, ViewMode.RESTRICTED, Visibility.PUBLIC, False, True),
        (True, ViewMode.RESTRICTED, Visibility.PUBLIC, True, True),
        (True, ViewMode.RESTRICTED, Visibility.RESTRICTED, False, True),
        (True, ViewMode.RESTRICTED, Visibility.RESTRICTED, True, True),
        (True, ViewMode.RESTRICTED, Visibility.PRIVATE, False, False),
        (True, ViewMode.RESTRICTED, Visibility.PRIVATE, True, True),
    ],
)
def test_comment_access_predicate_and_sql(db: Session, user_has_perm: bool, view_mode: ViewMode, comment_visibility: Visibility, is_author: bool, expected: bool) -> None:
    """Test the comment_access predicate and SQL clause against the truth table.

    We create a group + document + comment, add memberships for an author and
    the viewer and adjust permissions according to the parametrization.
    """
    # Create users
    author = f.UserFactory()
    viewer = f.UserFactory()

    # Create group and document
    group = f.GroupFactory()
    document = f.DocumentFactory(group=group, view_mode=view_mode)

    # Create memberships for author and viewer
    # Author should always be a member and accepted
    f.MembershipFactory(user=author, group=group, is_owner=False, accepted=True)

    # Viewer membership accepted by default; add permission flag if required.
    perms = []
    if user_has_perm:
        perms = [Permission.VIEW_RESTRICTED_COMMENTS]

    f.MembershipFactory(user=viewer, group=group, permissions=perms, accepted=True)

    # Create the comment as either the viewer (if is_author=True) or another user
    # is_author indicates whether the viewer is the comment author
    comment_user = viewer if is_author else author
    comment = f.CommentFactory(document=document, user=comment_user, visibility=comment_visibility)

    # Ensure relationships are properly loaded for the predicate test
    # Manually load memberships from database and assign to group
    from models.tables import Membership
    from sqlmodel import select
    db.flush()

    # Query memberships directly
    memberships = db.exec(select(Membership).where(Membership.group_id == group.id)).all()
    group.memberships = list(memberships)
    document.group = group

    guard = Guard.comment_access()

    # Check python predicate
    pred_result = guard.predicate(comment, viewer)
    assert pred_result is expected

    # Check SQL clause - the clause is designed to be executed against the DB
    clause = guard.clause(viewer, {"comment_id": comment.id}, multi=False)
    # Clause is a boolean-select; selecting it should produce the equivalent truth value
    sql_result = db.exec(__import__("sqlmodel").select(clause)).one()
    assert sql_result is expected
