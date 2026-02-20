"""Score models for user gamification within groups."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

from models.enums import Emoji

if TYPE_CHECKING:
    from models.reaction import GroupReactionRead


class ReactionBreakdownItem(SQLModel):
    """Per-emoji breakdown of received/given reactions and points."""

    group_reaction_id: int
    emoji: str
    received_count: int
    received_from_admin: int
    received_points: int
    given_count: int
    given_points: int


class ScoreBreakdown(SQLModel):
    """Detailed breakdown of a user's score components."""

    highlights: int
    highlight_points: int
    comments: int
    comment_points: int
    tags: int
    tag_points: int
    reactions_received: int
    reactions_received_from_admin: int
    reaction_received_points: int
    reactions_given: int
    reaction_given_points: int
    reaction_breakdown: list[ReactionBreakdownItem] = []


class ScoreRead(SQLModel):
    """User score for a specific group, with caching metadata."""

    total: int
    breakdown: ScoreBreakdown
    cached_at: datetime


class ScoreConfigRead(SQLModel):
    """Read schema for per-group scoring configuration."""

    group_id: str
    highlight_points: int
    comment_points: int
    tag_points: int
    reactions: list["GroupReactionRead"]


class ScoreConfigUpdate(SQLModel):
    """Update schema for per-group scoring configuration."""

    highlight_points: int | None = None
    comment_points: int | None = None
    tag_points: int | None = None
