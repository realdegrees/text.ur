import asyncio
import contextlib
import json
from collections.abc import Callable
from typing import Annotated, Any

import core.config as cfg
import redis.asyncio as redis
from fastapi import Request, WebSocket
from fastapi.params import Depends


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
            f"redis://{cfg.REDIS_HOST}:{cfg.REDIS_PORT}", decode_responses=True, password=cfg.REDIS_PASSWORD
        )
        self._subscriber_task = asyncio.create_task(self._subscriber_loop())

    async def disconnect(self) -> None:
        """Cleanup Redis connection."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._subscriber_task
        if self._redis:
            await self._redis.aclose()

    # ---------------- WebSocket client management ----------------
    async def register_client(self, websocket: WebSocket, *, channel: str, on_event: Callable[[dict], None]) -> None:
        """Register a WebSocket client."""
        websocket.state.channel = channel
        websocket.state.on_event = on_event
        self._clients.setdefault(channel, set()).add(websocket)

    async def unregister_client(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket client."""
        channel: str = getattr(websocket.state, "channel", "default")
        if channel in self._clients:
            self._clients[channel].discard(websocket)
            if not self._clients[channel]:
                del self._clients[channel]

    # ---------------- Publishing ----------------
    
    async def publish(self, event: dict, channel: str = "default") -> None:
        """Publish event to Redis channel."""
        if not self._redis:
            raise RuntimeError("Redis connection not initialized")
        payload: str = json.dumps(event)
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
                await pubsub.subscribe(*current_channels)

            try:
                async for message in pubsub.listen():
                    await self._on_message(message)
            except Exception:
                # Reconnect on error
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

        for ws in clients:
            # Outgoing validation
            on_event = getattr(ws.state, "on_event", None)
            try:
                on_event(data)
            except Exception:
                to_remove.add(ws)

        # Cleanup disconnected clients
        for ws in to_remove:
            await self.unregister_client(ws) # prevent tight loop


async def events_dependency(websocket: WebSocket) -> EventManager:
    """Dependency to get the EventManager instance attached to the app state."""
    if websocket.app.state.event_manager is None:
        raise RuntimeError("EventManager not initialized")
    return websocket.app.state.event_manager

# Actual Dependency to use in endpoints
Events = Annotated[EventManager, Depends(events_dependency)]