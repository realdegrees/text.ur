"""Reaction schemas for API request/response models."""

from typing import TYPE_CHECKING, Any

from pydantic import model_validator
from sqlmodel import SQLModel

from models.enums import Emoji

if TYPE_CHECKING:
    from models.user import UserRead


# Default reactions seeded for every new group.
# Used by both the Alembic migration backfill and ``create_group``.
DEFAULT_REACTIONS: list[dict] = [
    {
        "emoji": Emoji.THUMBS_UP,
        "points": 2,
        "admin_points": 4,
        "giver_points": 2,
        "order": 0,
    },
    {
        "emoji": Emoji.SMILE,
        "points": 2,
        "admin_points": 4,
        "giver_points": 2,
        "order": 1,
    },
    {
        "emoji": Emoji.HEART,
        "points": 2,
        "admin_points": 4,
        "giver_points": 2,
        "order": 2,
    },
    {
        "emoji": Emoji.FIRE,
        "points": 2,
        "admin_points": 4,
        "giver_points": 2,
        "order": 3,
    },
    {
        "emoji": Emoji.PINCH,
        "points": 2,
        "admin_points": 4,
        "giver_points": 2,
        "order": 4,
    },
    {
        "emoji": Emoji.NERD,
        "points": 2,
        "admin_points": 4,
        "giver_points": 2,
        "order": 5,
    },
]

# Mapping from old ReactionType string values to Emoji for migration.
OLD_TYPE_TO_EMOJI: dict[str, Emoji] = {
    "thumbs_up": Emoji.THUMBS_UP,
    "smile": Emoji.SMILE,
    "heart": Emoji.HEART,
    "fire": Emoji.FIRE,
    "pinch": Emoji.PINCH,
    "nerd": Emoji.NERD,
}

# =========================


class ReactionCreate(SQLModel):
    """Create a reaction using a group_reaction_id."""

    group_reaction_id: int


class ReactionRead(SQLModel):
    """Read schema for a reaction, including emoji info."""

    group_reaction_id: int
    emoji: Emoji
    user: "UserRead"
    comment_id: int

    @model_validator(mode="before")
    @classmethod
    def flatten_group_reaction(
        cls,
        data: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """Pull emoji from the group_reaction relationship.

        When validating from an ORM ``Reaction`` object, the
        ``emoji`` field lives on the related ``GroupReaction``,
        not on ``Reaction`` itself.
        """
        if hasattr(data, "group_reaction"):
            gr = data.group_reaction
            if gr is not None:
                return {
                    "group_reaction_id": data.group_reaction_id,
                    "emoji": gr.emoji,
                    "user": data.user,
                    "comment_id": data.comment_id,
                }
        return data


class GroupReactionCreate(SQLModel):
    """Create a new reaction emoji for a group."""

    emoji: Emoji
    points: int = 2
    admin_points: int = 4
    giver_points: int = 2
    order: int = 0


class GroupReactionUpdate(SQLModel):
    """Update a group reaction's settings."""

    points: int | None = None
    admin_points: int | None = None
    giver_points: int | None = None
    order: int | None = None


class GroupReactionRead(SQLModel):
    """Read schema for a group reaction config."""

    id: int
    emoji: Emoji
    points: int
    admin_points: int
    giver_points: int
    order: int
