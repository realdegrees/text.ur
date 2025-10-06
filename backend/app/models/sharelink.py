# TODO create sharelink models (create update read)

from typing import TYPE_CHECKING

from sqlmodel import SQLModel

from models.enums import Permission, ReactionType

if TYPE_CHECKING:
    from models.user import UserRead

# =========================

class ShareLinkCreate(SQLModel):
    permissions: set[Permission]
    expires_at: str | None = None
    label: str | None = None

class ShareLinkRead(SQLModel):
    id: int
    permissions: set[Permission]
    expires_at: str | None = None
    label: str | None = None
    token: str

class ShareLinkUpdate(SQLModel):
    permissions: set[Permission] | None = None
    expires_at: str | None = None
    label: str | None = None
    rotate_token: bool | None = None
