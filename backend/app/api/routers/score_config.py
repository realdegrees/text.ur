"""Endpoints for managing per-group scoring configuration and reactions."""

from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.resource import Resource
from core.app_exception import AppException
from fastapi import Body, Response
from models.enums import AppErrorCode, Permission
from models.reaction import (
    GroupReactionCreate,
    GroupReactionRead,
    GroupReactionUpdate,
)
from models.score import ScoreConfigRead, ScoreConfigUpdate
from models.tables import Group, GroupReaction, ScoreConfig, User
from sqlmodel import select
from util.api_router import APIRouter
from util.cache import invalidate_group_scores
from util.queries import Guard

router = APIRouter(
    tags=["Score Configuration"],
)


async def _build_score_config_read(
    db: Database,
    config: ScoreConfig,
) -> ScoreConfigRead:
    """Build a full ScoreConfigRead including the group's reactions."""
    result = await db.exec(
        select(GroupReaction)
        .where(GroupReaction.group_id == config.group_id)
        .order_by(GroupReaction.order)
    )
    reactions = result.all()

    return ScoreConfigRead(
        group_id=config.group_id,
        highlight_points=config.highlight_points,
        comment_points=config.comment_points,
        tag_points=config.tag_points,
        reactions=[GroupReactionRead.model_validate(r) for r in reactions],
    )


# region ScoreConfig


@router.get("/score-config", response_model=ScoreConfigRead)
async def get_score_config(
    db: Database,
    _: User = Authenticate([Guard.group_access()]),
    group: Group = Resource(Group, param_alias="group_id"),
) -> ScoreConfigRead:
    """Get the scoring configuration for a group."""
    result = await db.exec(
        select(ScoreConfig).where(ScoreConfig.group_id == group.id)
    )
    config = result.first()
    if config is None:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Score configuration not found",
        )

    return await _build_score_config_read(db, config)


@router.patch("/score-config", response_model=ScoreConfigRead)
async def update_score_config(
    db: Database,
    update: ScoreConfigUpdate = Body(...),
    _: User = Authenticate(
        guards=[Guard.group_access({Permission.ADMINISTRATOR})]
    ),
    group: Group = Resource(Group, param_alias="group_id"),
) -> ScoreConfigRead:
    """Update the scoring configuration for a group.

    This retroactively affects all user scores.
    """
    result = await db.exec(
        select(ScoreConfig).where(ScoreConfig.group_id == group.id)
    )
    config = result.first()
    if config is None:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Score configuration not found",
        )

    await db.merge(config)
    config.sqlmodel_update(update.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(config)

    await invalidate_group_scores(group.id)

    return await _build_score_config_read(db, config)


# endregion

# region GroupReaction


@router.get("/reactions", response_model=list[GroupReactionRead])
async def list_group_reactions(
    db: Database,
    _: User = Authenticate([Guard.group_access()]),
    group: Group = Resource(Group, param_alias="group_id"),
) -> list[GroupReactionRead]:
    """List all available reaction emojis for a group."""
    result = await db.exec(
        select(GroupReaction)
        .where(GroupReaction.group_id == group.id)
        .order_by(GroupReaction.order)
    )
    return [GroupReactionRead.model_validate(r) for r in result.all()]


@router.post(
    "/reactions",
    response_model=GroupReactionRead,
    status_code=201,
)
async def create_group_reaction(
    db: Database,
    data: GroupReactionCreate = Body(...),
    _: User = Authenticate(
        guards=[Guard.group_access({Permission.ADMINISTRATOR})]
    ),
    group: Group = Resource(Group, param_alias="group_id"),
) -> GroupReactionRead:
    """Add a new reaction emoji to a group."""
    # Check for duplicate emoji in group
    result = await db.exec(
        select(GroupReaction).where(
            GroupReaction.group_id == group.id,
            GroupReaction.emoji == data.emoji,
        )
    )
    if result.first() is not None:
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.INVALID_INPUT,
            detail="This emoji is already configured for the group",
        )

    reaction = GroupReaction(group_id=group.id, **data.model_dump())
    db.add(reaction)
    await db.commit()
    await db.refresh(reaction)
    return GroupReactionRead.model_validate(reaction)


@router.patch(
    "/reactions/{reaction_id}",
    response_model=GroupReactionRead,
)
async def update_group_reaction(
    db: Database,
    reaction_id: int,
    update: GroupReactionUpdate = Body(...),
    _: User = Authenticate(
        guards=[Guard.group_access({Permission.ADMINISTRATOR})]
    ),
    group: Group = Resource(Group, param_alias="group_id"),
) -> GroupReactionRead:
    """Update a group reaction's points or order."""
    result = await db.exec(
        select(GroupReaction).where(
            GroupReaction.id == reaction_id,
            GroupReaction.group_id == group.id,
        )
    )
    reaction = result.first()
    if reaction is None:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Group reaction not found",
        )

    await db.merge(reaction)
    reaction.sqlmodel_update(update.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(reaction)

    await invalidate_group_scores(group.id)

    return GroupReactionRead.model_validate(reaction)


@router.delete("/reactions/{reaction_id}")
async def delete_group_reaction(
    db: Database,
    reaction_id: int,
    _: User = Authenticate(
        guards=[Guard.group_access({Permission.ADMINISTRATOR})]
    ),
    group: Group = Resource(Group, param_alias="group_id"),
) -> Response:
    """Delete a group reaction.

    This CASCADE-deletes all user reactions of this type and
    retroactively affects scores. The frontend should require
    double confirmation before calling this endpoint.
    """
    result = await db.exec(
        select(GroupReaction).where(
            GroupReaction.id == reaction_id,
            GroupReaction.group_id == group.id,
        )
    )
    reaction = result.first()
    if reaction is None:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Group reaction not found",
        )

    await db.delete(reaction)
    await db.commit()

    await invalidate_group_scores(group.id)

    return Response(status_code=204)


# endregion
