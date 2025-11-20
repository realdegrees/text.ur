import asyncio
import contextlib
import json
from collections.abc import Callable
from typing import Annotated, Any, Literal

import core.config as cfg
import redis.asyncio as redis
from core.logger import get_logger
from fastapi import Request, WebSocket
from fastapi.params import Depends

# Logger for the events subsystem
logger = get_logger("events")


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
        print("[events] EventManager connected to Redis and started subscriber loop")
        logger.info("EventManager connected")

    async def disconnect(self) -> None:
        """Cleanup Redis connection."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._subscriber_task
        if self._redis:
            await self._redis.aclose()
        print("[events] EventManager disconnected and Redis closed")
        logger.info("EventManager disconnected")

    # ---------------- WebSocket client management ----------------
    async def register_client(self, websocket: WebSocket, *, channel: str, on_event: Callable[[dict], Any]) -> None:
        """Register a WebSocket client. on_event can be sync or async."""
        websocket.state.channel = channel
        websocket.state.on_event = on_event
        self._clients.setdefault(channel, set()).add(websocket)
        # Logging the registration for debug
        client_info = getattr(websocket, 'client', None)
        print(f"[events] Register client -> channel={channel} client={client_info}")
        logger.info("Registered websocket client for channel %s: %s", channel, client_info)

    async def unregister_client(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket client."""
        channel: str = getattr(websocket.state, "channel", "default")
        if channel in self._clients:
            self._clients[channel].discard(websocket)
            if not self._clients[channel]:
                del self._clients[channel]
            print(f"[events] Unregistered client from channel {channel}")
            logger.info("Unregistered websocket client from channel %s", channel)

    # ---------------- Publishing ----------------
    
    async def publish(self, event: dict, channel: str = "default") -> None:
        """Publish event to Redis channel."""
        if not self._redis:
            raise RuntimeError("Redis connection not initialized")
        payload: str = json.dumps(event)
        print(f"[events] Publishing event to channel {channel}: {event}")
        logger.info("Publishing event to %s: %s", channel, event)
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
                print(f"[events] Subscribing to channels: {', '.join(current_channels)}")
                logger.info("Subscribing to Redis channels: %s", ",".join(current_channels))
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
                print(f"[events] _on_message => channel={channel} data={data} sending to ws={ws}")
                # Handle both sync and async callbacks
                result = on_event(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in on_event callback: {e}", exc_info=True)
                print(f"[events] ERROR in on_event: {e}")
                to_remove.add(ws)

        # Cleanup disconnected clients
        for ws in to_remove:
            await self.unregister_client(ws) # prevent tight loop
            print("[events] Removed disconnected client from channel")
            logger.info("Removed disconnected client from channel %s", channel)


async def events_dependency_http(request: Request) -> EventManager:
    """HTTP dependency returning the shared EventManager."""
    # Diagnostic logs for dependency usage
    print(f"[events] HTTP Events dependency requested for path={request.url.path} method={request.method}")
    logger.info("HTTP events dependency requested: %s %s", request.method, request.url.path)
    if request.app.state.event_manager is None:
        print("[events] HTTP EventManager not initialized")
        raise RuntimeError("EventManager not initialized")
    return request.app.state.event_manager


async def events_dependency_ws(ws: WebSocket) -> EventManager:
    """WebSocket dependency returning the shared EventManager."""
    # Diagnostic logs for websocket connections requesting the event manager
    client = getattr(ws, "client", None)
    headers = dict(ws.headers)
    print(f"[events] WebSocket Events dependency requested by client={client}, path={ws.url.path}, headers={headers}")
    logger.info("WS events dependency requested: client=%s path=%s", client, ws.url.path)
    if ws.app.state.event_manager is None:
        print("[events] WebSocket EventManager not initialized")
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