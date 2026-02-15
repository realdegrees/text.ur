from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import core.config as cfg
from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.events import Events
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from api.dependencies.s3 import S3
from api.routers.events import (
    EventModelConfig,
    EventRouterConfig,
    get_events_router,
)
from core.app_exception import AppException
from fastapi import (
    BackgroundTasks,
    Body,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
)
from models.comment import (
    CommentCreate,
    CommentDelete,
    CommentRead,
    CommentUpdate,
)
from models.document import (
    DocumentCreate,
    DocumentRead,
    DocumentTransfer,
    DocumentUpdate,
    MousePositionEvent,
    MousePositionInput,
    ViewModeChangedEvent,
)
from models.enums import AppErrorCode, Permission, ViewMode, Visibility
from models.event import Event
from models.filter import DocumentFilter
from models.pagination import Paginated
from models.tables import Comment, Document, Group, Membership, User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from starlette.responses import StreamingResponse
from util.api_router import APIRouter
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

# ========================================================================
# ================= Document/Comment WebSocket Hooks ====================
# ========================================================================

def can_user_see_comment(
    user: User,
    membership: Membership,
    document: Document,
    comment_visibility: Visibility,
    comment_user_id: int,
) -> bool:
    """Determine comment visibility using the centralized comment_access guard.

    This builds a minimal Comment-like object from the provided data so we can
    reuse the Guard.comment_access predicate logic and avoid duplicating access rules.
    """
    # If we don't have a recipient user, short-circuit to False
    if not user:
        return False

    # Compose a minimal document object with a group containing only the recipient's
    # membership (if any). Guard.comment_access predicate expects comment.document.group.memberships
    # to be an iterable of Membership-like objects.
    memberships = [membership] if membership is not None else []
    group_obj = SimpleNamespace(memberships=memberships)
    document_obj = SimpleNamespace(view_mode=document.view_mode if document is not None else None, group=group_obj)
    comment_obj = SimpleNamespace(user_id=comment_user_id, visibility=comment_visibility, document=document_obj)

    # Delegate to the guard predicate (single source of truth)
    guard = Guard.comment_access()
    return guard.predicate(comment_obj, user)


async def _setup_document_comment_connection(websocket: WebSocket, related_resource: Document, user: User, session: AsyncSession) -> None:
    """Set up connection state for document comment channel.

    Attaches document and membership to websocket.state for use in other hooks.
    """
    # Fetch and store user's membership for this document's group (for permission checks)
    membership: Membership | None = None
    if related_resource.group_id:
        result = await session.exec(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.group_id == related_resource.group_id,
                Membership.accepted == True,  # noqa: E712
            )
        )
        membership = result.first()
    websocket.state.membership = membership


def _comment_visibility_transform(event_data: dict, websocket: WebSocket) -> dict | None:
    """Transform outgoing create/update/delete events for comment visibility.

    - For create: skip if recipient cannot see the comment
    - For update: possibly convert to create or delete depending on visibility changes
    - For delete: always send
    """
    event_type = event_data.get("type")
    payload = event_data.get("payload") or {}

    # Get state from websocket
    recipient: User | None = getattr(websocket.state, "user", None)
    doc: Document | None = getattr(websocket.state, "related_resource", None)
    membership: Membership | None = getattr(websocket.state, "membership", None)

    # Always send deletes (clients must remove UI state) and skip filtering if we lack context
    if event_type == "delete" or not recipient or not doc:
        return event_data

    comment_visibility_str = payload.get("visibility")
    comment_user = payload.get("user", {})
    comment_user_id = comment_user.get("id") if isinstance(comment_user, dict) else None

    if not (comment_visibility_str and comment_user_id is not None):
        return event_data

    try:
        comment_visibility = Visibility(comment_visibility_str)
    except ValueError:
        comment_visibility = Visibility.PUBLIC

    can_see = can_user_see_comment(recipient, membership, doc, comment_visibility, comment_user_id)

    if event_type == "create":
        return event_data if can_see else None

    # update handling
    old_visibility_str = event_data.get("old_visibility")
    could_see_before = True
    if old_visibility_str:
        try:
            old_visibility = Visibility(old_visibility_str)
            could_see_before = can_user_see_comment(recipient, membership, doc, old_visibility, comment_user_id)
        except ValueError:
            pass

    if can_see and could_see_before:
        return event_data
    if can_see and not could_see_before:
        return {**event_data, "type": "create"}
    if not can_see and could_see_before:
        return {**event_data, "type": "delete", "payload": {"id": payload.get("id")}}

    return None



