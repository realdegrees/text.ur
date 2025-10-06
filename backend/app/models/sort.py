from typing import Literal

from sqlmodel import Field, SQLModel

Direction = Literal["asc", "desc"]


class Sort(SQLModel):
    field: str = Field()
    direction: Direction = Field()
