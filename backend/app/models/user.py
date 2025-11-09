from sqlmodel import Field, SQLModel

from models.base import BaseModel

# TODO maybe move these into config
MAX_USERNAME_LENGTH = 20
MAX_FIRST_NAME_LENGTH = 50
MAX_LAST_NAME_LENGTH = 50
MAX_EMAIL_LENGTH = 255
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

class UserCreate(SQLModel):
    username: str = Field(max_length=MAX_USERNAME_LENGTH)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    email: str = Field(max_length=MAX_EMAIL_LENGTH)
    first_name: str | None = Field(default=None, max_length=MAX_FIRST_NAME_LENGTH)
    last_name: str | None = Field(default=None, max_length=MAX_LAST_NAME_LENGTH)


class UserRead(BaseModel):
    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None


class UserPrivate(UserRead):
    email: str


class UserUpdate(SQLModel):
    username: str | None = Field(default=None, max_length=MAX_USERNAME_LENGTH)
    new_password: str | None = Field(default=None, max_length=MAX_PASSWORD_LENGTH)
    old_password: str | None = Field(default=None, max_length=MAX_PASSWORD_LENGTH)
    email: str | None = Field(default=None, max_length=MAX_EMAIL_LENGTH)
    first_name: str | None = Field(default=None, max_length=MAX_FIRST_NAME_LENGTH)
    last_name: str | None = Field(default=None, max_length=MAX_LAST_NAME_LENGTH)

