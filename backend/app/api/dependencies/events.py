import asyncio
import contextlib
import json
from collections.abc import Callable
from datetime import datetime
from functools import lru_cache
from typing import Annotated, Any, Literal

import core.config as cfg
import redis.asyncio as redis
from core.logger import get_logger
from fastapi import Request, WebSocket
from fastapi.params import Depends
from pydantic import BaseModel

events_logger = get_logger("events")

# Heartbeat interval for active user tracking (in seconds)
HEARTBEAT_INTERVAL = 180  # 3 minutes
# Key expiry for active users (slightly longer than heartbeat to handle delays)
USER_KEY_EXPIRY = HEARTBEAT_INTERVAL + 60  # 4 minutes


class ConnectedUser(BaseModel):
    """Represents a user connected to a channel endpoint (an active websocket connection)."""

    user_id: int
    username: str
    connection_id: str
    connected_at: str


class EventManager:
    """Redis-backed event manager for broadcasting events to WebSocket clients."""
    
    _redis: redis.Redis | None = None
    _subscriber_task: asyncio.Task | None = None
    _clients: dict[str, set[WebSocket]] = {}  # noqa: RUF012
        
    def __init__(self) -> None:
        """Initialize the EventManager with Redis connection details."""
        if not all([cfg.REDIS_HOST, cfg.REDIS_PORT, cfg.REDIS_PASSWORD]):
            raise RuntimeError("Not all required Redis configuration variables are set.")

    # ---------------- Lifecycle ----------------

    async def connect(self) -> None:
        """Establish Redis connection if not already connected."""
        if self._redis is None:
            self._redis = redis.from_url(
                f"redis://{cfg.REDIS_HOST}:{cfg.REDIS_PORT}",
                decode_responses=True,
                password=cfg.REDIS_PASSWORD,
            )
            events_logger.info("Connected to Redis")
            await self._redis.ping()
            
        # Clear all active_users: keys on startup to avoid stale data
        keys = await self._redis.keys("active_users:*")
        if keys:
            await self._redis.delete(*keys)
            events_logger.info("Cleared %d stale active user keys", len(keys))
        
        self._subscriber_task = asyncio.create_task(self._subscriber_loop())
        events_logger.info("Started subscriber loop")
        
    async def check_connection(self) -> None:
        """Check Redis connection and reconnect if necessary."""
        r = redis.from_url(
            f"redis://{cfg.REDIS_HOST}:{cfg.REDIS_PORT}",
            decode_responses=True,
            password=cfg.REDIS_PASSWORD,
        )

        await r.ping()
        events_logger.debug("Redis connection is healthy")
            
    async def disconnect(self) -> None:
        """Cleanup Redis connection."""
        self._subscriber_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._subscriber_task
        await self._redis.aclose()
        events_logger.info("Disconnected from Redis")

    # ---------------- Active User Tracking ----------------
    def _active_users_key(self, channel_key: str) -> str:
        """Return a redis key used to store active users for a specific channel.

        The EventManager tracks active users per event subscription key — which may
        include resource identifiers and the channel name (for example
        "documents:123:comments"). Using the channel-key keeps active-user storage
        generic and endpoint-specific rather than hardcoded to documents/comments.
        """
        # Use a stable prefix to avoid accidental collisions with pubsub channel
        # names and make keys easily identifiable in Redis.
        return f"active_users:{channel_key}"

    async def add_active_user(
        self, channel_key: str, user_id: int, username: str, connection_id: str
    ) -> list[ConnectedUser]:
        """Add a user to the active users list for the given channel and return all active users.

        channel_key should be the same string used for EventManager.publish/subscribe
        (for example the endpoint-specific channel). This avoids hardcoding to
        document semantics and allows the router to track active users for any endpoint.
        """
        key = self._active_users_key(channel_key)
        user_data = ConnectedUser(
            user_id=user_id,
            username=username,
            connection_id=connection_id,
            connected_at=datetime.now().isoformat()
        )
        
        # Cache and merge to avoid race condition
        current_active_users = await self.get_active_users(channel_key)
        new_active_users = [user_data, *current_active_users]

        # Add user to hash and set expiry
        await self._redis.hset(key, str(user_id), user_data.model_dump_json())
        await self._redis.expire(key, USER_KEY_EXPIRY)

        return new_active_users

    async def remove_active_user(self, channel_key: str, user_id: int) -> None:
        """Remove a user from the active users list for the provided channel key."""
        key = self._active_users_key(channel_key)
        await self._redis.hdel(key, str(user_id))
        events_logger.info("Removed active user %s from channel %s", user_id, channel_key)

    async def get_active_users(self, channel_key: str) -> list[ConnectedUser]:
        """Get all active users for a channel key."""
        key = self._active_users_key(channel_key)
        users_data = await self._redis.hgetall(key)

        users = []
        for user_json in users_data.values():
            try:
                users.append(ConnectedUser.model_validate_json(user_json))
            except Exception as e:
                events_logger.warning("Failed to parse user data: %s", e)

        return users

    async def refresh_user_heartbeat(self, channel_key: str) -> None:
        """Refresh the expiry for active users for the provided channel key."""
        key = self._active_users_key(channel_key)
        await self._redis.expire(key, USER_KEY_EXPIRY)

    # ---------------- WebSocket client management ----------------
    async def register_client(self, websocket: WebSocket, *, channel: str, on_event: Callable[[dict], Any]) -> None:
        """Register a WebSocket client. on_event can be sync or async."""
        websocket.state.channel = channel
        websocket.state.on_event = on_event
        self._clients.setdefault(channel, set()).add(websocket)

    async def unregister_client(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket client."""
        channel: str = websocket.state.channel or "default"
        if channel in self._clients:
            self._clients[channel].discard(websocket)
            if not self._clients[channel]:
                del self._clients[channel]

    # ---------------- Publishing ----------------
    async def publish(self, event: dict, channel: str = "default") -> None:
        """Publish event to Redis channel."""
        payload: str = json.dumps(event)
        await self._redis.publish(channel, payload)

    # ---------------- Subscriber loop ----------------
    async def _subscriber_loop(self) -> None:
        """Listen to all Redis channels that have clients and forward messages."""
        pubsub = self._redis.pubsub()
        subscribed_channels: set[str] = set()

        while True:
            # Get current channels that have clients
            current_channels = set(self._clients.keys())

            # If no channels, wait and check again
            if not current_channels:
                # Unsubscribe from all if we were subscribed
                if subscribed_channels:
                    await pubsub.unsubscribe(*subscribed_channels)
                    subscribed_channels.clear()
                await asyncio.sleep(0.5)
                continue

            # Subscribe to new channels, unsubscribe from removed ones
            to_subscribe = current_channels - subscribed_channels
            to_unsubscribe = subscribed_channels - current_channels

            if to_unsubscribe:
                await pubsub.unsubscribe(*to_unsubscribe)
                subscribed_channels -= to_unsubscribe

            if to_subscribe:
                events_logger.debug("Subscribing to Redis channels: %s", ", ".join(to_subscribe))
                await pubsub.subscribe(*to_subscribe)
                subscribed_channels |= to_subscribe

            try:
                # Use get_message with timeout instead of blocking listen()
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    await self._on_message(message)
            except Exception as e:
                events_logger.warning("Redis pubsub error, reconnecting: %s", e)
                await asyncio.sleep(1.0)
                pubsub = self._redis.pubsub()
                subscribed_channels.clear()

            await asyncio.sleep(0.05)  # Small sleep to prevent busy loop when messages arrive rapidly

    async def _on_message(self, message: dict) -> None:
        if message["type"] != "message":
            return

        channel: str = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
        data: dict = json.loads(message["data"])
        clients: set[WebSocket] = self._clients.get(channel, set())
        to_remove: set[WebSocket] = set()

        for ws in clients:
            on_event = getattr(ws.state, "on_event", None)
            try:
                # Handle both sync and async callbacks
                result = on_event(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                events_logger.error("Error in on_event callback: %s", e, exc_info=True)
                to_remove.add(ws)

        # Cleanup disconnected clients
        for ws in to_remove:
            await self.unregister_client(ws)
            events_logger.debug("Removed disconnected client from channel %s", channel)


@lru_cache(maxsize=1)
def get_event_manager() -> EventManager:
    """Return the appropriate Depends for a Request or WebSocket."""
    return EventManager()

# Actual Dependency to use in endpoints for normal HTTP handlers
Events = Annotated[EventManager, Depends(get_event_manager)]
WebsocketEvents = Annotated[EventManager, Depends(get_event_manager)]