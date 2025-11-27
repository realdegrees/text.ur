from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import Permission

if TYPE_CHECKING:
    from models.sharelink import ShareLinkReadPublic
    from models.user import UserRead

MAX_GROUP_NAME_LENGTH = 80

# =========================


class GroupCreate(SQLModel):
    name: str = Field(max_length=MAX_GROUP_NAME_LENGTH)
    default_permissions: list[Permission]


class GroupRead(BaseModel):
    id: str
    name: str
    member_count: int
    owner: "UserRead | None"
    default_permissions: list[Permission]


class GroupUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=MAX_GROUP_NAME_LENGTH)
    default_permissions: list[Permission] | None = None


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
    share_link: "ShareLinkReadPublic | None"
