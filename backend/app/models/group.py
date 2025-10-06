from typing import TYPE_CHECKING

from sqlmodel import SQLModel

from models.base import BaseModel
from models.enums import Permission

if TYPE_CHECKING:
    from models.user import UserRead

# =========================

class GroupCreate(SQLModel):
    name: str
    default_permissions: list[Permission]

class GroupRead(BaseModel):
    id: int
    name: str
    member_count: int
    owner: "UserRead | None"
    
class GroupUpdate(SQLModel):
    name: str | None = None
    default_permissions: list[Permission] | None = None
    
class GroupTransfer(SQLModel):
    user_id: int
    
# =========================

class MembershipCreate(SQLModel):
    user_id: int
    
class MembershipPermissionUpdate(SQLModel):
    permissions: set[Permission]
    

# =========================

class GroupMembershipRead(SQLModel):
    permissions: list[Permission]
    user: "UserRead"
    is_owner: bool
    accepted: bool
    group_id: int

class UserMembershipRead(SQLModel):
    permissions: list[Permission]
    group: GroupRead
    is_owner: bool
    accepted: bool
    user_id: int

