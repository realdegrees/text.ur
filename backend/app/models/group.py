from typing import TYPE_CHECKING

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import Permission

if TYPE_CHECKING:
    from models.sharelink import ShareLinkReadNoToken
    from models.user import UserRead

MAX_GROUP_NAME_LENGTH = 80

# =========================


def _strip_and_validate_name(v: str) -> str:
    """Strip whitespace from group name."""
    return v.strip()


def _reject_administrator(
    v: list[Permission],
) -> list[Permission]:
    """Reject ADMINISTRATOR in default_permissions."""
    if Permission.ADMINISTRATOR in v:
        msg = "ADMINISTRATOR cannot be included in default_permissions"
        raise ValueError(msg)
    return v


class GroupCreate(SQLModel):
    name: str = Field(min_length=1, max_length=MAX_GROUP_NAME_LENGTH)
    default_permissions: list[Permission]

    _strip_name = field_validator("name", mode="before")(_strip_and_validate_name)
    _check_perms = field_validator("default_permissions", mode="after")(_reject_administrator)


class GroupRead(BaseModel):
    id: str
    name: str
    member_count: int
    document_count: int
    owner: "UserRead | None"
    default_permissions: list[Permission]


class GroupUpdate(SQLModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_GROUP_NAME_LENGTH,
    )
    default_permissions: list[Permission] | None = None

    _strip_name = field_validator("name", mode="before")(_strip_and_validate_name)
    _check_perms = field_validator("default_permissions", mode="after")(_reject_administrator)


class GroupTransfer(SQLModel):
    user_id: int


# =========================


class MembershipCreate(SQLModel):
    user_id: int


class MembershipPermissionUpdate(SQLModel):
    permissions: set[Permission]


# =========================


class MembershipRead(SQLModel):
    permissions: list[Permission]
    user: "UserRead"
    group: GroupRead
    is_owner: bool
    accepted: bool
    share_link: "ShareLinkReadNoToken | None"
