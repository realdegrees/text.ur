from datetime import UTC, datetime, timedelta
from typing import Any, Literal, overload

import bcrypt
from api.dependencies.database import Database
from core.app_exception import AppException
from core.config import (
    JWT_ACCESS_EXPIRATION_MINUTES,
    JWT_REFRESH_EXPIRATION_DAYS,
    JWT_SECRET,
)
from fastapi import Depends, Request, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jwt import decode, encode
from jwt.exceptions import InvalidTokenError
from models.auth import GlobalJWTPayload, Token, TokenType, UserJWTPayload
from models.enums import AppErrorCode
from models.tables import User

if not JWT_SECRET:
    raise RuntimeError(
        "Required environment variable JWT_SECRET is not set")


ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login/", auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a password using bcrypt"""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def validate_password(user: User, password: str) -> bool:
    """Validate password."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        user.password.encode("utf-8"),
    )


@overload
def parse_jwt(token: str, db: Database, *, for_type: TokenType | None = None, strict: Literal[True] = True) -> User: ...

@overload
def parse_jwt(token: str, db: Database, *, for_type: TokenType | None = None, strict: Literal[False] = False) -> User | None: ...

def parse_jwt(token: str, db: Database, *, for_type: TokenType | None = None, strict: bool = True) -> User | None:
    """Validate a nested JWT and return the user if valid."""
    try:
        outer_payload: dict[str, Any] = decode(token, JWT_SECRET, algorithms=[ALGORITHM])  # Automatically checks expiry
        user_id: str | None = outer_payload.get("sub")
        inner_token: str | None = outer_payload.get("inner")
        token_type: str | None = outer_payload.get("type")

        def do_validate() -> tuple[User | None, str | None]:
            if for_type and token_type != for_type:
                return None, f"Expected type {for_type} but got {token_type}"

            if not user_id or not inner_token:
                return None, "Malformed token"

            user: User | None = db.get(User, user_id)
            if not user:
                return None, "User not found"

            inner_payload: dict[str, Any] = decode(inner_token, user.secret, algorithms=[ALGORITHM])
            sub: str | None = inner_payload.get("sub")

            if sub is None or str(sub) != str(user_id):
                return None, "Token user mismatch"

            return user, None

        user, error = do_validate()
        if user:
            return user
        else:
            if strict:
                raise AppException(status_code=401, error_code=AppErrorCode.INVALID_TOKEN, detail=error or "Invalid token")
            return None
    except (InvalidTokenError, Exception) as e:
        if strict:
            raise AppException(
                status_code=401,
                error_code=AppErrorCode.INVALID_TOKEN,
                detail=str(e) if isinstance(e, InvalidTokenError) else "Invalid token",
            ) from e
        return None

def refresh_token(user: User, db: Database) -> Token:
    """Generate a new access token using a valid refresh token."""
    token = generate_token(user, "access")
    return Token(access_token=token, token_type="bearer")



def generate_token(user: User, token_type: Literal["access", "refresh"]) -> str:
    """Generate a nested JWT: inner signed with user secret, outer with global secret."""
    if token_type == "access":
        expire = datetime.now(UTC) + timedelta(minutes=JWT_ACCESS_EXPIRATION_MINUTES)
    elif token_type == "refresh":
        expire = datetime.now(UTC) + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS)

    # Inner JWT (personal)
    inner_payload = UserJWTPayload(
        sub=str(user.id),
        exp=expire,
        iat=datetime.now(UTC),
    )
    # Optionally add roles/permissions if available
    inner_token = encode(inner_payload.model_dump(), user.secret, algorithm=ALGORITHM)

    # Outer JWT (global)
    outer_payload = GlobalJWTPayload(
        sub=str(user.id),
        inner=inner_token,
        exp=expire,
        iat=datetime.now(UTC),
        type=token_type,
    )
    outer_token = encode(outer_payload.model_dump(), JWT_SECRET, algorithm=ALGORITHM)
    return outer_token
