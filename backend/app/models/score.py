"""Score models for user gamification within groups."""

from datetime import datetime

from sqlmodel import SQLModel


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


class ScoreRead(SQLModel):
    """User score for a specific group, with caching metadata."""

    total: int
    breakdown: ScoreBreakdown
    cached_at: datetime
