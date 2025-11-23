from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import ViewMode, Visibility

if TYPE_CHECKING:
    from models.group import GroupRead
    from models.user import UserRead


class DocumentCreate(SQLModel):
    visibility: Visibility
    name: str = Field(max_length=255)
    group_id: str

class DocumentRead(BaseModel):
    id: str
    s3_key: str
    name: str
    group_id: str
    visibility: Visibility
    view_mode: ViewMode

class DocumentTransfer(SQLModel):
    group_id: str

class DocumentUpdate(SQLModel):
    visibility: Visibility | None = None
    view_mode: ViewMode | None = None
    name: str | None = Field(default=None, max_length=255)


class ViewModeChangedEvent(SQLModel):
    """Event payload for view_mode changes - sent to WebSocket clients."""

    document_id: str
    view_mode: ViewMode


class MousePositionEvent(SQLModel):
    """Event payload for mouse cursor position - sent to WebSocket clients for real-time cursor tracking."""

    user_id: int
    username: str
    x: float  # Normalized X position (0-1 relative to PDF page width)
    y: float  # Normalized Y position (0-1 relative to PDF page height)
    page: int  # Page number (1-indexed)
    visible: bool = True  # False when mouse leaves the PDF area