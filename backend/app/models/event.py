
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from sqlmodel import Field, SQLModel


# TODO maybe add a unique event ID identifier that must be provided and is validated as a uuid
class Event[Payload: PydanticBaseModel](PydanticBaseModel):
    """Represents an event to be published to/from WebSocket clients."""

    event_id: UUID
    published_at: datetime = Field(default_factory=datetime.now)
    payload: Payload | None
    resource_id: int | None
    resource: str | None
    type: Literal["create", "update", "delete", "custom"]


# TODO structured event error model