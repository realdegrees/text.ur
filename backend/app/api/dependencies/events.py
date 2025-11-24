import asyncio
import contextlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, Literal

import core.config as cfg
import redis.asyncio as redis
from core.logger import get_logger
from fastapi import Request, WebSocket
from fastapi.params import Depends
from pydantic import BaseModel

app_logger = get_logger("app")
events_logger = get_logger("events")

# Heartbeat interval for active user tracking (in seconds)
HEARTBEAT_INTERVAL = 180  # 3 minutes
# Key expiry for active users (slightly longer than heartbeat to handle delays)
USER_KEY_EXPIRY = HEARTBEAT_INTERVAL + 60  # 4 minutes


class ConnectedUser(BaseModel):
    """Represents a user connected to a document."""

    user_id: int
    username: str
    connection_id: str
    connected_at: str


class EventManager:
    """Redis-backed event manager for broadcasting events to WebSocket clients."""

    def __init__(self) -> None:
        """Initialize the EventManager with Redis connection details."""
        self._redis: redis.Redis | None = None
        self._subscriber_task: asyncio.Task | None = None
        self._clients: dict[str, set[WebSocket]] = {}  # channel -> set of clients

    # ---------------- Lifecycle ----------------
    async def connect(self) -> None:
        """Connect to Redis and start subscriber loop."""
        self._redis = redis.from_url(
            f"redis://{cfg.REDIS_HOST}:{cfg.REDIS_PORT}",
            decode_responses=True,
            password=cfg.REDIS_PASSWORD,
            socket_connect_timeout=10,  # Connection timeout
            socket_timeout=10,  # Operation timeout
        )
        # Verify connection works
        await self._verify_connection()
        self._subscriber_task = asyncio.create_task(self._subscriber_loop())
        app_logger.info("EventManager connected to Redis and started subscriber loop")

    async def _verify_connection(self) -> None:
        """Verify Redis connection at startup."""
        if not self._redis:
            raise RuntimeError("Redis client not initialized")
        try:
            await self._redis.ping()
            app_logger.info("Redis connection verified successfully")
        except Exception as e:
            app_logger.error("Redis connection failed: %s", e)
            raise RuntimeError(f"Failed to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        """Cleanup Redis connection."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._subscriber_task
        if self._redis:
            await self._redis.aclose()
        app_logger.info("EventManager disconnected")

    # ---------------- Active User Tracking ----------------
    def _active_users_key(self, document_id: str) -> str:
        """Get Redis key for active users of a document."""
        return f"document:{document_id}:active_users"

    async def add_active_user(
        self, document_id: str, user_id: int, username: str, connection_id: str
    ) -> list[ConnectedUser]:
        """Add a user to the active users list and return all active users."""
        if not self._redis:
            raise RuntimeError("Redis connection not initialized")

        key = self._active_users_key(document_id)
        user_data = ConnectedUser(
            user_id=user_id,
            username=username,
            connection_id=connection_id,
            connected_at=datetime.now().isoformat()
        )

        # Add user to hash and set expiry
        await self._redis.hset(key, str(user_id), user_data.model_dump_json())
        await self._redis.expire(key, USER_KEY_EXPIRY)

        events_logger.info("Added active user %s to document %s", username, document_id)
        return await self.get_active_users(document_id)

    async def remove_active_user(self, document_id: str, user_id: int) -> None:
        """Remove a user from the active users list."""
        if not self._redis:
            raise RuntimeError("Redis connection not initialized")

        key = self._active_users_key(document_id)
        await self._redis.hdel(key, str(user_id))
        events_logger.info("Removed active user %s from document %s", user_id, document_id)

    async def get_active_users(self, document_id: str) -> list[ConnectedUser]:
        """Get all active users for a document."""
        if not self._redis:
            raise RuntimeError("Redis connection not initialized")

        key = self._active_users_key(document_id)
        users_data = await self._redis.hgetall(key)

        users = []
        for user_json in users_data.values():
            try:
                users.append(ConnectedUser.model_validate_json(user_json))
            except Exception as e:
                events_logger.warning("Failed to parse user data: %s", e)

        return users

    async def refresh_user_heartbeat(self, document_id: str) -> None:
        """Refresh the expiry for active users (called periodically as heartbeat)."""
        if not self._redis:
            return

        key = self._active_users_key(document_id)
        await self._redis.expire(key, USER_KEY_EXPIRY)

    # ---------------- WebSocket client management ----------------
    async def register_client(self, websocket: WebSocket, *, channel: str, on_event: Callable[[dict], Any]) -> None:
        """Register a WebSocket client. on_event can be sync or async."""
        websocket.state.channel = channel
        websocket.state.on_event = on_event
        self._clients.setdefault(channel, set()).add(websocket)
        client_info = getattr(websocket, "client", None)
        events_logger.debug("Registered websocket client for channel %s: %s", channel, client_info)

    async def unregister_client(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket client."""
        channel: str = getattr(websocket.state, "channel", "default")
        if channel in self._clients:
            self._clients[channel].discard(websocket)
            if not self._clients[channel]:
                del self._clients[channel]
            events_logger.debug("Unregistered websocket client from channel %s", channel)

    # ---------------- Publishing ----------------
    async def publish(self, event: dict, channel: str = "default") -> None:
        """Publish event to Redis channel."""
        if not self._redis:
            raise RuntimeError("Redis connection not initialized")
        payload: str = json.dumps(event)
        events_logger.info("Publishing event to %s: %s", channel, event)
        await self._redis.publish(channel, payload)

    # ---------------- Subscriber loop ----------------
    async def _subscriber_loop(self) -> None:
        """Listen to all Redis channels that have clients and forward messages."""
        if not self._redis:
            raise RuntimeError("Redis connection not initialized")

        pubsub = self._redis.pubsub()
        while True:
            # Subscribe to all channels with clients
            current_channels = set(self._clients.keys())
            if current_channels:
                events_logger.debug("Subscribing to Redis channels: %s", ", ".join(current_channels))
                await pubsub.subscribe(*current_channels)

            try:
                async for message in pubsub.listen():
                    await self._on_message(message)
            except Exception as e:
                events_logger.warning("Redis pubsub error, reconnecting: %s", e)
                await asyncio.sleep(1.0)
                pubsub = self._redis.pubsub()

            await asyncio.sleep(0.1)

    async def _on_message(self, message: dict) -> None:
        if message["type"] != "message":
            return

        channel: str = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
        data: dict = json.loads(message["data"])
        clients: set[WebSocket] = self._clients.get(channel, set())
        to_remove: set[WebSocket] = set()

        events_logger.info("Received event on %s: %s", channel, data)

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


async def events_dependency_http(request: Request) -> EventManager:
    """HTTP dependency returning the shared EventManager."""
    if request.app.state.event_manager is None:
        raise RuntimeError("EventManager not initialized")
    return request.app.state.event_manager


async def events_dependency_ws(ws: WebSocket) -> EventManager:
    """WebSocket dependency returning the shared EventManager."""
    if ws.app.state.event_manager is None:
        raise RuntimeError("EventManager not initialized")
    return ws.app.state.event_manager


def ProvideEvents(endpoint: Literal["http", "ws"] = "http") -> Depends:
    """Return the appropriate Depends for a Request or WebSocket.

    Usage:
        ProvideEvents() -> Annotated[EventManager, Depends(events_dependency_http)]
        ProvideEvents(endpoint="ws") -> Annotated[EventManager, Depends(events_dependency_ws)]
    """
    return Depends(events_dependency_ws if endpoint == "ws" else events_dependency_http)

# Actual Dependency to use in endpoints for normal HTTP handlers
Events = Annotated[EventManager, ProvideEvents()]