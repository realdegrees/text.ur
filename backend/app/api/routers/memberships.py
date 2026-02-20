from datetime import UTC, datetime

from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.paginated.resources import (
    PaginatedResource,
)
from api.dependencies.resource import Resource
from core.app_exception import AppException
from fastapi import Body, HTTPException, Query, Response
from models.enums import AppErrorCode, Permission
from models.filter import MembershipFilter
from models.group import (
    MembershipCreate,
    MembershipPermissionUpdate,
    MembershipRead,
)
from models.pagination import Paginated
from models.score import (
    ReactionBreakdownItem,
    ScoreBreakdown,
    ScoreRead,
)
from models.tables import (
    Comment,
    CommentTag,
    Document,
    Group,
    GroupReaction,
    Membership,
    Reaction,
    ScoreConfig,
    User,
)
from sqlalchemy import case, func, or_
from sqlmodel import select
from util.api_router import APIRouter
from util.cache import get_cached, score_cache_key, set_cached
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

groupmembership_router = APIRouter(
    tags=["Memberships"],
)

membership_router = APIRouter(
    prefix="/memberships",
    tags=["Memberships"],
)


@membership_router.get(
    "/",
    response_model=Paginated[MembershipRead],
    response_class=ExcludableFieldsJSONResponse,
)
async def list_memberships(
    _: User = Authenticate(),
    memberships: Paginated[Membership] = PaginatedResource(
        Membership,
        MembershipFilter,
        key_columns=[Membership.user_id, Membership.group_id],
        guards=[Guard.group_access()],
    ),
) -> Paginated[MembershipRead]:
    """Get all group memberships. By default only returns memberships for groups the user is a member of."""
    return memberships


@groupmembership_router.get("/{user_id}", response_model=MembershipRead)
async def get_membership(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access()],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
    member: User = Resource(User, param_alias="user_id"),
) -> MembershipRead:
    """Get a specific group membership."""
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == member.id,
        )
    )
    membership: Membership | None = result.first()

    if not membership:
        raise HTTPException(
            status_code=404, detail="Target user is not a member of this group"
        )

    return membership


@groupmembership_router.post("/")
async def invite_member(
    db: Database,
    group: Group = Resource(Group, param_alias="group_id"),
    _: User = Authenticate([Guard.group_access({Permission.ADD_MEMBERS})]),
    membership_create: MembershipCreate = Body(...),
) -> Response:
    """Create a new membership."""
    # Check if user exists and is not already a member
    result = await db.exec(
        select(User, Membership)
        .outerjoin(
            Membership,
            (Membership.user_id == User.id) & (Membership.group_id == group.id),
        )
        .where(User.id == membership_create.user_id)
    )
    user, membership = result.first() or (None, None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if membership:
        raise HTTPException(
            status_code=400, detail="User is already a member of this group"
        )

    # TODO: Send an email notification to the user about the invite (just link to the frontend dashboard group page and accept on load if the query param accept is present)

    # Create new membership
    membership_create = Membership(
        user_id=membership_create.user_id,
        group_id=group.id,
        permissions=group.default_permissions,
        is_owner=False,
        accepted=False,
    )
    db.add(membership_create)
    await db.commit()
    await db.refresh(membership_create)
    return Response(status_code=201)


@groupmembership_router.put("/{user_id}/permissions")
async def update_member_permissions(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access({Permission.MANAGE_PERMISSIONS})],
    ),
    membership_update: MembershipPermissionUpdate = Body(...),
    group: Group = Resource(Group, param_alias="group_id"),
    member: User = Resource(User, param_alias="user_id"),
) -> Response:
    """Change group membership."""
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == member.id,
        )
    )
    membership: Membership | None = result.first()
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == session_user.id,
        )
    )
    session_user_membership: Membership = result.first()

    if not membership:
        raise HTTPException(
            status_code=404, detail="Target user is not a member of this group"
        )

    current_permissions = set(membership.permissions)
    target_permissions = set(
        membership_update.permissions or current_permissions
    )
    is_owner = session_user_membership.is_owner
    is_administrator = (
        Permission.ADMINISTRATOR in session_user_membership.permissions
    )

    added_permissions = target_permissions - current_permissions
    removed_permissions = current_permissions - target_permissions

    if Permission.ADMINISTRATOR in added_permissions and not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Only the owner can grant the ADMINISTRATOR permission",
        )

    if Permission.ADMINISTRATOR in removed_permissions and not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Only the owner can revoke the ADMINISTRATOR permission",
        )

    if Permission.MANAGE_PERMISSIONS in added_permissions and not (
        is_administrator or is_owner
    ):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can grant the MANAGE_PERMISSIONS permission",
        )

    if Permission.MANAGE_PERMISSIONS in removed_permissions and not (
        is_administrator or is_owner
    ):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can grant or revoke the MANAGE_PERMISSIONS permission",
        )

    if any(p in removed_permissions for p in group.default_permissions):
        raise AppException(
            status_code=403,
            detail="Cannot remove permissions that are included in the group's default permissions",
            error_code=AppErrorCode.CANNOT_REMOVE_PERMISSION_REASON_DEFAULT_GROUP,
        )

    if membership.share_link and any(
        p in removed_permissions for p in membership.share_link.permissions
    ):
        raise AppException(
            status_code=403,
            detail="Cannot remove permissions that are included in the related sharelink's permissions",
            error_code=AppErrorCode.CANNOT_REMOVE_PERMISSION_REASON_SHARELINK,
        )

    await db.merge(membership)
    # Apply updates to the membership fields
    membership.sqlmodel_update(membership_update.model_dump(exclude_unset=True))
    await db.commit()
    return Response(status_code=204)


