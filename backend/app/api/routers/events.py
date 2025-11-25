import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path as PathLibPath
from typing import Annotated, Any, Literal
from uuid import uuid4

from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.events import (
    HEARTBEAT_INTERVAL,
    ConnectedUser,
    EventManager,
    ProvideEvents,
)
from core.logger import get_logger
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from jinja2 import Template
from models.base import BaseModel
from models.event import Event
from models.tables import User
from pydantic import ValidationError
from pydantic import create_model as internal_model
from sqlmodel import Session, SQLModel
from util.api_router import APIRouter

logger = get_logger("app")

# Load the WebSocket description template
WEBSOCKET_TEMPLATE_PATH = PathLibPath(__file__).parent.parent / "docs" / "websocket.jinja"
with open(WEBSOCKET_TEMPLATE_PATH) as template_file:
    WEBSOCKET_TEMPLATE = Template(template_file.read())


@dataclass
class EventModelConfig[T: SQLModel, R: SQLModel](dict):
    """Configuration for a specific event model used in the event router.

    The `model` field is used to validate incoming payloads from clients.
    After validation, event.payload will be an instance of this model.

    The optional `response_model` is used for documentation purposes to show
    the shape of outgoing payloads (e.g., CommentCreate -> CommentRead).
    """

    model: T  # Model for validating incoming payloads
    response_model: R | None = None  # Optional model for documentation of outgoing payloads
    # Optional transform hook for outgoing events. Should return the final event dict to send,
    # or None to skip sending for this particular user. Can access websocket.state for custom state.
    # Signature: (event_data, websocket) -> event_data | None
    transform_outgoing: Callable[[T, WebSocket], R | None] | None = None
    # Optional handler for incoming events (e.g., to perform database operations).
    # Receives event with pre-validated payload (event.payload is an instance of `model`).
    # Should return the event to publish (potentially modified). Can access websocket.state for custom state.
    # Signature: (event, websocket, session) -> event
    handle_incoming: Callable[[Event, WebSocket, Session], Event] | None = None

@dataclass
class EventRouterConfig(dict):
    """Configuration for event models used in the event router.

    The router is fully generic and supports arbitrary event types through a string-keyed dictionary.
    Event type names are defined by the consumer (e.g., documents router) and can be anything.
    """

    # Map of event type string -> event configuration
    event_types: dict[str, EventModelConfig]
    # Optional callback to set up connection-specific state when a client connects.
    # Can attach any objects to websocket.state that will be accessible in all hooks.
    # Signature: (websocket, related_resource, user, session) -> None
    setup_connection: Callable[[WebSocket, BaseModel, User, Session], None] | None = None
    # Whether to track active users for this channel (default: True)
    track_active_users: bool = True

