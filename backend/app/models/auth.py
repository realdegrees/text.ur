from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TokenType = Literal["access", "refresh"]

class Token(BaseModel):
    """A token object that contains the access and refresh tokens."""

    access_token: str
    refresh_token: str | None = None
    token_type: str

class UserJWTPayload(BaseModel):
    """The inner payload of a JWT, signed with the user's secret."""

    sub: str  # user id
    exp: datetime | None = None
    iat: datetime | None = None

class GlobalJWTPayload(BaseModel):
    """The payload of a client facing JWT, signed with the global secret."""

    sub: str  # user id
    type: TokenType | None = None
    exp: datetime | None = None
    iat: datetime | None = None
    inner: str | None = None

