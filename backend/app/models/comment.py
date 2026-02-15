from typing import TYPE_CHECKING, Any

from core.config import MAX_COMMENT_LENGTH
from core.logger import get_logger
from pydantic import field_validator
from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import Visibility

if TYPE_CHECKING:
    from models.reaction import ReactionRead
    from models.tag import TagRead
    from models.user import UserRead

logger = get_logger("app")

# TODO maybe move these into config


def sanitize_content(value: str | None) -> str | None:
    """Remove null bytes and other problematic characters from content."""
    if value is None:
        return None
    # Remove null bytes which PostgreSQL doesn't accept
    value = value.replace("\x00", "")
    # Remove other control characters except newlines and tabs
    value = "".join(c for c in value if c in "\n\t\r" or ord(c) >= 32)
    return value


class BoundingBox(SQLModel):
    page_number: int
    x: float
    y: float
    width: float
    height: float


class Annotation(SQLModel):
    text: str
    boundingBoxes: list[BoundingBox]


class CommentCreate(SQLModel):
    visibility: Visibility
    document_id: str
    parent_id: int | None = None
    content: str | None = Field(default=None, max_length=MAX_COMMENT_LENGTH)
    annotation: Annotation | None = None

    @field_validator("content", mode="before")
    @classmethod
    def clean_content(cls, v: str | None) -> str | None:
        """Sanitize content to remove problematic characters."""
        return sanitize_content(v)


class CommentRead(BaseModel):
    id: int
    visibility: Visibility
    user: "UserRead | None"
    parent_id: int | None
    annotation: Annotation | None
    content: str | None
    num_replies: int
    reactions: list["ReactionRead"]
    tags: list["TagRead"]

    @field_validator("annotation", mode="before")
    @classmethod
    def sanitize_annotation(
        cls,
        v: Any,  # noqa: ANN401
    ) -> Annotation | None:
        """Coerce malformed annotation data to None.

        Guards against corrupted JSONB data (e.g. from faulty
        migrations) that would otherwise cause a
        ResponseValidationError (500) for the entire response.
        """
        if v is None:
            return None
        if isinstance(v, dict):
            if not v or v.get("text") is None:
                if v:
                    logger.warning(
                        "Corrupted annotation data coerced to None: %s",
                        v,
                    )
                return None
        return v


class CommentUpdate(SQLModel):
    visibility: Visibility | None = None
    content: str | None = Field(default=None, max_length=MAX_COMMENT_LENGTH)
    annotation: Annotation | None = None

    @field_validator("content", mode="before")
    @classmethod
    def clean_content(cls, v: str | None) -> str | None:
        """Sanitize content to remove problematic characters."""
        return sanitize_content(v)


class CommentTagsUpdate(SQLModel):
    """Model for bulk updating comment tags with explicit ordering."""

    tag_ids: list[int] = Field(
        description="Ordered list of tag IDs to associate with the comment"
    )


class CommentDelete(SQLModel):
    id: int
