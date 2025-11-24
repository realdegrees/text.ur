import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path as PathLibPath
from typing import Annotated, Literal, Union
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
from models.enums import Permission, ViewMode, Visibility
from models.event import Event
from models.tables import Document, Membership, User
from pydantic import ValidationError
from pydantic import create_model as internal_model
from sqlmodel import SQLModel, select
from util.api_router import APIRouter

logger = get_logger("app")

# Load the WebSocket description template
WEBSOCKET_TEMPLATE_PATH = PathLibPath(__file__).parent.parent / "docs" / "websocket.jinja"
with open(WEBSOCKET_TEMPLATE_PATH) as template_file:
    WEBSOCKET_TEMPLATE = Template(template_file.read())


def can_user_see_comment(
    user: User,
    membership: Membership | None,
    document: Document,
    comment_visibility: Visibility,
    comment_user_id: int,
) -> bool:
    """Check if a user can see a comment based on view_mode, visibility, and permissions.

    Rules:
    - Document view_mode RESTRICTED: only owner, admins, and users with VIEW_RESTRICTED_COMMENTS
    - Document view_mode PUBLIC: based on comment visibility and user permissions

    Comment visibility (when view_mode is PUBLIC):
    - PRIVATE: only comment author sees it
    - RESTRICTED: author + owner + admin + users with VIEW_RESTRICTED_COMMENTS
    - PUBLIC: author + owner + admin + members if the group
    """
    # Comment author always sees their own comments
    if comment_user_id == user.id:
        return True

    # No membership = no access (except for own comments handled above)
    if not membership:
        return False

    # Check document view_mode first
    if document.view_mode == ViewMode.RESTRICTED:
        # Only owner, admins, and users with VIEW_RESTRICTED_COMMENTS can see comments
        return (
            membership.is_owner
            or Permission.ADMINISTRATOR in membership.permissions
            or Permission.VIEW_RESTRICTED_COMMENTS in membership.permissions
        )

    # view_mode is PUBLIC - check comment visibility
    # Owner and admin bypass visibility restrictions
    if membership.is_owner or Permission.ADMINISTRATOR in membership.permissions:
        return True

    # Check based on comment visibility
    if comment_visibility == Visibility.PRIVATE:
        # Only author (handled above) can see private comments
        return False

    if comment_visibility == Visibility.RESTRICTED:
        return Permission.VIEW_RESTRICTED_COMMENTS in membership.permissions

    if comment_visibility == Visibility.PUBLIC:
        return True

    return False
    
@dataclass
class EventModelConfig[T: SQLModel](dict):
    """Configuration for a specific event model used in the event router."""

    model: T
    validation_in: Callable[[T, User], bool] | None = None
    validation_out: Callable[[T, User], bool] | None = None
    # Optional transform hook for outgoing events. Should return the final event dict to send,
    # or None to skip sending for this particular user. Signature: (event_data, user, document, membership)
    transform_outgoing: Callable[[dict, User | None, Document | None, Membership | None], dict | None] | None = None
    
@dataclass
class EventRouterConfig[CreateModel: SQLModel, ReadModel: SQLModel, UpdateModel: SQLModel, DeleteModel: SQLModel, ViewModeModel: SQLModel, MouseModel: SQLModel](dict):
    """Configuration for event models used in the event router.

    The router supports the classical CRUD event types for a resource (create, read, update, delete)
    and two explicit "non-resource" event shapes used by the documents/comments channel:
    - view_mode_changed: when the document's view_mode changes
    - mouse_position: cursor/mouse position events used for collaborative cursors
    """

    create: EventModelConfig[CreateModel] | None = None
    read: EventModelConfig[ReadModel] | None = None
    update: EventModelConfig[UpdateModel] | None = None
    delete: EventModelConfig[DeleteModel] | None = None
    view_mode_changed: EventModelConfig[ViewModeModel] | None = None
    mouse_position: EventModelConfig[MouseModel] | None = None

