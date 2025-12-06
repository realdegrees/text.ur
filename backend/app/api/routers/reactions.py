from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.resource import Resource
from fastapi import Body, Response
from models.enums import Permission
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

# region Groups

@router.post("/", response_model=ReactionRead)
async def add_reaction(
    db: Database,
    user: User = Authenticate(guards=[Guard.comment_access({Permission.ADD_REACTIONS})]),
    reaction_create: ReactionCreate = Body(...),
    comment: Comment = Resource(Comment, param_alias="comment_id")
) -> ReactionRead:
    """Create a new reaction."""
    reaction = Reaction(**reaction_create.model_dump(), user_id=user.id, comment_id=comment.id)
    db.add(reaction)
    await db.commit()
    return reaction

@router.delete("/{reaction_id}")
async def remove_reaction(
    db: Database,
    user: User = Authenticate(guards=[Guard.comment_access({Permission.REMOVE_REACTIONS})]),
    comment: Comment = Resource(Comment, param_alias="comment_id")
) -> dict[str, bool]:
    """Delete a reaction."""
    result = await db.exec(
        select(Reaction).where(
            Reaction.user_id == user.id,
            Reaction.comment_id == comment.id
        )
    )
    reaction = result.first()
    if reaction is None:
        return Response(status_code=404, content="Reaction not found")

    await db.delete(reaction)
    await db.commit()
    return Response(status_code=204)
