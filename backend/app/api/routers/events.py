from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path as PathLibPath
from typing import Literal, Union

from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.events import Events
from core.logger import get_logger
from fastapi import HTTPException, Path, WebSocket, WebSocketDisconnect
from jinja2 import Template
from models.base import BaseModel
from models.event import Event
from models.tables import User
from pydantic import ValidationError
from pydantic import create_model as internal_model
from sqlmodel import SQLModel
from util.api_router import APIRouter

logger = get_logger("app")

# Load the WebSocket description template
WEBSOCKET_TEMPLATE_PATH = PathLibPath(__file__).parent.parent / "docs" / "websocket.jinja"
with open(WEBSOCKET_TEMPLATE_PATH) as template_file:
    WEBSOCKET_TEMPLATE = Template(template_file.read())
    
@dataclass
class EventModelConfig[T: SQLModel](dict):
    """Configuration for a specific event model used in the event router."""
    
    model: T
    validation_in: Callable[[T, User], bool] | None = None
    validation_out: Callable[[T, User], bool] | None = None
    
@dataclass
class EventRouterConfig[CreateModel: SQLModel, ReadModel: SQLModel, UpdateModel: SQLModel, DeleteModel: SQLModel, CustomModel: SQLModel](dict):
    """Configuration for event models used in the event router."""
    
    create: EventModelConfig[CreateModel] | None = None
    update: EventModelConfig[UpdateModel] | None = None
    delete: EventModelConfig[DeleteModel] | None = None
    custom: EventModelConfig[CustomModel] | None = None

def get_events_router[TableModel: SQLModel, RelatedResourceModel: BaseModel, CreateModel: SQLModel, UpdateModel: SQLModel, DeleteModel: SQLModel, CustomModel: SQLModel](  # noqa: C901
    channel: str,
    related_resource_model: RelatedResourceModel,
    table_model: TableModel,
    *,
    config: EventRouterConfig[CreateModel, UpdateModel, DeleteModel, CustomModel],
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

    # TODO store the auth state in websocket.state and use it in the event manager to filter outgoing events individually like an endpoint would
    # Create the WebSocket handler function
    async def client_endpoint(  # noqa: C901
        websocket: WebSocket, db: Database, events: Events, resource_id: int = Path(...), user: User = Authenticate(endpoint="ws")
    ) -> None:
        """Connect a client to the event stream."""
        related_resource = db.get(related_resource_model, resource_id)
        
        if not related_resource:
            await websocket.close(code=1008)
            return

        await websocket.accept()


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
                return validation(event, user)
            return True

        def has_required_models(event_type: str) -> bool:
            """Check if the required models for the event type exist in config."""
            if event_type == "create":
                return bool(config.create and config.create.model)
            if event_type == "update":
                return bool(config.update and config.update.model)
            if event_type == "delete":
                return bool(config.delete and config.delete.model)
            if event_type == "custom":
                return bool(config.custom and config.custom.model)
            return False

        def on_event(event: Event[TableModel]) -> bool:
            """Validate outgoing event before sending to client."""
            if not is_user_eligible(event, "out"):
                return
            websocket.send_json(event.model_dump(mode="json"))
            
        async def client_event_loop() -> None:
            while True:
                event_data = await websocket.receive_json()
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
                elif event.type == "custom":
                    payload: CustomModel = config.custom.model.model_validate(event.payload)
                    event.payload = payload.model_dump()

                await events.publish(event.model_dump(mode="json"), channel=websocket.state.channel)

        # Register the client with the event manager (Outgoing events from server to client)
        await events.register_client(
            websocket, 
            channel=full_channel.format(resource_id=resource_id),
            on_event=on_event
        )

        # Client event loop (Incoming events from client to server)
        try:
            await client_event_loop() 
        except WebSocketDisconnect:
            await events.unregister_client(websocket)
        except ValidationError as e:
            await websocket.send_json({"error": "Validation error", "details": str(e)}, mode="text")
            await websocket.close(code=1003)
        except Exception as e:
            logger.error(
                f"Error processing WebSocket message for {table_model.__name__} resource {resource_id} "
                f"on route {full_path}: {e}"
            )
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
    custom_model=config.custom.model if config and config.custom else None
        
    # Render the WebSocket documentation using the Jinja2 template
    dynamic_description = WEBSOCKET_TEMPLATE.render(
        channel=channel,
        full_channel=full_channel,
        create_model=create_model,
        read_model=read_model,
        update_model=update_model,
        delete_model=delete_model,
        custom_model=custom_model
    )

    response_models: list[type] = []

    MODEL_CONFIGS = [
        (create_model and read_model, "CreateEvent", ["create"], read_model, None),
        (update_model and read_model, "UpdateEvent", ["update"], read_model, int),
        (custom_model, "CustomEvent", ["custom"], custom_model, int),
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
                __base__=Event
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