async def _handle_mouse_position(event: Event, websocket: WebSocket, session: AsyncSession) -> Event:
    """Handle incoming mouse_position event - enriches with user info.

    event.payload is already a validated MousePositionInput instance from the events router.
    """
    user: User = websocket.state.user

    # event.payload is a MousePositionInput instance - enrich with user info
    # and convert to MousePositionEvent format
    enriched_payload = MousePositionEvent(
        user_id=user.id,
        username=user.username,
        x=event.payload.x,
        y=event.payload.y,
        page=event.payload.page,
        visible=event.payload.visible,
    )
    # Build a new Event typed for MousePositionEvent so downstream
    # serialization/validation doesn't warn about mismatched payload types.
    event_dict = event.model_dump()
    event_dict["payload"] = enriched_payload.model_dump()
    # Validate into a correctly-typed Event[MousePositionEvent]
    return Event[MousePositionEvent].model_validate(event_dict)


events_router = get_events_router(
    "comments",
    Document,
    base_router=router,
    config=EventRouterConfig(
        event_types={
            "create": EventModelConfig(
                model=CommentRead,
                response_model=CommentRead,
                transform_outgoing=_comment_visibility_transform,
            ),
            "update": EventModelConfig(
                model=CommentRead,
                response_model=CommentRead,
                transform_outgoing=_comment_visibility_transform,
            ),
            "delete": EventModelConfig(
                model=CommentRead,
                response_model=CommentDelete,
            ),
            "view_mode_changed": EventModelConfig(
                model=ViewModeChangedEvent,
            ),
            "mouse_position": EventModelConfig(
                model=MousePositionInput,  # Input: validate against MousePositionInput (no user info)
                response_model=MousePositionEvent,  # Output: documentation shows MousePositionEvent (with user info)
                handle_incoming=_handle_mouse_position,
            ),
        },
        setup_connection=_setup_document_comment_connection,
        track_active_users=True,
    )
)

# Include the HTTP router
tags = router.tags
router.tags = []
router.include_router(events_router)
router.tags = tags
router.websocket_config = events_router.websocket_config

router.tags.append("Documents")

# ======= Document Endpoints ==============

@router.post("/", response_model=DocumentRead)
async def create_document(
    db: Database,
    s3: S3,
    session_user: BasicAuthentication, # only basic auth because we need the validated form data for authorization in this case
    file: UploadFile = File(...),
    data: str = Form(..., description="JSON string of type `DocumentCreate`"),
) -> DocumentRead:
    """Create a new document entry and return presigned S3 upload URL."""
    document_create = DocumentCreate.model_validate_json(data)

    # Validate file type and size
    if file.content_type != "application/pdf":
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.INVALID_INPUT,
            detail="Only PDF files are allowed.",
        )
    max_size_bytes = cfg.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size and file.size > max_size_bytes:
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.INVALID_INPUT,
            detail=f"File size exceeds maximum of {cfg.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # Check if user is authorized if they are uploading to a group
    result = await db.exec(select(Membership).where(
        Membership.user_id == session_user.id,
        Membership.group_id == document_create.group_id,
        Membership.accepted == True,  # noqa: E712
    ))
    membership = result.first()
    if not membership:
        raise AppException(status_code=403, error_code=AppErrorCode.NOT_IN_GROUP, detail="User is not a member of the group.")
    if Permission.ADD_DOCUMENTS not in membership.permissions and membership.is_owner is False and Permission.ADMINISTRATOR not in membership.permissions:
        raise AppException(status_code=403, error_code=AppErrorCode.NOT_AUTHORIZED, detail="User does not have permission to add documents.")

    # Generate unique S3 key
    s3_key = f"document-{uuid4()}.pdf"

    # Upload to S3 first so we don't create orphaned DB records
    s3.upload(s3_key, file.file, content_type=file.content_type)

    # Create document entry; delete S3 object if DB commit fails
    document = Document(s3_key=s3_key, size_bytes=file.size, **document_create.model_dump(exclude_unset=True))
    db.add(document)
    try:
        await db.commit()
    except Exception:
        s3.delete(s3_key)
        raise
    await db.refresh(document)
    return document

@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    _: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> DocumentRead:
    """Get a document by ID."""
    return document

def slugify(text: str) -> str:
    """Generate a safe filename from an S3 key."""
    # Make the text safe for urls by replacing unsafe characters
    return "".join(c if c.isalnum() or c in (' ', '.', '_') else '_' for c in text).rstrip()

@router.get("/{document_id}/file")
async def get_document_file(
    request: Request,
    s3: S3,
    _: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> Response:
    """Download the document file from S3 and return it.

    Supports conditional requests via ETag/If-None-Match to avoid
    re-downloading unchanged files.
    """
    # Cheap HEAD request to get S3 metadata (including ETag)
    metadata = s3.metadata(document.s3_key)
    etag = (
        metadata.get("ETag", "").strip('"') if metadata else ""
    )

    # Check conditional request header
    if_none_match = request.headers.get("If-None-Match", "").strip('"')
    if etag and if_none_match == etag:
        return Response(status_code=304)

    # Stream the file from S3 with caching headers
    iterator = s3.download_stream(document.s3_key)
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{slugify(document.name)}.pdf"'
        ),
        "Cache-Control": "private, max-age=3600",
    }
    if etag:
        headers["ETag"] = f'"{etag}"'

    return StreamingResponse(
        iterator, media_type="application/pdf", headers=headers
    )

