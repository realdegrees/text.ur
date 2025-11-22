# Share Link Router
# TODO create sharelink router (create delete update read read-list)
# TODO router should be subrouter of groups router, probably needs new endpoint guards

from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from fastapi import Body, Path, Response
from models.enums import Permission
from models.filter import ShareLinkFilter
from models.pagination import Paginated
from models.sharelink import ShareLinkCreate, ShareLinkRead, ShareLinkUpdate
from models.tables import Group, ShareLink, User
from util.api_router import APIRouter
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

router = APIRouter(
    prefix="/sharelinks",
    tags=["Share Links"],
)

@router.get("/", response_model=Paginated[ShareLinkRead], response_class=ExcludableFieldsJSONResponse)
async def list_share_links(
    _: BasicAuthentication,
    share_links: Paginated[ShareLink] = PaginatedResource(
        ShareLink, ShareLinkFilter, guards=[Guard.group_access(require_permissions={Permission.MANAGE_SHARE_LINKS})]
    )
) -> Paginated[ShareLinkRead]:
    """Get all group memberships."""
    return share_links

@router.post("/", response_model=ShareLinkRead)
async def create_share_link(
    db: Database,
    group: Group = Resource(Group, param_alias="group_id"),
    _: User = Authenticate([Guard.group_access({Permission.ADMINISTRATOR})]),
    share_link_create: ShareLinkCreate = Body(...)
) -> ShareLinkRead:
    """Create a new share link for a group."""
    share_link = ShareLink(**share_link_create.model_dump())
    share_link.group_id = group.id
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
    db.merge(share_link)
    share_link.sqlmodel_update(share_link_update.model_dump(exclude_unset=True, exclude={"rotate_token"}))
    if share_link_update.rotate_token:
        share_link.rotate_token()
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

# TODO probably add an endpoint to validate a share link 
# (should maybe act like login and return a session token that identifies the temporary user and create a temporary db user so that everything else just works, 
# then save the id of the temporary user in the frontend so that if the user ever makes an account with the same device, the account can be connected.)