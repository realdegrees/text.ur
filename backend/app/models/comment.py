from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import Visibility

if TYPE_CHECKING:
    from models.reaction import ReactionRead
    from models.user import UserRead

# TODO maybe move these into config
MAX_COMMENT_CONTENT_LENGTH = 500

class CommentCreate(SQLModel):
    visibility: Visibility
    document_id: str
    parent_id: int | None = None
    content: str | None = Field(default=None, max_length=MAX_COMMENT_CONTENT_LENGTH)
    annotation: dict | None = None
    

class CommentRead(BaseModel):
    id: int
    visibility: Visibility
    user: "UserRead | None"
    annotation: dict | None
    content: str | None
    num_replies: int
    reactions: list["ReactionRead"]

class CommentUpdate(SQLModel):
    visibility: Visibility | None = None
    content: str | None = Field(default=None, max_length=MAX_COMMENT_CONTENT_LENGTH)
    annotation: dict | None = None
    
class CommentDelete(SQLModel):
    id: int
