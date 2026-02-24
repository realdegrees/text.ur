"""Task schemas for API request/response models."""

from typing import Any, Self

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import AnswerType, StringMatchMode

# ---------------------
# Task Option schemas
# ---------------------


class TaskOptionCreate(SQLModel):
    """Create schema for a multiple-choice option."""

    label: str = Field(max_length=200)
    is_correct: bool = False
    order: int = Field(default=0, ge=0)


class TaskOptionRead(BaseModel):
    """Admin read schema for a task option (includes correctness)."""

    id: int
    label: str
    is_correct: bool
    order: int


class TaskOptionMemberRead(SQLModel):
    """Member read schema for a task option (no correctness info)."""

    id: int
    label: str
    order: int


# ---------------------
# Shared validation
# ---------------------


def _validate_answer_type_fields(
    answer_type: AnswerType,
    options: list[TaskOptionCreate] | None,
    correct_string_answer: str | None,
    correct_number_answer: float | None,
) -> None:
    """Validate that answer-type-specific fields are consistent.

    Raises ValueError when the provided fields don't match
    what the answer_type requires (e.g. MC needs >= 2 options).
    """
    if answer_type == AnswerType.MULTIPLE_CHOICE:
        resolved = options or []
        if len(resolved) < 2:
            raise ValueError(
                "Multiple choice tasks require at least 2 options."
            )
        if not any(o.is_correct for o in resolved):
            raise ValueError(
                "At least one option must be marked as correct."
            )
    elif answer_type == AnswerType.STRING:
        if not correct_string_answer:
            raise ValueError(
                "String tasks require a correct_string_answer."
            )
    elif answer_type == AnswerType.NUMBER:
        if correct_number_answer is None:
            raise ValueError(
                "Number tasks require a correct_number_answer."
            )


# ---------------------
# Task schemas
# ---------------------

MAX_TASKS_PER_DOCUMENT = 50


class TaskCreate(SQLModel):
    """Create schema for a document task."""

    question: str = Field(max_length=500, min_length=1)
    answer_type: AnswerType
    correct_string_answer: str | None = Field(
        default=None, max_length=255
    )
    correct_number_answer: float | None = None
    number_tolerance: float | None = Field(default=None, ge=0)
    string_match_mode: StringMatchMode = StringMatchMode.CASE_INSENSITIVE
    points: int = Field(default=1, ge=0)
    order: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=1, ge=1)
    options: list[TaskOptionCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_answer_config(self) -> Self:
        """Validate that the correct answer fields match the answer type."""
        _validate_answer_type_fields(
            self.answer_type,
            self.options,
            self.correct_string_answer,
            self.correct_number_answer,
        )
        return self


class TaskUpdate(SQLModel):
    """Update schema for a document task (all fields optional)."""

    question: str | None = Field(default=None, max_length=500)
    answer_type: AnswerType | None = None
    correct_string_answer: str | None = Field(
        default=None, max_length=255
    )
    correct_number_answer: float | None = None
    number_tolerance: float | None = Field(default=None, ge=0)
    string_match_mode: StringMatchMode | None = None
    points: int | None = Field(default=None, ge=0)
    order: int | None = Field(default=None, ge=0)
    max_attempts: int | None = Field(default=None, ge=1)
    options: list[TaskOptionCreate] | None = None

    @model_validator(mode="after")
    def validate_answer_config(self) -> Self:
        """Validate answer fields when answer_type is explicitly set."""
        provided = self.model_fields_set
        if "answer_type" not in provided or self.answer_type is None:
            return self
        _validate_answer_type_fields(
            self.answer_type,
            self.options,
            self.correct_string_answer,
            self.correct_number_answer,
        )
        return self


class TaskAdminRead(BaseModel):
    """Admin read schema for a task (includes correct answers)."""

    id: int
    document_id: str
    question: str
    answer_type: AnswerType
    correct_string_answer: str | None
    correct_number_answer: float | None
    number_tolerance: float | None
    string_match_mode: StringMatchMode
    points: int
    order: int
    max_attempts: int
    options: list[TaskOptionRead]


class TaskRead(BaseModel):
    """Member read schema for a task (no correct answers)."""

    id: int
    document_id: str
    question: str
    answer_type: AnswerType
    string_match_mode: StringMatchMode
    points: int
    order: int
    max_attempts: int
    options: list[TaskOptionMemberRead]


class TaskReorder(SQLModel):
    """Schema for bulk reordering tasks."""

    task_ids: list[int]


# ---------------------
# Task Response schemas
# ---------------------


class TaskResponseCreate(SQLModel):
    """Create/update schema for a user's task response."""

    selected_option_ids: list[int] | None = None
    text: str | None = None
    value: float | None = None

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        """Strip whitespace from text answers."""
        if v is not None:
            return v.strip()
        return v


class TaskResponseRead(SQLModel):
    """Read schema for a user's task response."""

    task_id: int
    user_id: int
    answer: dict[str, Any]
    is_correct: bool
    attempts: int
    correct_answer: dict[str, Any] | None = None


# ---------------------
# Task Event schemas
# ---------------------


class TasksUpdatedEvent(SQLModel):
    """Event payload for task configuration changes."""

    document_id: str