@groupmembership_router.put("/accept")
async def accept_membership(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access()],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
) -> Response:
    """Accept group membership."""
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == session_user.id,
        )
    )
    membership: Membership | None = result.first()

    # If membership doesn't exist, the invite was revoked
    if not membership:
        raise AppException(
            status_code=404,
            detail="Membership invite not found or has been revoked",
            error_code=AppErrorCode.MEMBERSHIP_NOT_FOUND,
        )

    await db.merge(membership)
    membership.accepted = True
    await db.commit()
    return Response(status_code=204)


@groupmembership_router.delete("/reject")
async def reject_membership(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access()],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
) -> Response:
    """Reject group membership. Can be used to leave a group."""
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == session_user.id,
        )
    )
    membership: Membership | None = result.first()

    if not membership:
        raise AppException(
            status_code=404,
            detail="Membership invite not found or has been revoked",
            error_code=AppErrorCode.MEMBERSHIP_NOT_FOUND,
        )

    if membership.is_owner:
        raise AppException(
            status_code=403,
            detail="The owner cannot leave the group. Delete the group instead.",
            error_code=AppErrorCode.OWNER_CANNOT_LEAVE_GROUP,
        )

    await db.delete(membership)
    await db.commit()
    return Response(status_code=204)


@groupmembership_router.delete("/{user_id}")
async def remove_member(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access({Permission.REMOVE_MEMBERS})],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
    member: User = Resource(User, param_alias="user_id"),
) -> Response:
    """Remove a user from a group."""
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == member.id,
        )
    )
    membership: Membership | None = result.first()
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == session_user.id,
        )
    )
    session_user_membership: Membership = result.first()

    if not membership:
        raise HTTPException(
            status_code=404, detail="Target user is not a member of this group"
        )

    # users with ADMINISTRATOR and the owner cannot be removed
    if membership.is_owner or (
        Permission.ADMINISTRATOR in membership.permissions
        and not session_user_membership.is_owner
    ):
        raise HTTPException(
            status_code=403,
            detail="The owner and administrators cannot be removed from the group",
        )

    await db.delete(membership)
    await db.commit()
    return Response(status_code=204)


@groupmembership_router.post("/promote/{user_id}")
async def promote_guest_to_member(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access({Permission.ADD_MEMBERS})],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
    member: User = Resource(User, param_alias="user_id"),
) -> Response:
    """Upgrade a guest membership to a regular membership."""
    result = await db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == member.id,
        )
    )
    membership: Membership | None = result.first()

    if not membership:
        raise HTTPException(
            status_code=404, detail="Target user is not a member of this group"
        )

    db.add(membership)

    membership.sharelink_id = None
    await db.commit()
    return Response(status_code=204)


