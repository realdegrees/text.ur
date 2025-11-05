from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic import create_model
from sqlmodel import Field

from models.filter import Filter


class Pagination(PydanticBaseModel):
    """Model for pagination dependency injection"""

    offset: int = Field(ge=0, default=0)
    limit: int = Field(ge=0, le=100, default=25)


class Paginated[Model: PydanticBaseModel](PydanticBaseModel):
    """Do not use this model directly. Use the `paginated_model` factory instead."""

    data: list[Model]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=0, le=100)
    filters: list[Filter] = Field(default=[])
    order_by: list[str] = Field(default=[])


PaginatedBase = create_model(
    "PaginatedBase",
    data=(list[Any], ...),
    __base__=Paginated[Any],
)
