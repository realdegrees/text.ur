# TODO create sharelink models (create update read)

from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

from models.enums import Permission, ReactionType

if TYPE_CHECKING:
    from models.user import UserRead
    
# TODO maybe move these into config
MAX_LABEL_LENGTH = 30

# =========================

class ShareLinkCreate(SQLModel):
    permissions: set[Permission]
    allow_anonymous_access: bool = False
    expires_at: datetime | None = None
    label: str | None = Field(default=None, max_length=MAX_LABEL_LENGTH)

class ShareLinkRead(SQLModel):
    id: int
    permissions: set[Permission]
    expires_at: datetime | None = None
    label: str | None = None
    allow_anonymous_access: bool
    token: str
    author: "UserRead | None"
    group_id: str

class ShareLinkUpdate(SQLModel):
    permissions: set[Permission] | None = None
    expires_at: datetime | None = None
    allow_anonymous_access: bool | None = None
    label: str | None = Field(default=None, max_length=MAX_LABEL_LENGTH)
    rotate_token: bool | None = None
