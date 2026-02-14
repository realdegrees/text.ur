"""Rate limiting configuration using slowapi with Redis backend."""

import core.config as cfg
from slowapi import Limiter
from slowapi.util import get_remote_address
from util.ip import get_client_ip


def _default_key_func(request):  # noqa: ANN001, ANN202
    """Key by authenticated user ID when available, else by client IP.

    This ensures authenticated users get a per-user bucket while
    anonymous/unauthenticated requests fall back to IP-based limiting.
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return f"user:{user.id}"
    return get_client_ip(request)


def _build_redis_uri() -> str:
    """Build the Redis URI from configuration."""
    password_part = (
        f":{cfg.REDIS_PASSWORD}@" if cfg.REDIS_PASSWORD else "@"
    )
    return (
        f"redis://{password_part}{cfg.REDIS_HOST}:{cfg.REDIS_PORT}/1"
    )


limiter = Limiter(
    key_func=_default_key_func,
    default_limits=["120/minute"],
    storage_uri=_build_redis_uri(),
    strategy="fixed-window",
)

# Re-export for use in route decorators that need IP-only keying
ip_key_func = get_remote_address
