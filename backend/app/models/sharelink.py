from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from models.enums import Permission

if TYPE_CHECKING:
    from models.group import GroupRead
    from models.user import UserRead

# TODO maybe move these into config
MAX_LABEL_LENGTH = 30


def _validate_tz_aware(
    v: datetime | None,
) -> datetime | None:
    """Reject naive datetimes — requires timezone info."""
    if v is not None and v.tzinfo is None:
        raise ValueError(
            "expires_at must include timezone info "
            "(e.g. '2025-09-13T14:30:00Z')"
        )
    return v


# =========================


class ShareLinkCreate(SQLModel):
    """Schema for creating a share link."""

    permissions: set[Permission]
    allow_anonymous_access: bool = False
    expires_at: datetime | None = None
    label: str | None = Field(default=None, max_length=MAX_LABEL_LENGTH)

    _validate_expires_at = field_validator("expires_at")(
        _validate_tz_aware
    )
    
class ShareLinkReadBase(SQLModel):
    id: int
    permissions: set[Permission]
    expires_at: datetime | None = None
    allow_anonymous_access: bool
    created_at: datetime
    updated_at: datetime

class ShareLinkRead(ShareLinkReadBase):
    label: str | None = None
    token: str
    author: "UserRead | None"
    group_id: str
    num_memberships: int
    
class ShareLinkReadNoToken(ShareLinkReadBase):
    group_id: str
    
class ShareLinkReadFromToken(ShareLinkReadBase):
    """Read model for share link fetched via token, includes group info and the token itself."""
    
    group: "GroupRead"
    token: str

class ShareLinkUpdate(SQLModel):
    """Schema for updating a share link."""

    permissions: set[Permission] | None = None
    expires_at: datetime | None = None
    allow_anonymous_access: bool | None = None
    label: str | None = Field(default=None, max_length=MAX_LABEL_LENGTH)
    rotate_token: bool | None = None

    _validate_expires_at = field_validator("expires_at")(
        _validate_tz_aware
    )
