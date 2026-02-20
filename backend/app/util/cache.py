"""Redis-based cache utility for expensive query results."""

import json
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from urllib.parse import quote

import core.config as cfg
import redis.asyncio as redis
from core.logger import get_logger

cache_logger = get_logger("cache")

# Default TTL for cached score data (in seconds)
SCORE_CACHE_TTL = 300  # 5 minutes


def _build_redis_url() -> str:
    """Build Redis URL for cache database (db 2)."""
    password_part = (
        f":{quote(cfg.REDIS_PASSWORD, safe='')}@" if cfg.REDIS_PASSWORD else ""
    )
    return f"redis://{password_part}{cfg.REDIS_HOST}:{cfg.REDIS_PORT}/2"


@lru_cache(maxsize=1)
def _get_redis() -> redis.Redis:
    """Return a singleton async Redis client for caching."""
    return redis.from_url(
        _build_redis_url(),
        decode_responses=True,
    )


async def get_cached(key: str) -> dict[str, Any] | None:
    """Retrieve a cached value by key.

    Returns the deserialized dict if found, None on miss.
    """
    r = _get_redis()
    try:
        raw = await r.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception as e:
        cache_logger.warning("Cache read error for %s: %s", key, e)
    return None


async def set_cached(
    key: str,
    value: dict[str, Any],
    ttl: int = SCORE_CACHE_TTL,
) -> None:
    """Store a value in cache with TTL (seconds)."""
    r = _get_redis()
    try:
        await r.set(key, json.dumps(value), ex=ttl)
    except Exception as e:
        cache_logger.warning("Cache write error for %s: %s", key, e)


async def invalidate_group_scores(group_id: str) -> None:
    """Delete all cached scores for a group.

    Uses SCAN + DELETE to remove keys matching
    ``score:{group_id}:*``.  Called when score config or
    group reactions change.
    """
    r = _get_redis()
    pattern = f"score:{group_id}:*"
    try:
        cursor: int | str = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                await r.delete(*keys)
            if int(cursor) == 0:
                break
    except Exception as e:
        cache_logger.warning("Cache invalidation error for %s: %s", pattern, e)


def score_cache_key(
    group_id: str,
    user_id: int,
    document_id: str | None = None,
) -> str:
    """Build the Redis key for a user's group score.

    When *document_id* is provided the key is scoped to that
    single document so per-document scores are cached
    independently of the whole-group score.
    """
    base = f"score:{group_id}:{user_id}"
    if document_id is not None:
        return f"{base}:doc:{document_id}"
    return base
