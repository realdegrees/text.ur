from typing import TYPE_CHECKING

from core.config import (
    MAX_DOCUMENT_DESCRIPTION_LENGTH,
    MAX_DOCUMENT_NAME_LENGTH,
)
from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import DocumentVisibility, ViewMode, Visibility

if TYPE_CHECKING:
    from models.tag import TagRead


class DocumentCreate(SQLModel):
    visibility: DocumentVisibility
    name: str = Field(max_length=MAX_DOCUMENT_NAME_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_DOCUMENT_DESCRIPTION_LENGTH)
    group_id: str

class DocumentRead(BaseModel):
    id: str
    s3_key: str
    name: str
    group_id: str
    visibility: DocumentVisibility
    description: str | None
    view_mode: ViewMode
    tags: list["TagRead"]

class DocumentTransfer(SQLModel):
    group_id: str

class DocumentUpdate(SQLModel):
    visibility: DocumentVisibility | None = None
    view_mode: ViewMode | None = None
    description: str | None = Field(default=None, max_length=MAX_DOCUMENT_DESCRIPTION_LENGTH)
    name: str | None = Field(default=None, max_length=MAX_DOCUMENT_NAME_LENGTH)


class ViewModeChangedEvent(SQLModel):
    """Event payload for view_mode changes - sent to WebSocket clients."""

    document_id: str
    view_mode: ViewMode


class MousePositionInput(SQLModel):
    """Input model for mouse cursor position - sent from clients (without user info)."""

    x: float  # Normalized X position (0-1 relative to PDF page width)
    y: float  # Normalized Y position (0-1 relative to PDF page height)
    page: int  # Page number (1-indexed)
    visible: bool = True  # False when mouse leaves the PDF area


class MousePositionEvent(SQLModel):
    """Event payload for mouse cursor position - broadcasted to WebSocket clients (with user info)."""

    user_id: int
    username: str
    x: float  # Normalized X position (0-1 relative to PDF page width)
    y: float  # Normalized Y position (0-1 relative to PDF page height)
    page: int  # Page number (1-indexed)
    visible: bool = True  # False when mouse leaves the PDF area