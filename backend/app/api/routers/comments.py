from datetime import datetime
from uuid import uuid4

from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.events import Events
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from api.routers.reactions import router as ReactionRouter
from core import config
from fastapi import Body, Header, HTTPException, Response
from models.comment import CommentCreate, CommentRead, CommentUpdate
from models.enums import Permission
from models.event import Event
from models.filter import CommentFilter
from models.pagination import Paginated
from models.tables import Comment, CommentTag, Tag, User
from sqlmodel import func, select
from util.api_router import APIRouter
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

# ======= Comment Router ==============

router = APIRouter(
    prefix="/comments",
    tags=["Comments"],
)

# ======= Comment Endpoints ==============


@router.get("/", response_model=Paginated[CommentRead], response_class=ExcludableFieldsJSONResponse)
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

@router.post("/", response_model=CommentRead)
async def create_comment(
    db: Database,
    events: Events,
    user: User = Authenticate([Guard.document_access({Permission.ADD_COMMENTS})]),
    create: CommentCreate = Body(...),
    x_connection_id: str | None = Header(None, alias="X-Connection-ID"),
) -> Comment:
    """Create a new comment."""
    comment = Comment(**create.model_dump())
    comment.user_id = user.id
    comment.document_id = create.document_id
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Broadcast creation event
    event = Event(
        event_id=uuid4(),
        published_at=datetime.now(),
        payload=CommentRead.model_validate(comment),
        resource_id=comment.id,
        resource="comment",
        type="create",
        originating_connection_id=x_connection_id  # Don't echo to originating connection
    )
    await events.publish(
        event.model_dump(mode="json"),
        channel=f"documents:{comment.document_id}:comments"
    )

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
    events: Events,
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    user: User = Authenticate([Guard.comment_access(None, only_owner=True)]),
    update: CommentUpdate = Body(...),
    x_connection_id: str | None = Header(None, alias="X-Connection-ID"),
) -> Comment:
    """Update a comment."""
    # Store old visibility before updating (for WebSocket event filtering)
    old_visibility = comment.visibility.value if comment.visibility else None

    # Apply updates to the comment fields
    db.merge(comment)
    comment.sqlmodel_update(update.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(comment)

    # Broadcast update event with old_visibility for visibility change detection
    event = Event(
        event_id=uuid4(),
        published_at=datetime.now(),
        payload=CommentRead.model_validate(comment),
        resource_id=comment.id,
        resource="comment",
        type="update",
        originating_connection_id=x_connection_id  # Don't echo to originating connection
    )
    event_data = event.model_dump(mode="json")
    event_data["old_visibility"] = old_visibility  # Include old visibility for filtering

    await events.publish(
        event_data,
        channel=f"documents:{comment.document_id}:comments"
    )

    return comment


@router.delete("/{comment_id}")
async def delete_comment(
    db: Database,
    events: Events,
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    user: User = Authenticate([Guard.comment_access({Permission.REMOVE_COMMENTS})]),
    x_connection_id: str | None = Header(None, alias="X-Connection-ID"),
) -> Response:
    """Delete a comment."""
    # Store document_id and comment_id before deletion
    document_id = comment.document_id
    comment_id = comment.id

    # Serialize comment BEFORE deleting (relationships won't be accessible after deletion)
    comment_payload = CommentRead.model_validate(comment)

    db.delete(comment)
    db.commit()

    # Broadcast delete event
    event = Event(
        event_id=uuid4(),
        published_at=datetime.now(),
        payload=comment_payload,
        resource_id=comment_id,
        resource="comment",
        type="delete",
        originating_connection_id=x_connection_id  # Don't echo to originating connection
    )
    await events.publish(
        event.model_dump(mode="json"),
        channel=f"documents:{document_id}:comments"
    )

    return Response(status_code=204)


@router.post("/{comment_id}/tags/{tag_id}")
async def add_tag_to_comment(
    tag_id: int,
    db: Database,
    events: Events,
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    user: User = Authenticate([Guard.comment_access(None, only_owner=True)]),
    x_connection_id: str | None = Header(None, alias="X-Connection-ID"),
) -> Response:
    """Add a tag to a comment.

    Only the comment owner can add tags to their own comment.
    """
    # Verify tag exists and belongs to the same document as the comment
    tag = db.exec(select(Tag).where(Tag.id == tag_id)).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if tag.document_id != comment.document_id:
        raise HTTPException(status_code=400, detail="Tag does not belong to the same document as the comment")

    # Check if tag is already added to comment
    existing = db.exec(
        select(CommentTag).where(
            CommentTag.comment_id == comment.id,
            CommentTag.tag_id == tag_id
        )
    ).first()
    if existing:
        # Tag already added, just return the comment
        db.refresh(comment)
        return Response(status_code=204)

    # Check if comment has reached max tag limit
    tag_count = db.exec(
        select(func.count(CommentTag.tag_id)).where(CommentTag.comment_id == comment.id)
    ).one()
    if tag_count >= config.MAX_TAGS_PER_COMMENT:
        raise HTTPException(
            status_code=400,
            detail=f"Comment has reached the maximum number of tags ({config.MAX_TAGS_PER_COMMENT})"
        )

    # Add tag to comment
    comment_tag = CommentTag(comment_id=comment.id, tag_id=tag_id)
    db.add(comment_tag)
    db.commit()
    db.refresh(comment)

    # Broadcast update event
    event = Event(
        event_id=uuid4(),
        published_at=datetime.now(),
        payload=CommentRead.model_validate(comment),
        resource_id=comment.id,
        resource="comment",
        type="update",
        originating_connection_id=x_connection_id
    )
    await events.publish(
        event.model_dump(mode="json"),
        channel=f"documents:{comment.document_id}:comments"
    )

    return Response(status_code=204)


@router.delete("/{comment_id}/tags/{tag_id}")
async def remove_tag_from_comment(
    tag_id: int,
    db: Database,
    events: Events,
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    user: User = Authenticate([Guard.comment_access(None, only_owner=True)]),
    x_connection_id: str | None = Header(None, alias="X-Connection-ID"),
) -> Comment:
    """Remove a tag from a comment.

    Only the comment owner can remove tags from their own comment.
    """
    # Find and delete the comment-tag association
    comment_tag = db.exec(
        select(CommentTag).where(
            CommentTag.comment_id == comment.id,
            CommentTag.tag_id == tag_id
        )
    ).first()
    if not comment_tag:
        raise HTTPException(status_code=404, detail="Tag not associated with this comment")

    db.delete(comment_tag)
    db.commit()
    db.refresh(comment)

    # Broadcast update event
    event = Event(
        event_id=uuid4(),
        published_at=datetime.now(),
        payload=CommentRead.model_validate(comment),
        resource_id=comment.id,
        resource="comment",
        type="update",
        originating_connection_id=x_connection_id
    )
    await events.publish(
        event.model_dump(mode="json"),
        channel=f"documents:{comment.document_id}:comments"
    )

    return comment


tags = router.tags
router.tags = []
router.include_router(ReactionRouter, prefix="/{comment_id}")
router.tags = tags