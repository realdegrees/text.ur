from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from api.dependencies.storage import Storage
from api.routers.memberships import (
    groupmembership_router as GroupMembershipRouter,
)
from api.routers.sharelinks import router as ShareLinkRouter
from core.app_exception import AppException
from core.logger import get_logger
from core.rate_limit import limiter
from fastapi import Body, Request, Response
from models.document import DocumentRead, DocumentReorder
from models.enums import AppErrorCode, Permission
from models.filter import GroupFilter
from models.group import (
    GroupCreate,
    GroupRead,
    GroupTransfer,
    GroupUpdate,
    MembershipCreate,
    MembershipPermissionUpdate,
)
from models.pagination import Paginated
from models.reaction import DEFAULT_REACTIONS
from models.tables import (
    Document,
    Group,
    GroupReaction,
    Membership,
    ScoreConfig,
    User,
)
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from util.api_router import APIRouter
from util.group_cleanup import cleanup_storage_keys, prepare_group_deletion
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

groups_logger = get_logger("app")

router = APIRouter(
    prefix="/groups",
    tags=["Group Management"],
)

# region Groups


@router.get(
    "/",
    response_model=Paginated[GroupRead],
    response_class=ExcludableFieldsJSONResponse,
)
async def list_groups(
    _: BasicAuthentication,
    groups: Paginated[Group] = PaginatedResource(Group, GroupFilter, guards=[Guard.group_access()]),
) -> Paginated[GroupRead]:
    """Get all groups the user is a member of."""
    return groups


@router.post("/", response_model=GroupRead)
@limiter.limit("10/minute")
async def create_group(
    request: Request,
    db: Database,
    user: BasicAuthentication,
    group_create: GroupCreate = Body(...),
) -> Group:
    """Create a new group."""
    group = Group(**group_create.model_dump())
    db.add(group)
    await db.flush()

    membership = Membership(
        user_id=user.id,
        group_id=group.id,
        permissions=[Permission.ADMINISTRATOR],
        is_owner=True,
        accepted=True,
    )
    db.add(membership)

    # Seed default score config and group reactions
    score_config = ScoreConfig(group_id=group.id)
    db.add(score_config)

    for r in DEFAULT_REACTIONS:
        db.add(GroupReaction(group_id=group.id, **r))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppException(
            status_code=409,
            error_code=AppErrorCode.INVALID_INPUT,
            detail="Group with this name already exists.",
        ) from None

    await db.refresh(group)
    return group


# TODO maybe if the group system becomes invite only then by default only return if the user is a part of the group
@router.get("/{group_id}", response_model=GroupRead)
async def read_group(
    _: User = Authenticate([Guard.group_access()]),
    group: Group = Resource(Group, param_alias="group_id"),
) -> Group:
    """Get a group by ID. Reject if the user is not a member."""
    return group


@router.put("/{group_id}", response_model=GroupRead)
async def update_group(
    db: Database,
    session_user: User = Authenticate([Guard.group_access({Permission.ADMINISTRATOR})]),
    group: Group = Resource(Group, param_alias="group_id"),
    group_update: GroupUpdate = Body(...),
) -> Group:
    """Update a group."""
    # Only the owner may include ADMINISTRATOR in default_permissions
    if group_update.default_permissions is not None and Permission.ADMINISTRATOR in group_update.default_permissions:
        result = await db.exec(
            select(Membership).where(
                Membership.group_id == group.id,
                Membership.user_id == session_user.id,
            )
        )
        caller_membership: Membership | None = result.first()
        if not caller_membership or not caller_membership.is_owner:
            raise AppException(
                status_code=403,
                error_code=AppErrorCode.INVALID_PERMISSIONS,
                detail="Only the owner can include ADMINISTRATOR in default permissions",
            )

    await db.merge(group)
    group.sqlmodel_update(group_update.model_dump(exclude_unset=True))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppException(
            status_code=409,
            error_code=AppErrorCode.ALREADY_EXISTS,
            detail="Group with this name already exists.",
        ) from None

    # if default permissions were changed, update all existing memberships to include at least those permissions
    if group_update.default_permissions is not None:
        result = await db.exec(
            select(Membership).where(
                Membership.group_id == group.id,
                ~Membership.permissions.contains(group_update.default_permissions),
            )
        )
        memberships_missing_permissions = result.all()
        for membership in memberships_missing_permissions:
            membership.permissions = list(set(membership.permissions).union(set(group_update.default_permissions)))
            db.add(membership)
        await db.commit()

    await db.refresh(group)
    return group


