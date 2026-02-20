from datetime import UTC, datetime
from uuid import uuid4

from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.events import Events
from api.dependencies.resource import Resource
from core.app_exception import AppException
from fastapi import Body, Header, Response
from models.comment import CommentRead
from models.enums import AppErrorCode, Permission
from models.event import Event
from models.reaction import ReactionCreate, ReactionRead
from models.tables import Comment, Reaction, User
from sqlmodel import select
from util.api_router import APIRouter
from util.queries import Guard

# ! Do not use as a standalone router, this is included in the comments router!
router = APIRouter(
    prefix="/reactions",
    tags=["Reactions"],
)


async def _publish_reaction_event(
    db: Database,
    events: Events,
    comment: Comment,
    connection_id: str | None,
) -> None:
    """Refresh the comment and publish an update event."""
    await db.refresh(comment, attribute_names=["reactions"])
    event = Event(
        event_id=uuid4(),
        published_at=datetime.now(UTC),
        payload=CommentRead.model_validate(comment),
        resource_id=comment.id,
        resource="comment",
        type="update",
        originating_connection_id=connection_id,
    )
    await events.publish(
        event.model_dump(mode="json"),
        channel=f"documents:{comment.document_id}:comments",
    )


@router.post("/", response_model=ReactionRead)
async def add_reaction(
    db: Database,
    events: Events,
    user: User = Authenticate(
        guards=[Guard.comment_access({Permission.ADD_REACTIONS})]
    ),
    reaction_create: ReactionCreate = Body(...),
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    x_connection_id: str | None = Header(
        None, alias="X-Connection-ID"
    ),
) -> ReactionRead:
    """Create or update a reaction on a root-level comment."""
    if comment.user_id == user.id:
        raise AppException(
            status_code=403,
            error_code=AppErrorCode.SELF_REACTION,
            detail="You cannot react to your own comment",
        )

    if comment.parent_id is not None:
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.REPLY_REACTION,
            detail=(
                "Reactions are only allowed on root-level comments"
            ),
        )

    # Upsert: update type if reaction already exists
    result = await db.exec(
        select(Reaction).where(
            Reaction.user_id == user.id,
            Reaction.comment_id == comment.id,
        )
    )
    existing = result.first()

    if existing:
        await db.merge(existing)
        existing.type = reaction_create.type
        await db.commit()
        await db.refresh(existing)
        await _publish_reaction_event(
            db, events, comment, x_connection_id
        )
        return existing

    reaction = Reaction(
        **reaction_create.model_dump(),
        user_id=user.id,
        comment_id=comment.id,
    )
    db.add(reaction)
    await db.commit()
    await db.refresh(reaction)
    await _publish_reaction_event(
        db, events, comment, x_connection_id
    )
    return reaction


@router.delete("/")
async def remove_reaction(
    db: Database,
    events: Events,
    user: User = Authenticate(
        guards=[Guard.comment_access({Permission.ADD_REACTIONS})]
    ),
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    x_connection_id: str | None = Header(
        None, alias="X-Connection-ID"
    ),
) -> Response:
    """Remove the current user's reaction from a comment."""
    result = await db.exec(
        select(Reaction).where(
            Reaction.user_id == user.id,
            Reaction.comment_id == comment.id,
        )
    )
    reaction = result.first()
    if reaction is None:
        return Response(status_code=404)

    await db.delete(reaction)
    await db.commit()
    await _publish_reaction_event(
        db, events, comment, x_connection_id
    )
    return Response(status_code=204)


@router.delete("/{user_id}")
async def remove_user_reaction(
    db: Database,
    events: Events,
    user_id: int,
    admin: User = Authenticate(
        guards=[
            Guard.comment_access({Permission.REMOVE_REACTIONS})
        ]
    ),
    comment: Comment = Resource(Comment, param_alias="comment_id"),
    x_connection_id: str | None = Header(
        None, alias="X-Connection-ID"
    ),
) -> Response:
    """Remove another user's reaction (admin/permission required)."""
    result = await db.exec(
        select(Reaction).where(
            Reaction.user_id == user_id,
            Reaction.comment_id == comment.id,
        )
    )
    reaction = result.first()
    if reaction is None:
        return Response(status_code=404)

    await db.delete(reaction)
    await db.commit()
    await _publish_reaction_event(
        db, events, comment, x_connection_id
    )
    return Response(status_code=204)
