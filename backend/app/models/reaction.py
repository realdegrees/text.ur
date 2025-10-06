from typing import TYPE_CHECKING

from sqlmodel import SQLModel

from models.enums import ReactionType

if TYPE_CHECKING:
    from models.user import UserRead

# =========================

class ReactionCreate(SQLModel):
    type: ReactionType

class ReactionRead(SQLModel):
    type: ReactionType
    user: "UserRead"
    comment_id: int
