from typing import TYPE_CHECKING

from sqlmodel import SQLModel

from models.base import BaseModel
from models.enums import Visibility

if TYPE_CHECKING:
    from models.group import GroupRead
    from models.user import UserRead


class DocumentCreate(SQLModel):
    visibility: Visibility
    group_id: int

class DocumentRead(BaseModel):
    id: int
    s3_key: str
    group_id: int
    visibility: Visibility

class DocumentTransfer(SQLModel):
    group_id: int
    
class DocumentUpdate(SQLModel):
    visibility: Visibility | None = None
