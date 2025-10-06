from sqlmodel import SQLModel

from models.base import BaseModel


class UserCreate(SQLModel):
    username: str
    password: str
    email: str
    first_name: str | None = None
    last_name: str | None = None


class UserRead(BaseModel):
    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None


class UserPrivate(UserRead):
    password: str
    email: str
    first_name: str | None = None
    last_name: str | None = None


class UserUpdate(SQLModel):
    username: str | None = None
    new_password: str | None = None
    old_password: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None

