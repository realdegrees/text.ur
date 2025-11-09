from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from fastapi import Body, HTTPException, Path, Response
from models.enums import Permission
from models.filter import GroupMembershipFilter
from models.group import (
    GroupMembershipRead,
    MembershipCreate,
    MembershipPermissionUpdate,
)
from models.pagination import Paginated
from models.tables import Group, Membership, User
from sqlmodel import select
from util.api_router import APIRouter
from util.queries import Guard

router = APIRouter(
    prefix="/memberships",
    tags=["Memberships"],
)


@router.get("/", response_model=Paginated[GroupMembershipRead])
async def list_memberships(
    _: User = Authenticate([Guard.group_access()]),
    memberships: Paginated[Membership] = PaginatedResource(
        Membership, GroupMembershipFilter, guards=[Guard.combine(op="and", guards=[Guard.membership_in_group()])], key_columns=[Membership.user_id, Membership.group_id]
    ),
    group_id: str = Path(...,
                         description="The ID of the group to list memberships for"),
) -> Paginated[GroupMembershipRead]:
    """Get all group memberships."""
    return memberships


@router.post("/")
async def invite_member(
    db: Database,
    group: Group = Resource(Group, param_alias="group_id"),
    _: User = Authenticate([Guard.group_access({Permission.ADD_MEMBERS})]),
    membership_create: MembershipCreate = Body(...)
) -> Response:
    """Get all group memberships."""
    # Check if user exists and is not already a member
    user, membership = db.exec(
        select(User, Membership)
        .outerjoin(Membership, (Membership.user_id == User.id) & (Membership.group_id == group.id))
        .where(User.id == membership_create.user_id)
    ).first() or (None, None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if membership:
        raise HTTPException(
            status_code=400, detail="User is already a member of this group")

    # Create new membership
    membership_create = Membership(
        user_id=membership_create.user_id, group_id=group.id, permissions=group.default_permissions, is_owner=False, accepted=False
    )
    db.add(membership_create)
    db.commit()
    db.refresh(membership_create)
    return Response(status_code=201)


@router.put("/{user_id}/permissions")
async def update_member_permissions(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access({Permission.MANAGE_PERMISSIONS})],
    ),
    membership_update: MembershipPermissionUpdate = Body(...),
    group: Group = Resource(Group, param_alias="group_id"),
    member: User = Resource(User, param_alias="user_id")
) -> Response:
    """Change group membership."""
    membership: Membership | None = db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == member.id,
        )
    ).first()
    session_user_membership: Membership = db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == session_user.id,
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=404, detail="Target user is not a member of this group")

    current_permissions = set(membership.permissions)
    target_permissions = set(
        membership_update.permissions or current_permissions)
    is_owner = session_user_membership.is_owner
    is_administrator = Permission.ADMINISTRATOR in session_user_membership.permissions

    added_permissions = target_permissions - current_permissions
    removed_permissions = current_permissions - target_permissions

    if Permission.ADMINISTRATOR in added_permissions and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only the owner can grant the ADMINISTRATOR permission")

    if Permission.ADMINISTRATOR in removed_permissions and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only the owner can revoke the ADMINISTRATOR permission")

    if Permission.MANAGE_PERMISSIONS in added_permissions and not is_administrator:
        raise HTTPException(
            status_code=403, detail="Only administrators can grant the MANAGE_PERMISSIONS permission")

    if Permission.MANAGE_PERMISSIONS in removed_permissions and not is_administrator:
        raise HTTPException(
            status_code=403, detail="Only administrators can grant or revoke the MANAGE_PERMISSIONS permission")

    db.merge(membership)
    # Apply updates to the membership fields
    membership.sqlmodel_update(
        membership_update.model_dump(exclude_unset=True)
    )
    db.commit()
    return Response(status_code=204)


@router.put("/accept")
async def accept_membership(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access()],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
) -> Response:
    """Accept group membership."""
    membership: Membership = db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == session_user.id,
        )
    ).first()

    db.merge(membership)
    membership.accepted = True
    db.commit()
    return Response(status_code=204)


@router.put("/reject")
async def reject_membership(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access()],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
) -> Response:
    """Reject group membership. Can be used to leave a group."""
    membership: Membership = db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == session_user.id,
        )
    ).first()

    db.delete(membership)
    db.commit()
    return Response(status_code=204)


@router.delete("/{user_id}")
async def remove_member(
    db: Database,
    session_user: User = Authenticate(
        [Guard.group_access({Permission.REMOVE_MEMBERS})],
    ),
    group: Group = Resource(Group, param_alias="group_id"),
    member: User = Resource(User, param_alias="user_id")
) -> Response:
    """Remove a user from a group."""
    membership: Membership | None = db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == member.id,
        )
    ).first()
    session_user_membership: Membership = db.exec(
        select(Membership).where(
            Membership.group_id == group.id,
            Membership.user_id == session_user.id,
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=404, detail="Target user is not a member of this group")

    # users with ADMINISTRATOR and the owner cannot be removed
    if membership.is_owner or (Permission.ADMINISTRATOR in membership.permissions and not session_user_membership.is_owner):
        raise HTTPException(
            status_code=403, detail="The owner and administrators cannot be removed from the group")

    db.delete(membership)
    db.commit()
    return Response(status_code=204)
