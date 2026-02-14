
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    from models.comment import CommentRead


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


# TODO maybe add a unique event ID identifier that must be provided and is validated as a uuid
class Event[Payload: PydanticBaseModel](PydanticBaseModel):
    """Represents an event to be published to/from WebSocket clients."""

    event_id: UUID
    published_at: datetime = Field(default_factory=_utcnow)
    payload: Payload | None
    resource_id: int | str | None
    resource: str | None
    type: str
    originating_connection_id: str | None = None  # Connection that triggered this event (to avoid echo)


# Concrete event types for type generation
class CommentEvent(PydanticBaseModel):
    """Comment WebSocket event - concrete type for frontend type generation."""

    event_id: UUID
    published_at: datetime = Field(default_factory=_utcnow)
    payload: "CommentRead | None"
    resource_id: int | None
    resource: str | None
    type: str
    originating_connection_id: str | None = None


# TODO structured event error model