@groupmembership_router.get("/{user_id}/score", response_model=ScoreRead)
async def get_member_score(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access()],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
    member: User = Resource(User, param_alias="user_id"),
    document_id: str | None = Query(
        None,
        description="Filter score to a specific document",
    ),
) -> ScoreRead:
    """Get the gamification score for a user within a group.

    Optionally filter to a single document via ``document_id``.
    Scores are cached in Redis for 5 minutes. The response
    includes a ``cached_at`` timestamp so the frontend can
    show when the score was last computed.
    """
    cache_key = score_cache_key(group.id, member.id, document_id)
    cached = await get_cached(cache_key)
    if cached is not None:
        return ScoreRead.model_validate(cached)

    score = await _compute_score(db, group.id, member.id, document_id)
    await set_cached(cache_key, score.model_dump(mode="json"))
    return score


async def _compute_score(
    db: Database,
    group_id: str,
    user_id: int,
    document_id: str | None = None,
) -> ScoreRead:
    """Compute a user's score within a group.

    When *document_id* is supplied the score is scoped to that
    single document; otherwise all documents in the group are
    included.  Only root-level comments (parent_id IS NULL)
    count.
    """
    # Document scope: single document or all group documents
    if document_id is not None:
        doc_filter = (
            Comment.document_id == document_id,  # type: ignore[union-attr]
        )
    else:
        group_docs = (
            select(Document.id)
            .where(Document.group_id == group_id)
            .scalar_subquery()
        )
        doc_filter = (
            Comment.document_id.in_(group_docs),  # type: ignore[union-attr]
        )

    # Base filter: root comments by this user in scoped documents
    root_comments_filter = (
        Comment.user_id == user_id,
        Comment.parent_id.is_(None),  # type: ignore[union-attr]
        *doc_filter,
    )

    # 1. Highlights: comments with non-empty annotation
    highlight_result = await db.exec(
        select(func.count())
        .select_from(Comment)
        .where(
            *root_comments_filter,
            Comment.annotation != {},
        )
    )
    highlights: int = highlight_result.one()

    # 2. Comments with text content
    comment_result = await db.exec(
        select(func.count())
        .select_from(Comment)
        .where(
            *root_comments_filter,
            Comment.content.is_not(None),  # type: ignore[union-attr]
        )
    )
    comments: int = comment_result.one()

    # 3. Tags on user's root comments
    tag_result = await db.exec(
        select(func.count())
        .select_from(CommentTag)
        .join(Comment, CommentTag.comment_id == Comment.id)
        .where(
            Comment.user_id == user_id,
            Comment.parent_id.is_(None),  # type: ignore[union-attr]
            *doc_filter,
        )
    )
    tags: int = tag_result.one()

    # Load per-group scoring configuration
    cfg_result = await db.exec(
        select(ScoreConfig).where(ScoreConfig.group_id == group_id)
    )
    score_cfg = cfg_result.first()

    # Fall back to defaults if no config row exists
    cfg_highlight = score_cfg.highlight_points if score_cfg else 1
    cfg_comment = score_cfg.comment_points if score_cfg else 5
    cfg_tag = score_cfg.tag_points if score_cfg else 2

    # 4. Reactions received — split by admin/normal
    #    A reactor is admin if they are owner or have ADMINISTRATOR
    #    in their membership permissions for this group.
    #    Points now come from GroupReaction per-emoji config.
    reactor_membership = (
        select(Membership).where(Membership.group_id == group_id).subquery()
    )

    is_admin_case = case(
        (
            or_(
                reactor_membership.c.is_owner.is_(True),
                reactor_membership.c.permissions.contains(
                    [Permission.ADMINISTRATOR.value]
                ),
            ),
            1,
        ),
        else_=0,
    )

    # Per-reaction points from GroupReaction table
    admin_points_col = case(
        (
            or_(
                reactor_membership.c.is_owner.is_(True),
                reactor_membership.c.permissions.contains(
                    [Permission.ADMINISTRATOR.value]
                ),
            ),
            GroupReaction.admin_points,
        ),
        else_=GroupReaction.points,
    )

    received_result = await db.exec(
        select(
            func.count(),
            func.coalesce(func.sum(is_admin_case), 0),
            func.coalesce(func.sum(admin_points_col), 0),
        )
        .select_from(Reaction)
        .join(Comment, Reaction.comment_id == Comment.id)
        .join(
            GroupReaction,
            Reaction.group_reaction_id == GroupReaction.id,
        )
        .outerjoin(
            reactor_membership,
            Reaction.user_id == reactor_membership.c.user_id,
        )
        .where(
            Comment.user_id == user_id,
            Comment.parent_id.is_(None),  # type: ignore[union-attr]
            *doc_filter,
        )
    )
    row = received_result.one()
    reactions_received: int = row[0]
    reactions_from_admin: int = int(row[1])
    reaction_received_points = int(row[2])

    # 5. Reactions given by this user on root comments in the group
    given_result = await db.exec(
        select(
            func.count(),
            func.coalesce(func.sum(GroupReaction.giver_points), 0),
        )
        .select_from(Reaction)
        .join(Comment, Reaction.comment_id == Comment.id)
        .join(
            GroupReaction,
            Reaction.group_reaction_id == GroupReaction.id,
        )
        .where(
            Reaction.user_id == user_id,
            Comment.parent_id.is_(None),  # type: ignore[union-attr]
            *doc_filter,
        )
    )
    given_row = given_result.one()
    reactions_given: int = given_row[0]
    reaction_given_points = int(given_row[1])

    # 6. Per-reaction breakdown
    # Received per emoji
    per_received = await db.exec(
        select(
            GroupReaction.id,
            GroupReaction.emoji,
            func.count(),
            func.coalesce(func.sum(is_admin_case), 0),
            func.coalesce(func.sum(admin_points_col), 0),
        )
        .select_from(Reaction)
        .join(Comment, Reaction.comment_id == Comment.id)
        .join(
            GroupReaction,
            Reaction.group_reaction_id == GroupReaction.id,
        )
        .outerjoin(
            reactor_membership,
            Reaction.user_id == reactor_membership.c.user_id,
        )
        .where(
            Comment.user_id == user_id,
            Comment.parent_id.is_(None),  # type: ignore[union-attr]
            *doc_filter,
        )
        .group_by(GroupReaction.id, GroupReaction.emoji)
    )
    received_per_emoji: dict[int, tuple[str, int, int, int]] = {}
    for r_row in per_received.all():
        received_per_emoji[r_row[0]] = (
            r_row[1],  # emoji
            int(r_row[2]),  # count
            int(r_row[3]),  # from_admin
            int(r_row[4]),  # points
        )

    # Given per emoji
    per_given = await db.exec(
        select(
            GroupReaction.id,
            func.count(),
            func.coalesce(func.sum(GroupReaction.giver_points), 0),
        )
        .select_from(Reaction)
        .join(Comment, Reaction.comment_id == Comment.id)
        .join(
            GroupReaction,
            Reaction.group_reaction_id == GroupReaction.id,
        )
        .where(
            Reaction.user_id == user_id,
            Comment.parent_id.is_(None),  # type: ignore[union-attr]
            *doc_filter,
        )
        .group_by(GroupReaction.id)
    )
    given_per_emoji: dict[int, tuple[int, int]] = {}
    for g_row in per_given.all():
        given_per_emoji[g_row[0]] = (int(g_row[1]), int(g_row[2]))

    # Build per-reaction breakdown for all group reactions
    all_gr_result = await db.exec(
        select(GroupReaction)
        .where(GroupReaction.group_id == group_id)
        .order_by(GroupReaction.order)
    )
    reaction_breakdown: list[ReactionBreakdownItem] = []
    for gr in all_gr_result.all():
        rcvd = received_per_emoji.get(gr.id, (gr.emoji, 0, 0, 0))
        gvn = given_per_emoji.get(gr.id, (0, 0))
        reaction_breakdown.append(
            ReactionBreakdownItem(
                group_reaction_id=gr.id,
                emoji=gr.emoji,
                received_count=rcvd[1],
                received_from_admin=rcvd[2],
                received_points=rcvd[3],
                given_count=gvn[0],
                given_points=gvn[1],
            )
        )

    # Calculate points
    highlight_points = highlights * cfg_highlight
    comment_points = comments * cfg_comment
    tag_points = tags * cfg_tag

    total = (
        highlight_points
        + comment_points
        + tag_points
        + reaction_received_points
        + reaction_given_points
    )

    breakdown = ScoreBreakdown(
        highlights=highlights,
        highlight_points=highlight_points,
        comments=comments,
        comment_points=comment_points,
        tags=tags,
        tag_points=tag_points,
        reactions_received=reactions_received,
        reactions_received_from_admin=reactions_from_admin,
        reaction_received_points=reaction_received_points,
        reactions_given=reactions_given,
        reaction_given_points=reaction_given_points,
        reaction_breakdown=reaction_breakdown,
    )

    return ScoreRead(
        total=total,
        breakdown=breakdown,
        cached_at=datetime.now(UTC),
    )