@router.post("/{group_id}/transfer")
@limiter.limit("5/minute")
async def transfer_ownership(
    request: Request,
    db: Database,
    transfer: GroupTransfer = Body(...),
    session_user: User = Authenticate([Guard.group_access(None, only_owner=True)]),
    group: Group = Resource(Group, param_alias="group_id"),
) -> None:
    """Transfer group ownership."""
    # Check if transfer user exists
    result = await db.exec(select(User).where(User.id == transfer.user_id))
    transfer_user = result.first()

    if not transfer_user:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Target user not found",
        )

    # Check if the new owner is a member of the group
    result = await db.exec(
        select(Membership).where(
            Membership.user_id == transfer.user_id,
            Membership.group_id == group.id,
            Membership.accepted == True,  # noqa: E712
        )
    )
    transfer_membership = result.first()

    if not transfer_membership:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Target user is not a member of the group",
        )

    result = await db.exec(
        select(Membership).where(
            Membership.user_id == session_user.id,
            Membership.group_id == group.id,
        )
    )
    current_owner_membership = result.first()

    current_owner_membership.is_owner = False
    current_owner_membership.permissions = [Permission.ADMINISTRATOR]
    transfer_membership.is_owner = True

    db.add(current_owner_membership)
    db.add(transfer_membership)
    await db.commit()


@router.delete("/{group_id}")
@limiter.limit("5/minute")
async def delete_group(
    request: Request,
    db: Database,
    storage: Storage,
    _: User = Authenticate([Guard.group_access(None, only_owner=True)]),
    group: Group = Resource(Group, param_alias="group_id"),
) -> Response:
    """Delete a group and its associated stored files."""
    storage_keys = await prepare_group_deletion(db, group.id)
    await db.commit()

    cleanup_storage_keys(storage, storage_keys, groups_logger, f"group {group.id}")

    return Response(status_code=204)


# endregion

# region Document Reorder


@router.put(
    "/{group_id}/documents/reorder",
    response_model=list[DocumentRead],
)
async def reorder_documents(
    db: Database,
    reorder: DocumentReorder = Body(...),
    session_user: User = Authenticate([Guard.group_access({Permission.ADMINISTRATOR})]),
    group: Group = Resource(Group, param_alias="group_id"),
) -> list[DocumentRead]:
    """Reorder a subset of documents within a group.

    Accepts a partial list of document IDs in the desired order.
    Only the submitted documents are reordered — all others keep
    their current positions. The submitted documents swap into
    each other's order slots.
    """
    result = await db.exec(
        select(Document).where(
            Document.group_id == group.id,
            Document.id.in_(reorder.document_ids),
        )
    )
    docs_by_id = {d.id: d for d in result.all()}

    # Validate all submitted IDs exist in this group
    unknown = set(reorder.document_ids) - set(docs_by_id.keys())
    if unknown:
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.VALIDATION_ERROR,
            detail=f"Unknown document IDs: {sorted(unknown)}",
        )

    # Slot reassignment: collect current order values, sort them,
    # then assign them in the new sequence.
    slots = sorted(docs_by_id[did].order for did in reorder.document_ids)
    for slot, doc_id in zip(slots, reorder.document_ids, strict=True):
        doc = await db.merge(docs_by_id[doc_id])
        doc.order = slot

    await db.commit()

    # Return the reordered subset
    result = await db.exec(
        select(Document)
        .where(
            Document.group_id == group.id,
            Document.id.in_(reorder.document_ids),
        )
        .order_by(Document.order)
    )
    return [DocumentRead.model_validate(d) for d in result.all()]


# endregion

from api.routers.score_config import router as ScoreConfigRouter  # noqa: E402

tags = router.tags
router.tags = []
router.include_router(ShareLinkRouter, prefix="/{group_id}")
router.include_router(GroupMembershipRouter, prefix="/{group_id}/memberships")
router.include_router(ScoreConfigRouter, prefix="/{group_id}")
router.tags = tags
