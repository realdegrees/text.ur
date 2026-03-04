"""Rate limiting configuration using slowapi with Redis backend."""

from typing import Any
from urllib.parse import quote

import core.config as cfg
from core.auth import ALGORITHM
from core.config import JWT_SECRET
from fastapi import Request
from jwt import decode
from jwt.exceptions import InvalidTokenError
from slowapi import Limiter
from util.ip import get_client_ip


def get_cache_key(request: Request) -> str:
    """Key by authenticated user ID when available, else by client IP.

    Reads the ``access_token`` cookie and decodes the outer JWT to
    extract the user ID.  This runs inside the SlowAPI middleware
    — before FastAPI dependency injection — so we cannot rely on
    ``request.state.user`` being populated by the ``Authenticate``
    dependency.

    On any failure (missing cookie, expired / invalid token) the
    function falls back to IP-based keying.
    """
    token: str | None = request.cookies.get("access_token")
    if token:
        try:
            payload: dict[str, Any] = decode(token, JWT_SECRET, algorithms=[ALGORITHM])
            user_id: str | None = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except (InvalidTokenError, Exception):  # noqa: S110
            pass

    return get_client_ip(request)


def _build_redis_uri() -> str:
    """Build the Redis URI from configuration."""
    password_part = f":{quote(cfg.REDIS_PASSWORD, safe='')}@" if cfg.REDIS_PASSWORD else ""
    return f"redis://{password_part}{cfg.REDIS_HOST}:{cfg.REDIS_PORT}/1"


limiter = Limiter(
    key_func=get_cache_key,
    default_limits=["120/minute"],
    storage_uri=_build_redis_uri(),
    strategy="fixed-window",
)
