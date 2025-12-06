from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from api.routers.memberships import (
    groupmembership_router as GroupMembershipRouter,
)
from api.routers.sharelinks import router as ShareLinkRouter
from fastapi import Body, HTTPException, Response
from models.enums import Permission
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
from models.tables import Group, Membership, User
from sqlmodel import select
from util.api_router import APIRouter
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

router = APIRouter(
    prefix="/groups",
    tags=["Group Management"],
)

# region Groups

@router.get("/", response_model=Paginated[GroupRead], response_class=ExcludableFieldsJSONResponse)
async def list_groups(
    _: BasicAuthentication,
    groups: Paginated[Group] = PaginatedResource(
        Group, GroupFilter, guards=[Guard.group_access()]
    )
) -> Paginated[GroupRead]:
    """Get all groups the user is a member of."""
    return groups


@router.post("/", response_model=GroupRead)
async def create_group(
    db: Database, user: BasicAuthentication, group_create: GroupCreate = Body(...)
) -> Group:
    """Create a new group."""
    result = await db.exec(
        select(Group).where(Group.name == group_create.name)
    )
    existing_group = result.first()
    if existing_group:
        raise HTTPException(
            status_code=400, detail="Group with this name already exists"
        )

    group = Group(**group_create.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group)

    groupMembership = Membership(
        user_id=user.id, group_id=group.id, permissions=[Permission.ADMINISTRATOR], is_owner=True, accepted=True
    )
    db.add(groupMembership)
    await db.commit()
    await db.refresh(groupMembership)

    return group

# TODO maybe if the group system becomes invite only then by default only return if the user is a part of the group
@router.get("/{group_id}", response_model=GroupRead)
async def read_group(
    _: User = Authenticate([Guard.group_access()]),
    group: Group = Resource(Group, param_alias="group_id")
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
    await db.merge(group)
    group.sqlmodel_update(group_update.model_dump(exclude_unset=True))

    await db.commit()

    # if default permissions were changed, update all existing memberships to include at least those permissions
    if group_update.default_permissions is not None:
        result = await db.exec(
            select(Membership).where(
                Membership.group_id == group.id,
                ~Membership.permissions.contains(group_update.default_permissions)
            )
        )
        memberships_missing_permissions = result.all()
        for membership in memberships_missing_permissions:
            membership.permissions = list(
                set(membership.permissions).union(set(group_update.default_permissions))
            )
            db.add(membership)
        await db.commit()

    await db.refresh(group)
    return group

@router.post("/{group_id}/transfer")
async def transfer_ownership(
    db: Database,
    transfer: GroupTransfer = Body(...),
    session_user: User = Authenticate([Guard.group_access(None, only_owner=True)]),
    group: Group = Resource(Group, param_alias="group_id"),
) -> None:
    """Transfer group ownership."""
    # Check if transfer user exists
    result = await db.exec(
        select(User).where(User.id == transfer.user_id)
    )
    transfer_user = result.first()

    if not transfer_user:
        raise HTTPException(
            status_code=404, detail="Target user not found")


    # Check if the new owner is a member of the group
    result = await db.exec(
        select(Membership).where(
            Membership.user_id == transfer.user_id,
            Membership.group_id == group.id,
            Membership.accepted == True, # noqa: E712
        )
    )
    transfer_membership = result.first()

    if not transfer_membership:
        raise HTTPException(
            status_code=404, detail="Target user is not a member of the group")

    result = await db.exec(
        select(Membership).where(
            Membership.user_id == session_user.id,
            Membership.group_id == group.id
        )
    )
    current_owner_membership = result.first()

    current_owner_membership.is_owner = False
    current_owner_membership.permissions = list(Permission.ADMINISTRATOR)
    transfer_membership.is_owner = True

    db.add(current_owner_membership)
    db.add(transfer_membership)
    await db.commit()

@router.delete("/{group_id}")
async def delete_group(
    db: Database,
    _: User = Authenticate([Guard.group_access(None, only_owner=True)]),
    group: Group = Resource(Group, param_alias="group_id"),
) -> dict[str, bool]:
    """Delete a group."""
    await db.delete(group)
    await db.commit()
    return Response(status_code=204)

# endregion

tags = router.tags
router.tags = []
router.include_router(ShareLinkRouter, prefix="/{group_id}")
router.include_router(GroupMembershipRouter, prefix="/{group_id}/memberships")
router.tags = tags

# TODO: add sharelink management endpoints (only owner and admin can create share links, admins can not create share links with admin permissions)