# Share Link Router
# TODO create sharelink router (create delete update read read-list)
# TODO router should be subrouter of groups router, probably needs new endpoint guards

from datetime import UTC, datetime

from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from fastapi import Body, HTTPException, Path, Response
from models.enums import Permission
from models.filter import ShareLinkFilter
from models.pagination import Paginated
from models.sharelink import ShareLinkCreate, ShareLinkRead, ShareLinkUpdate
from models.tables import Group, Membership, ShareLink, User
from sqlmodel import select
from util.api_router import APIRouter
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

router = APIRouter(
    prefix="/sharelinks",
    tags=["Share Links"],
)
root_router = APIRouter(
    prefix="/sharelinks",
    tags=["Share Links"],
)


@router.get("/", response_model=Paginated[ShareLinkRead], response_class=ExcludableFieldsJSONResponse)
async def list_share_links(
    _: BasicAuthentication,
    share_links: Paginated[ShareLink] = PaginatedResource(
        ShareLink, ShareLinkFilter, guards=[Guard.sharelink_access()]
    )
) -> Paginated[ShareLinkRead]:
    """Get all share links for the group."""
    return share_links


@root_router.get("/{token}", response_model=ShareLinkRead)
async def get_share_link_from_token(
    _: User = Authenticate(guards=[Guard.sharelink_access()]),
    share_link: ShareLink = Resource(ShareLink, param_alias="token"),
) -> ShareLinkRead:
    """Get all share links for groups the user has access to."""
    return share_link


@router.post("/", response_model=ShareLinkRead)
async def create_share_link(
    db: Database,
    group: Group = Resource(Group, param_alias="group_id"),
    user: User = Authenticate(
        [Guard.group_access({Permission.ADMINISTRATOR})]),
    share_link_create: ShareLinkCreate = Body(...)
) -> ShareLinkRead:
    """Create a new share link for a group."""
    share_link = ShareLink(**share_link_create.model_dump())
    share_link.group_id = group.id
    share_link.author_id = user.id
    db.add(share_link)
    db.commit()
    db.refresh(share_link)
    return share_link


@router.put("/{share_link_id}", response_model=ShareLinkRead)
async def update_share_link(
    db: Database,
    _: User = Authenticate([Guard.group_access({Permission.ADMINISTRATOR})]),
    share_link: ShareLink = Resource(ShareLink, param_alias="share_link_id"),
    share_link_update: ShareLinkUpdate = Body(...),
    group: Group = Resource(Group, param_alias="group_id"),
) -> ShareLinkRead:
    """Update a share link."""
    permissions_changed = share_link_update.permissions is not None and set(share_link_update.permissions) != set(share_link.permissions)
    db.merge(share_link)
    share_link.sqlmodel_update(share_link_update.model_dump(
        exclude_unset=True, exclude={"rotate_token"}))
    
    memberships: list[Membership] = db.exec(
            select(Membership).join(ShareLink, Membership.share_link).where(
                ShareLink.token == share_link.token,
                Membership.group_id == group.id,
            )
        ).all()
    
    if permissions_changed:
        # Compute minimum permissions: group defaults plus the sharelink's new permissions.
        new_sharelink_permissions: set[Permission] = set(share_link.permissions)
        group_default_permissions: set[Permission] = set(group.default_permissions)
        updated_permissions: set[Permission] = group_default_permissions | new_sharelink_permissions

        # Ensure each membership has at least the required permissions without removing existing ones.
        for membership in memberships:
            db.merge(membership)
            membership.permissions = updated_permissions
    
    # Handle token rotation and membership deletions
    if share_link_update.rotate_token:
        share_link.rotate_token()
        # Delete all memberships that were using this token
        # Query memberships associated with the sharelink relationship that match the token and group.
        memberships: list[Membership] = db.exec(
            select(Membership).join(ShareLink, Membership.share_link).where(
                ShareLink.token == share_link.token,
                Membership.group_id == group.id,
            )
        ).all()
        for membership in memberships:
            db.delete(membership)
            
    # Handle permission updates:
            
    db.commit()
    return share_link


@router.delete("/{share_link_id}")
async def delete_share_link(
    db: Database,
    _: User = Authenticate([Guard.group_access({Permission.ADMINISTRATOR})]),
    share_link: ShareLink = Resource(ShareLink, param_alias="share_link_id"),
    group: Group = Resource(Group, param_alias="group_id"),
) -> Response:
    """Delete a share link."""
    db.delete(share_link)
    db.commit()
    return Response(status_code=204)


@root_router.post("/use/{token}", response_model=ShareLinkRead)
async def use_sharelink_token(
    db: Database,
    token: str,
    user: User = Authenticate(),
) -> ShareLinkRead:
    """Create a membership for an authenticated user via sharelink token.

    This endpoint is only for authenticated users. Anonymous users should
    use the /login/anonymous endpoint directly.
    """
    # Find the sharelink by token
    share_link: ShareLink | None = db.exec(
        select(ShareLink).where(ShareLink.token == token)
    ).first()

    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    # Check if expired
    if share_link.is_expired:
        raise HTTPException(status_code=403, detail="Share link has expired")

    # Check if membership already exists
    existing_membership: Membership | None = db.exec(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.group_id == share_link.group_id
        )
    ).first()

    if existing_membership:
        # User is already a member
        return share_link

    # Create new membership
    membership = Membership(
        user_id=user.id,
        group_id=share_link.group_id,
        permissions=set(share_link.permissions) | set(
            share_link.group.default_permissions),
        is_owner=False,
        accepted=True,  # Auto-accept for sharelink memberships
        share_link=share_link
    )
    db.add(membership)
    db.commit()
    return share_link
