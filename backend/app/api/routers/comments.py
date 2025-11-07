from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from api.routers.reactions import router as ReactionRouter
from fastapi import Body, Response
from models.comment import CommentCreate, CommentRead, CommentUpdate
from models.enums import Permission
from models.filter import CommentFilter
from models.pagination import Paginated
from models.tables import Comment, User
from util.api_router import APIRouter
from util.queries import Guard

# ======= Comment Router ==============

router = APIRouter(
    prefix="/comments",
    tags=["Comments"],
)

# ======= Comment Endpoints ==============


@router.get("/", response_model=Paginated[CommentRead])
async def list_comments(
    _: BasicAuthentication,
    comments: Paginated[Comment] = PaginatedResource(
        Comment,
        CommentFilter,
        guards=[Guard.comment_access()],
    )
) -> Paginated[CommentRead]:
    """Get all comments that the user can access."""
    return comments

@router.post("/create", response_model=CommentRead)
async def create_comment(
    db: Database, 
    user: User = Authenticate([Guard.document_access({Permission.ADD_COMMENTS})]), 
    create: CommentCreate = Body(...),
) -> Comment:
    """Create a new comment."""
    comment = Comment(**create.model_dump())
    comment.user_id = user.id
    comment.document_id = create.document_id
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@router.get("/{comment_id}", response_model=CommentRead)
async def read_comment(
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    _: User = Authenticate([Guard.comment_access()]),
) -> Comment:
    """Get a comment by ID."""
    return comment


@router.put("/{comment_id}", response_model=CommentRead)
async def update_comment(
    db: Database,
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    _: User = Authenticate([Guard.comment_access(None, only_owner=True)]),
    update: CommentUpdate = Body(...),
) -> Comment:
    """Update a comment."""
    # Apply updates to the comment fields
    db.merge(comment)
    comment.sqlmodel_update(update.model_dump(exclude_unset=True))
    db.commit()
    return comment


@router.delete("/{comment_id}")
async def delete_comment(
    db: Database,
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    _: User = Authenticate([Guard.comment_access({Permission.REMOVE_COMMENTS})]),
) -> Response:
    """Delete a comment."""
    db.delete(comment)
    db.commit()
    return Response(status_code=204)

tags = router.tags
router.tags = []
router.include_router(ReactionRouter, prefix="/{comment_id}")
router.tags = tags