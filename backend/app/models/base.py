from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """Base class for all resource models."""

    created_at: datetime = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
        },
    )