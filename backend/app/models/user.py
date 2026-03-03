import re
from datetime import datetime

from pydantic import (
    BaseModel as PydanticBaseModel,
)
from pydantic import (
    EmailStr,
    field_validator,
)
from sqlmodel import Field, SQLModel

from models.base import BaseModel

# TODO maybe move these into config
MAX_USERNAME_LENGTH = 20
MIN_USERNAME_LENGTH = 3
MAX_FIRST_NAME_LENGTH = 50
MAX_LAST_NAME_LENGTH = 50
MAX_EMAIL_LENGTH = 255
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

_PASSWORD_RULES = [
    (re.compile(r"[a-z]"), "lowercase letter"),
    (re.compile(r"[A-Z]"), "uppercase letter"),
    (re.compile(r"\d"), "digit"),
    (re.compile(r"[^a-zA-Z0-9]"), "special character"),
]


def validate_password_policy(password: str) -> None:
    """Raise ValueError if password does not meet complexity rules."""
    missing = [name for pattern, name in _PASSWORD_RULES if not pattern.search(password)]
    if missing:
        raise ValueError("Password must contain at least one " + ", one ".join(missing))


class UserCreate(SQLModel):
    token: str | None = None
    username: str = Field(
        min_length=MIN_USERNAME_LENGTH,
        max_length=MAX_USERNAME_LENGTH,
    )
    password: str | None = Field(
        default=None,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
    )
    email: EmailStr | None = Field(default=None, max_length=MAX_EMAIL_LENGTH)
    first_name: str | None = Field(default=None, max_length=MAX_FIRST_NAME_LENGTH)
    last_name: str | None = Field(default=None, max_length=MAX_LAST_NAME_LENGTH)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        """Normalize email to lowercase."""
        if v is not None:
            return v.lower().strip()
        return v

    @field_validator("password", mode="after")
    @classmethod
    def validate_password_strength(cls, v: str | None) -> str | None:
        """Enforce password complexity requirements."""
        if v is None:
            return v
        validate_password_policy(v)
        return v


class UserRead(BaseModel):
    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None
    is_guest: bool = False


class UserPrivate(UserRead):
    email: str | None = None


class UserUpdate(SQLModel):
    username: str | None = Field(
        default=None,
        min_length=MIN_USERNAME_LENGTH,
        max_length=MAX_USERNAME_LENGTH,
    )
    new_password: str | None = Field(
        default=None,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
    )
    old_password: str | None = Field(default=None, max_length=MAX_PASSWORD_LENGTH)
    first_name: str | None = Field(default=None, max_length=MAX_FIRST_NAME_LENGTH)
    last_name: str | None = Field(default=None, max_length=MAX_LAST_NAME_LENGTH)

    @field_validator("new_password", mode="after")
    @classmethod
    def validate_password_strength(cls, v: str | None) -> str | None:
        """Enforce password complexity requirements."""
        if v is None:
            return v
        validate_password_policy(v)
        return v


class PasswordResetVerify(SQLModel):
    """Schema for password reset verification."""

    password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
    )

    @field_validator("password", mode="after")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce password complexity requirements."""
        validate_password_policy(v)
        return v


# GDPR data export models (Art. 20 — right to data portability)


class ExportProfile(PydanticBaseModel):
    """User profile data for export."""

    username: str
    email: str | None
    first_name: str | None
    last_name: str | None
    is_guest: bool
    verified: bool
    created_at: datetime
    updated_at: datetime


class ExportMembership(PydanticBaseModel):
    """Membership record for export."""

    group_name: str
    is_owner: bool
    accepted: bool
    permissions: list[str]
    joined_at: datetime


class ExportComment(PydanticBaseModel):
    """Comment record for export."""

    document_name: str
    group_name: str
    content: str | None
    annotation: dict | None = None
    visibility: str
    created_at: datetime
    updated_at: datetime


class ExportReaction(PydanticBaseModel):
    """Reaction record for export."""

    emoji: str
    comment_content_preview: str | None
    created_at: datetime


class ExportTaskResponse(PydanticBaseModel):
    """Task response record for export."""

    document_name: str
    task_question: str
    answer: dict
    is_correct: bool
    attempts: int
    created_at: datetime


class UserDataExport(PydanticBaseModel):
    """Complete user data export for GDPR portability."""

    exported_at: datetime
    profile: ExportProfile
    memberships: list[ExportMembership]
    comments: list[ExportComment]
    reactions: list[ExportReaction]
    task_responses: list[ExportTaskResponse]
