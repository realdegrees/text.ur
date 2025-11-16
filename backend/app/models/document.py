from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

from models.base import BaseModel
from models.enums import Visibility

if TYPE_CHECKING:
    from models.group import GroupRead
    from models.user import UserRead


class DocumentCreate(SQLModel):
    visibility: Visibility
    name: str = Field(max_length=255)
    group_id: str

class DocumentRead(BaseModel):
    id: str
    s3_key: str
    name: str
    group_id: str
    visibility: Visibility

class DocumentTransfer(SQLModel):
    group_id: str

class DocumentUpdate(SQLModel):
    visibility: Visibility | None = None
    name: str | None = Field(default=None, max_length=255)