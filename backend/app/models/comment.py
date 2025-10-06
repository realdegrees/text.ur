from typing import TYPE_CHECKING

from sqlmodel import SQLModel

from models.base import BaseModel
from models.enums import Visibility

if TYPE_CHECKING:
    from models.reaction import ReactionRead
    from models.user import UserRead

class CommentCreate(SQLModel):
    visibility: Visibility
    document_id: int
    parent_id: int | None = None
    content: str | None = None
    annotation: dict | None = None
    

class CommentRead(BaseModel):
    id: int
    visibility: Visibility
    user: "UserRead | None"
    annotation: dict
    content: str | None
    replies: list["CommentRead"]
    reactions: list["ReactionRead"]

class CommentUpdate(SQLModel):
    visibility: Visibility | None = None
    content: str | None = None
    annotation: dict | None = None
    
class CommentDelete(SQLModel):
    id: int