def get_events_router[TableModel: SQLModel, RelatedResourceModel: BaseModel, CreateModel: SQLModel, ReadModel: SQLModel, UpdateModel: SQLModel, DeleteModel: SQLModel, ViewModeModel: SQLModel, MouseModel: SQLModel](  # noqa: C901
    channel: str,
    related_resource_model: RelatedResourceModel,
    table_model: TableModel,
    *,
    config: EventRouterConfig[CreateModel, ReadModel, UpdateModel, DeleteModel, ViewModeModel, MouseModel],
    base_router: APIRouter,
) -> APIRouter:
    """Create a router with event endpoints for a resource.

    Args:
        channel: The channel to subscribe to for events
        related_resource_model: The resource model that this event router is related to
        table_model: The SQLModel table corresponding to the event data
        config: EventRouterConfig | None = None,
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

        # Store user and related resource for permission checks on outgoing events
        websocket.state.user = user
        websocket.state.document = related_resource if isinstance(related_resource, Document) else None

        # Fetch and store user's membership for this document's group (for permission checks)
        membership: Membership | None = None
        if websocket.state.document and websocket.state.document.group_id:
            membership = db.exec(
                select(Membership).where(
                    Membership.user_id == user.id,
                    Membership.group_id == websocket.state.document.group_id,
                    Membership.accepted == True,  # noqa: E712
                )
            ).first()
        websocket.state.membership = membership

        logger.info(f"[WS] Accepting connection for resource_id={resource_id}, connection_id={connection_id}")
        await websocket.accept()

        # Track active users for this document
        active_users: list[ConnectedUser] = []
        heartbeat_task: asyncio.Task | None = None

        if channel == "comments" and websocket.state.document:
            doc_id = websocket.state.document.id
            # Add this user to active users and get current list
            active_users = await events.add_active_user(
                doc_id, user.id, user.username, connection_id
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
            await events.publish(
                user_connected_event,
                channel=f"documents:{doc_id}:comments"
            )

            # Start heartbeat task to keep user active
            async def heartbeat_loop() -> None:
                while True:
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    await events.refresh_user_heartbeat(doc_id)

            heartbeat_task = asyncio.create_task(heartbeat_loop())

        def is_user_eligible(event: Event, direction: str) -> bool:
            """Check if the event passes the configured validation for the given direction ('in' or 'out')."""
            if not config:
                return True
            event_type = event.type
            type_config = getattr(config, event_type, None)
            if not type_config:
                return True
            validation = getattr(type_config, f"validation_{direction}", None)
            if validation:
                # Validation expects the payload (Comment object), not the Event wrapper
                return validation(event.payload, user)
            return True

        def has_required_models(event_type: str) -> bool:
            """Check if the required models for the event type exist in config."""
            if event_type == "create":
                return bool(config.create and config.create.model)
            if event_type == "update":
                return bool(config.update and config.update.model)
            if event_type == "delete":
                return bool(config.delete and config.delete.model)
            if event_type == "view_mode_changed":
                return bool(config.view_mode_changed and config.view_mode_changed.model)
            if event_type == "mouse_position":
                return bool(config.mouse_position and config.mouse_position.model)
            return False

        async def on_event(event_data: dict) -> None: # noqa: C901
            """Validate outgoing event before sending to client.

            Permission filtering logic for comment events:
            - DELETE: Always send (user needs to know to remove from their UI)
            - CREATE: Check visibility - if user can't see, skip
            - UPDATE: Check visibility - if user can see, send UPDATE;
                      if user can't see, send DELETE instead (remove from their view)
            - mouse_position: Always send (no filtering needed for cursor positions)
            """
            event_type = event_data.get("type")
            payload = event_data.get("payload")
            originating_connection_id = event_data.get("originating_connection_id")

            if not event_type or payload is None:
                logger.warning(f"Invalid event structure: {event_data}")
                return

            # Skip sending event back to the connection that triggered it
            if originating_connection_id is not None and originating_connection_id == websocket.state.connection_id:
                logger.debug(f"[WS] Skipping event echo for connection {websocket.state.connection_id}")
                return

            # Handle mouse_position events - just send them through without filtering
            if event_type == "mouse_position":
                await websocket.send_json(event_data)
                return

            # Get stored state for permission checks and allow per-type transform hooks
            ws_user: User | None = getattr(websocket.state, "user", None)
            ws_document: Document | None = getattr(websocket.state, "document", None)
            ws_membership: Membership | None = getattr(websocket.state, "membership", None)

            # If the router config provides a transform_outgoing hook for this event-type, give it a chance
            # to mutate or reject the event for this particular client. This keeps the core WebSocket
            # plumbing separate from event-specific permission/visibility logic.
            type_config = getattr(config, event_type, None)
            if type_config and getattr(type_config, "transform_outgoing", None):
                try:
                    transformed = type_config.transform_outgoing(event_data, ws_user, ws_document, ws_membership)
                    if transformed is None:
                        # The hook decided the event should not be sent to this client
                        return
                    event_data = transformed
                    payload = event_data.get("payload")
                except Exception:
                    logger.exception("Error running transform_outgoing hook for event %s", event_type)
                    # Fail-safe: if the transformation errors, skip sending to avoid leaking info
                    return

            # Handle explicit view-mode events (previously handled via `custom`)
            if event_type == "view_mode_changed" and payload.get("view_mode") and payload.get("document_id"):
                # Update cached document view_mode
                if ws_document and ws_document.id == payload.get("document_id"):
                    try:
                        new_view_mode = ViewMode(payload.get("view_mode"))
                        ws_document.view_mode = new_view_mode
                        logger.info(f"[WS] Updated cached view_mode to {new_view_mode} for document {ws_document.id}")
                    except ValueError:
                        logger.warning(f"[WS] Invalid view_mode in custom event: {payload.get('view_mode')}")

            logger.info(f"[WS] Sending event to client: type={event_data.get('type')}, resource_id={event_data.get('resource_id')}")
            await websocket.send_json(event_data)
            
        async def client_event_loop() -> None: # noqa: C901
            while True:
                event_data = await websocket.receive_json()

                # Handle mouse_position events specially - just broadcast to others
                if event_data.get("type") == "mouse_position":
                    # Add user info to the event and broadcast
                    mouse_event = {
                        "type": "mouse_position",
                        "payload": {
                            "user_id": user.id,
                            "username": user.username,
                            "x": event_data.get("payload", {}).get("x", 0),
                            "y": event_data.get("payload", {}).get("y", 0),
                            "page": event_data.get("payload", {}).get("page", 1),
                            "visible": event_data.get("payload", {}).get("visible", True),
                        },
                        "originating_connection_id": websocket.state.connection_id,
                    }
                    await events.publish(mouse_event, channel=websocket.state.channel)
                    continue

                event = Event[table_model].model_validate(event_data)

                if not is_user_eligible(event, "in"):
                    continue

                if not has_required_models(event.type):
                    # TODO: Inform client with structured error event (operation not supported)
                    continue

                if event.type == "create":
                    payload = config.create.model.model_validate(event.payload)
                    resource = table_model(**payload.model_dump())
                    db.add(resource)
                    db.commit()
                    db.refresh(resource)
                    event.payload = config.read.model.model_validate(resource, strict=True).model_dump()
                elif event.type == "update":
                    payload: UpdateModel = config.update.model.model_validate(event.payload)
                    resource: TableModel | None = db.get(table_model, event.resource_id)
                    if not resource:
                        # TODO: Inform client with structured error event (resource not found)
                        continue
                    db.merge(resource)
                    resource.sqlmodel_update(payload.model_dump(exclude_unset=True))
                    db.commit()
                    db.refresh(resource)
                    event.payload = config.read.model.model_validate(resource, strict=True).model_dump()
                elif event.type == "delete":
                    payload: DeleteModel = config.delete.model.model_validate(event.payload)
                    resource: TableModel | None = db.get(table_model, event.resource_id)
                    if not resource:
                        # TODO: Inform client with structured error event (resource not found)
                        continue
                    db.delete(resource)
                    db.commit()
                    event.payload = payload
                elif event.type == "view_mode_changed":
                    # Validate incoming view-mode events if the router exposes a model for it
                    if config.view_mode_changed and config.view_mode_changed.model:
                        payload = config.view_mode_changed.model.model_validate(event.payload)
                        event.payload = payload.model_dump()
                elif event.type == "mouse_position":
                    # Incoming mouse_position may be sent by clients; validate if a model is provided
                    if config.mouse_position and config.mouse_position.model:
                        payload = config.mouse_position.model.model_validate(event.payload)
                        event.payload = payload.model_dump()

                await events.publish(event.model_dump(mode="json"), channel=websocket.state.channel)

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

            # Remove user from active users and notify others
            if channel == "comments" and websocket.state.document:
                doc_id = websocket.state.document.id
                await events.remove_active_user(doc_id, user.id)

                # Publish user_disconnected event
                user_disconnected_event = {
                    "type": "user_disconnected",
                    "payload": {
                        "user_id": user.id
                    }
                }
                await events.publish(
                    user_disconnected_event,
                    channel=f"documents:{doc_id}:comments"
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
                f"Error processing WebSocket message for {table_model.__name__} resource {resource_id} "
                f"on route {full_path}: {e}"
            )
            await cleanup_connection()
            await websocket.send_json({"error": "Internal server error", "details": "Unknown error"})
            await websocket.close(code=1011)
            
    # ====================================================================
    # ================= WebSocket documentation endpoint =================
    # ====================================================================
    # This endpoint is only for documentation purposes and does not handle actual WebSocket connection logic

    create_model=config.create.model if config and config.create else None
    read_model=config.read.model if config and config.read else None
    update_model=config.update.model if config and config.update else None
    delete_model=config.delete.model if config and config.delete else None
    view_mode_model=config.view_mode_changed.model if config and config.view_mode_changed else None
    mouse_model=config.mouse_position.model if config and config.mouse_position else None
        
    # Render the WebSocket documentation using the Jinja2 template
    dynamic_description = WEBSOCKET_TEMPLATE.render(
        channel=channel,
        full_channel=full_channel,
        create_model=create_model,
        read_model=read_model,
        update_model=update_model,
        delete_model=delete_model,
        view_mode_model=view_mode_model,
        mouse_model=mouse_model
    )

    response_models: list[type] = []

    MODEL_CONFIGS = [
        (create_model and read_model, "CreateEvent", ["create"], read_model, None),
        (update_model and read_model, "UpdateEvent", ["update"], read_model, int),
        (view_mode_model, "ViewModeChangedEvent", ["view_mode_changed"], view_mode_model, None),
        (mouse_model, "MousePositionEvent", ["mouse_position"], mouse_model, None),
        (delete_model, "DeleteEvent", ["delete"], delete_model, int),
    ]

    for condition, model_suffix, event_types, payload_model, resource_id_type in MODEL_CONFIGS:
        if condition:
            event_model = internal_model(
                f"{table_model.__name__}{model_suffix}",
                payload=(payload_model, ...) if payload_model else (
                    type(None), None),
                type=(Literal[tuple(event_types)], ...),
                resource_id=(resource_id_type, ...),
                __base__=Event,
            )
            response_models.append(event_model)

    response_description: str = "Outgoing WebSocket Events have one of types listed below"
    # Use Union if multiple models, single model if only one, or Event if none
    if len(response_models) > 1:
        response_model_type = Union[tuple(response_models)]  # noqa: UP007
    elif len(response_models) == 1:
        response_model_type = response_models[0]
    else:
        response_model_type = None
        response_description = "Endpoint not configured for outgoing events"

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
