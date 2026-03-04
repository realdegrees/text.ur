from pydantic import field_validator
from sqlmodel import Field, SQLModel

from models.base import BaseModel


class TagCreate(SQLModel):
    """Model for creating a new tag."""

    label: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=200)
    color: str = Field(max_length=7)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate that color is a valid hex code."""
        if not v.startswith("#"):
            raise ValueError("Color must start with #")
        if len(v) != 7:
            raise ValueError("Color must be in format #RRGGBB")
        try:
            int(v[1:], 16)
        except ValueError as e:
            raise ValueError("Color must be a valid hex code") from e
        return v.upper()


class TagUpdate(SQLModel):
    """Model for updating an existing tag."""

    label: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, max_length=7)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        """Validate that color is a valid hex code."""
        if v is None:
            return None
        if not v.startswith("#"):
            raise ValueError("Color must start with #")
        if len(v) != 7:
            raise ValueError("Color must be in format #RRGGBB")
        try:
            int(v[1:], 16)
        except ValueError as e:
            raise ValueError("Color must be a valid hex code") from e
        return v.upper()


class TagRead(BaseModel):
    """Model for reading tag data."""

    id: int
    document_id: str
    label: str
    description: str | None
    color: str