@router.get("/", response_model=Paginated[DocumentRead], response_class=ExcludableFieldsJSONResponse)
async def list_documents(
    _: BasicAuthentication,
    documents: Paginated[Document] = PaginatedResource(
        Document, DocumentFilter, guards=[Guard.document_access()],
    )
) -> Paginated[DocumentRead]:
    """Get all documents matching the filter for the authenticated user.

    The API returns only documents that belong to the user or to groups the user is a member of.
    """
    return documents


@router.put("/{document_id}/transfer", response_model=DocumentRead)
async def transfer_document(
    db: Database,
    session_user: User = Authenticate(guards=[Guard.document_access({Permission.REMOVE_DOCUMENTS})]),
    document_update: DocumentTransfer = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
) -> DocumentRead:
    """Transfer a document and return the updated document."""
    # Handle group_id transfer
    if document.group_id == document_update.group_id:
        raise HTTPException(status_code=403, detail="Document is already owned by this group.")
    result = await db.exec(
        select(Membership).where(
            Membership.user_id == session_user.id,
            Membership.group_id == document_update.group_id,
            Membership.accepted == True,  # noqa: E712
        )
    )
    target_membership = result.first()
    if not target_membership:
        raise HTTPException(status_code=403, detail="Must be a member of the target group.")
    if Permission.ADD_DOCUMENTS not in target_membership.permissions and target_membership.is_owner is False and Permission.ADMINISTRATOR not in target_membership.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions in target group.")

    await db.merge(document)
    document.sqlmodel_update(document_update.model_dump(exclude_unset=True))
    await db.commit()
    return document

@router.put("/{document_id}", response_model=DocumentRead)
async def update_document(
    db: Database,
    events: Events,
    user: User = Authenticate(guards=[Guard.document_access({Permission.ADD_DOCUMENTS})]), # ? Users with add permissions can also update
    document_update: DocumentUpdate = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
) -> DocumentRead:
    """Update a document and return the updated document."""
    # Store old view_mode to detect changes
    old_view_mode = document.view_mode
    # Merge returns the persistent instance attached to the session
    document = await db.merge(document)

    if document_update.visibility is not None:
        document.visibility = document_update.visibility
        # Check if the user can still see the document after the update and raise if not
        required_permissions: set[Permission] | None = None
        if document_update.visibility == Visibility.RESTRICTED:
            required_permissions = {Permission.VIEW_RESTRICTED_DOCUMENTS}
        elif document_update.visibility == Visibility.PRIVATE:
            required_permissions = {Permission.ADMINISTRATOR}  # No one except admins can see private documents
        else:
            required_permissions = None  # Public documents can be seen by all group members
        guard = Guard.document_access(required_permissions)


        if not guard.predicate(document, user):
            raise HTTPException(status_code=403, detail="You do not have access to this document after the update.")


    document.sqlmodel_update(document_update.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(document)

    # If view_mode changed, publish a view_mode_changed event to update WebSocket clients
    if document.view_mode != old_view_mode:
        view_mode_event = Event(
            event_id=uuid4(),
            published_at=datetime.now(UTC),
            payload=ViewModeChangedEvent(
                document_id=document.id,
                view_mode=document.view_mode,
            ),
            resource_id=document.id,
            resource="document",
            type="view_mode_changed",
        )
        await events.publish(
            view_mode_event.model_dump(mode="json"),
            channel=f"documents:{document.id}:comments"
        )

    return document

@router.delete("/{document_id}")
async def delete_document(
    db: Database,
    s3: S3,
    _: User = Authenticate(guards=[Guard.document_access({Permission.REMOVE_DOCUMENTS})]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> Response:
    """Delete a document from database and S3."""
    # Delete from S3
    s3.delete(document.s3_key)

    # Delete from database (cascade delete handles related records)
    await db.delete(document)
    await db.commit()

    return Response(status_code=204)


@router.delete("/{document_id}/clear")
async def clear_document_comments(
    db: Database,
    user: User = Authenticate(guards=[Guard.document_access(require_permissions={Permission.ADMINISTRATOR})]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> Response:
    """Clear all comments from a document. Only group owners and administrators can perform this action."""
    # Delete all comments for this document (cascade will handle replies)
    result = await db.exec(
        select(Comment).where(Comment.document_id == document.id)
    )
    comments = result.all()

    for comment in comments:
        await db.delete(comment)

    await db.commit()

    return Response(status_code=204)

