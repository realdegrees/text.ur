from typing import TYPE_CHECKING

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import Visibility

if TYPE_CHECKING:
    from models.reaction import ReactionRead
    from models.tag import TagRead
    from models.user import UserRead

# TODO maybe move these into config
MAX_COMMENT_CONTENT_LENGTH = 500


def sanitize_content(value: str | None) -> str | None:
    """Remove null bytes and other problematic characters from content."""
    if value is None:
        return None
    # Remove null bytes which PostgreSQL doesn't accept
    value = value.replace('\x00', '')
    # Remove other control characters except newlines and tabs
    value = ''.join(c for c in value if c in '\n\t\r' or (ord(c) >= 32 or ord(c) >= 127))
    return value

class Annotation(SQLModel):
    page_number: int
    text: str
    rects: list[dict]


class CommentCreate(SQLModel):
    visibility: Visibility
    document_id: str
    parent_id: int | None = None
    content: str | None = Field(default=None, max_length=MAX_COMMENT_CONTENT_LENGTH)
    annotation: dict | None = None

    @field_validator('content', mode='before')
    @classmethod
    def clean_content(cls, v: str | None) -> str | None:
        """Sanitize content to remove problematic characters."""
        return sanitize_content(v)


class CommentRead(BaseModel):
    id: int
    visibility: Visibility
    user: "UserRead | None"
    parent_id: int | None
    annotation: dict | None
    content: str | None
    num_replies: int
    reactions: list["ReactionRead"]
    tags: list["TagRead"]

class CommentUpdate(SQLModel):
    visibility: Visibility | None = None
    content: str | None = Field(default=None, max_length=MAX_COMMENT_CONTENT_LENGTH)
    annotation: dict | None = None

    @field_validator('content', mode='before')
    @classmethod
    def clean_content(cls, v: str | None) -> str | None:
        """Sanitize content to remove problematic characters."""
        return sanitize_content(v)


class CommentTagsUpdate(SQLModel):
    """Model for bulk updating comment tags with explicit ordering."""
    
    tag_ids: list[int] = Field(description="Ordered list of tag IDs to associate with the comment")


class CommentDelete(SQLModel):
    id: int