def get_events_router[RelatedResourceModel: BaseModel](  # noqa: C901
    channel: str,
    related_resource_model: RelatedResourceModel,
    *,
    config: EventRouterConfig,
    base_router: APIRouter,
) -> APIRouter:
    """Create a generic router with event endpoints for a resource.

    This router is fully generic and supports arbitrary event types defined in the config.
    Event handling logic (validation, transformation, database operations) is provided via
    callbacks in the EventModelConfig for each event type.

    Args:
        channel: The channel to subscribe to for events (e.g., "comments")
        related_resource_model: The resource model that this event router is related to (e.g., Document)
        config: EventRouterConfig with event type mappings and optional hooks
        base_router: The base APIRouter to derive the full channel path from

    Returns:
        APIRouter with WebSocket handler attached as attributes that is registered with the app in main.py

    """
    router = APIRouter(
        prefix="/{resource_id}" + f"/events/{channel}",
        tags=["WebSocket Events"],
    )

    base_prefix = [p for p in base_router.prefix.split("/") if p]
    router_prefix = [p for p in router.prefix.split("/") if p]
    full_channel = ":".join(
        [*base_prefix, *router_prefix[:-2]]) + f":{channel}"

    # Create the WebSocket path for registration on the main app
    full_path = "/" + "/".join(base_prefix + router_prefix)

    # Create the WebSocket handler function
    async def client_endpoint(  # noqa: C901
        websocket: WebSocket, db: Database, events: Annotated[EventManager, ProvideEvents(endpoint="ws")], resource_id: str, user: User = Authenticate(endpoint="ws")
    ) -> None:
        """Connect a client to the event stream."""
        logger.info(f"[WS] Connection attempt for resource_id={resource_id}, user={user.id if user else None}")
        logger.info(f"[WS] Cookies: {websocket.cookies}")

        related_resource = db.get(related_resource_model, resource_id)

        if not related_resource:
            logger.warning(f"[WS] Resource not found: {resource_id}")
            await websocket.close(code=1008)
            return

        # Get or generate unique connection ID for this WebSocket connection
        # Frontend sends connection_id as query param to match with HTTP requests
        connection_id = websocket.query_params.get("connection_id") or str(uuid4())
        websocket.state.connection_id = connection_id

        # Store user and related resource (available to all hooks)
        websocket.state.user = user
        websocket.state.related_resource = related_resource

        # Run setup hook to attach any additional state to websocket
        if config.setup_connection:
            config.setup_connection(websocket, related_resource, user, db)

        logger.info(f"[WS] Accepting connection for resource_id={resource_id}, connection_id={connection_id}")
        await websocket.accept()

        # Build endpoint-specific channel key (matches subscription/publish channel)
        channel_key = full_channel.format(resource_id=resource_id)

        # Track active users for this endpoint if enabled
        active_users: list[ConnectedUser] = []
        heartbeat_task: asyncio.Task | None = None

        if config.track_active_users:
            # Add this user to active users and get current list
            active_users = await events.add_active_user(
                channel_key, user.id, user.username, connection_id
            )

            # Send handshake response with active users
            handshake_response = {
                "type": "handshake",
                "payload": {
                    "connection_id": connection_id,
                    "active_users": [u.model_dump() for u in active_users]
                }
            }
            await websocket.send_json(handshake_response)

            # Publish user_connected event to other clients
            user_connected_event = {
                "type": "user_connected",
                "payload": {
                    "user_id": user.id,
                    "username": user.username,
                    "connection_id": connection_id,
                    "connected_at": datetime.now().isoformat()
                },
                "originating_connection_id": connection_id
            }
            # Publish using the same channel key other subscribers will be
            # listening on for this endpoint/resource.
            await events.publish(
                user_connected_event,
                channel=channel_key,
            )

            # Start heartbeat task to keep user active
            async def heartbeat_loop() -> None:
                while True:
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    await events.refresh_user_heartbeat(channel_key)

            heartbeat_task = asyncio.create_task(heartbeat_loop())

        def get_event_config(event_type: str) -> EventModelConfig | None:
            """Get the event configuration for a given event type."""
            return config.event_types.get(event_type)

        async def on_event(event_data: dict) -> None:
            """Validate outgoing event before sending to client.

            Uses the transform_outgoing hook from the event config to determine if the event
            should be sent to this specific client, allowing for custom permission/visibility logic.
            """
            event_type = event_data.get("type")
            originating_connection_id = event_data.get("originating_connection_id")

            if not event_type:
                logger.warning(f"Invalid event structure: {event_data}")
                return

            # Skip sending event back to the connection that triggered it
            if originating_connection_id is not None and originating_connection_id == websocket.state.connection_id:
                return

            # System events bypass config and are always sent
            system_events = {"handshake", "user_connected", "user_disconnected"}
            if event_type in system_events:
                logger.debug(f"[WS] Sending system event: {event_type}")
                await websocket.send_json(event_data)
                return

            # Get event configuration for user-defined events
            type_config = get_event_config(event_type)

            # If no config found — log diagnostics and skip
            if type_config is None:
                available = list(config.event_types.keys()) if hasattr(config, "event_types") else []
                logger.warning(
                    "[WS] No config found for event type: %s (raw_type repr=%r, raw_type type=%s). Available types: %s",
                    event_type,
                    event_type,
                    type(event_type).__name__ if event_type is not None else "None",
                    available,
                )
                try:
                    comparisons = []
                    for k in available:
                        comparisons.append(f"{k!r}=={event_type!r}:{k == event_type}")
                    logger.debug("[WS] Event type comparisons: %s", ", ".join(comparisons))
                except Exception:
                    logger.debug("[WS] Failed to produce event type comparisons")
                return

            # If a transform_outgoing hook is provided, use it to filter/transform the event
            if type_config is not None and type_config.transform_outgoing:
                try:
                    transformed = type_config.transform_outgoing(event_data, websocket)
                    if transformed is None:
                        # The hook decided the event should not be sent to this client
                        return
                    event_data = transformed
                except Exception:
                    logger.exception("Error running transform_outgoing hook for event %s", event_type)
                    # Fail-safe: if the transformation errors, skip sending to avoid leaking info
                    return

            await websocket.send_json(event_data)
            
        async def client_event_loop() -> None: # noqa: C901
            """Handle incoming events from the client."""
            while True:
                event_data = await websocket.receive_json()

                event_type = event_data.get("type")

                if not event_type:
                    logger.warning("[WS] Received event without type")
                    continue

                # Get event configuration (quick lookup) and fallback to scanning the
                # configured keys if the dict lookup fails for any reason.
                type_config = get_event_config(event_type)

                # No fallback normalization — we expect clients to send the exact
                # configured event type string. If the lookup fails the detailed
                # diagnostics above will help trace mismatch causes.

                if type_config is None:
                    # Log available event types and a couple of diagnostics to help
                    available = list(config.event_types.keys()) if hasattr(config, "event_types") else []
                    logger.warning('Received unknown event type: %s. Available types: %s', event_type, available)
                    continue

                # Validate the event structure
                # Frontend sends simplified format: {type, payload, resource_id?}
                # Backend needs full Event format with event_id, published_at, etc.
                try:
                    # Auto-populate missing Event envelope fields
                    if "event_id" not in event_data:
                        event_data["event_id"] = str(uuid4())
                    if "published_at" not in event_data:
                        event_data["published_at"] = datetime.now().isoformat()
                    if "resource" not in event_data:
                        event_data["resource"] = None
                    if "resource_id" not in event_data:
                        event_data["resource_id"] = None
                    if "originating_connection_id" not in event_data:
                        event_data["originating_connection_id"] = websocket.state.connection_id

                    # Validate payload against the configured model
                    event = Event[type_config.model].model_validate(event_data)

                except ValidationError as e:
                    logger.error(f"[WS] Event validation failed for type '{event_type}': {e}")
                    logger.error(f"[WS] Event data: {event_data}")
                    # TODO: Inform client with structured error event (validation failed)
                    continue
                except Exception as e:
                    logger.exception(f"[WS] Unexpected error during validation: {e}")
                    continue

                # Handle the event using the configured handler
                if type_config.handle_incoming is not None:
                    try:
                        event = type_config.handle_incoming(event, websocket, db)
                    except Exception as e:
                        logger.exception(f"[WS] Error handling incoming event: {e}")
                        # TODO: Inform client with structured error event (internal error)
                        continue
                else:
                    # TODO: Send back an error event indicating no handler is configured
                    pass
                
                

                # Publish the event to other clients
                event_dict = event.model_dump(mode="json")
                await events.publish(event_dict, channel=websocket.state.channel)

        # Register the client with the event manager (Outgoing events from server to client)
        await events.register_client(
            websocket, 
            channel=full_channel.format(resource_id=resource_id),
            on_event=on_event
        )

        # Cleanup function for disconnect
        async def cleanup_connection() -> None:
            """Clean up connection resources."""
            # Cancel heartbeat task
            if heartbeat_task:
                heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat_task

            # Remove user from active users and notify others if tracking is enabled
            if config.track_active_users:
                await events.remove_active_user(channel_key, user.id)

                # Publish user_disconnected event
                user_disconnected_event = {
                    "type": "user_disconnected",
                    "payload": {
                        "user_id": user.id
                    }
                }
                await events.publish(
                    user_disconnected_event,
                    channel=channel_key,
                )

            await events.unregister_client(websocket)

        # Client event loop (Incoming events from client to server)
        try:
            await client_event_loop()
        except WebSocketDisconnect:
            await cleanup_connection()
        except ValidationError as e:
            await cleanup_connection()
            await websocket.send_json({"error": "Validation error", "details": str(e)}, mode="text")
            await websocket.close(code=1003)
        except Exception as e:
            logger.error(
                f"Error processing WebSocket message for resource {resource_id} "
                f"on route {full_path}: {e}"
            )
            await cleanup_connection()
            await websocket.send_json({"error": "Internal server error", "details": "Unknown error"})
            await websocket.close(code=1011)
            
    # ====================================================================
    # ================= WebSocket documentation endpoint =================
    # ====================================================================
    # This endpoint is only for documentation purposes and does not handle actual WebSocket connection logic

    # Build event type models dynamically from config
    # Provide both incoming (what clients send) and outgoing (what server sends)
    # so documentation can show both sides. Explicit None checks are required
    # because EventModelConfig subclasses dict and may evaluate falsy.
    event_type_models: dict[str, dict[str, type]] = {}
    for event_type_name, event_config in config.event_types.items():
        if event_config is not None:
            incoming_model = event_config.model
            outgoing_model = event_config.response_model or incoming_model
            if incoming_model is not None and outgoing_model is not None:
                event_type_models[event_type_name] = {
                    "incoming": incoming_model if event_config.handle_incoming is not None else None,
                    "outgoing": outgoing_model,
                }

    # Render the WebSocket documentation using the Jinja2 template
    dynamic_description = WEBSOCKET_TEMPLATE.render(
        channel=channel,
        full_channel=full_channel,
        event_types=event_type_models,
    )

    # Build a single response model for OpenAPI using Event[...] with a Union of all
    # configured response payload models.
    RESPONSE_DESCRIPTION_DEFAULT: str = "Outgoing WebSocket Events have one of the payload types below based on the event type."

    payload_models: list[type] = []
    for _, event_config in config.event_types.items():
        # Collect the response payload model (response_model or model) for each event type
        if event_config is not None:
            doc_model: type | None = event_config.response_model or event_config.model
            if doc_model is not None:
                payload_models.append(doc_model)

    # Compose a union of payload models (or a single model) and wrap it in Event[...]
    response_model_type: type | None
    response_description: str = RESPONSE_DESCRIPTION_DEFAULT

    if len(payload_models) == 0:
        response_model_type = None
        response_description = "Endpoint not configured for outgoing events"
    else:
        if len(payload_models) == 1:
            payload_union: type = payload_models[0]
        else:
            # Build a union of all payload models using the pipe (|) operator
            payload_union = payload_models[0]
            for _payload in payload_models[1:]:
                payload_union = payload_union | _payload
        # Use the generic Event[...] with the composed payload union
        response_model_type = Event[payload_union]  # type: ignore[misc]

    @router.api_route(
        "/",
        methods=["TRACE"],
        include_in_schema=True,
        summary="WebSocket Event Stream",
        response_description=response_description,
        description=dynamic_description,
        response_model=response_model_type
    )
    async def websocket_docs() -> Event:
        """WebSocket endpoint documentation."""
        # This is a dummy endpoint for documentation - actual functionality is via WebSocket
        raise HTTPException(
            status_code=400, detail="Use WebSocket connection at this endpoint, not HTTP")

    # Attach WebSocket handler and path to the router for main app registration
    router.websocket_config = (full_path, client_endpoint)
    return router
