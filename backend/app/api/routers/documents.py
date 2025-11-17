import uuid

from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
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
    Response,
    UploadFile,
)
from models.comment import (
    CommentDelete,
    CommentRead,
    CommentUpdate,
)
from models.document import (
    DocumentCreate,
    DocumentRead,
    DocumentTransfer,
    DocumentUpdate,
)
from models.enums import AppErrorCode, Permission
from models.filter import DocumentFilter
from models.pagination import Paginated
from models.tables import Comment, Document, Group, Membership, User
from sqlmodel import select
from util.api_router import APIRouter
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

# Define an events router for Comments linked to Documents
events_router = get_events_router(
    "comments", Document, Comment,
    base_router=router,
    config=EventRouterConfig(
        # TODO add global validation in/out for all events based on document access
        create=EventModelConfig(model=CommentRead,
                                validation_in=Guard.comment_access().predicate,
                                validation_out=Guard.comment_access().predicate
                                ),
        update=EventModelConfig(model=CommentUpdate,
                                validation_in=Guard.comment_access().predicate,
                                validation_out=Guard.comment_access().predicate
                                ),
        delete=EventModelConfig(model=CommentDelete,
                                validation_in=Guard.comment_access().predicate,
                                validation_out=Guard.comment_access().predicate
                                ),
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
    # Check if user is authorized if they are uploading to a group
    membership = db.exec(select(Membership).where(
        Membership.user_id == session_user.id,
        Membership.group_id == document_create.group_id
    )).first()
    if not membership:
        raise AppException(status_code=403, error_code=AppErrorCode.NOT_IN_GROUP, detail="User is not a member of the group.")
    if Permission.ADD_DOCUMENTS not in membership.permissions and membership.is_owner is False and Permission.ADMINISTRATOR not in membership.permissions:
        raise AppException(status_code=403, error_code=AppErrorCode.NOT_AUTHORIZED, detail="User does not have permission to add documents.")

    # Generate unique S3 key
    s3_key = f"document-{uuid.uuid4()}.pdf"

    # Create document entry
    document = Document(s3_key=s3_key, size_bytes=file.size, **document_create.model_dump(exclude_unset=True))

    db.add(document)
    db.commit()
    db.refresh(document)

    s3.upload(s3_key, file.file, content_type=file.content_type)
    return document

@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    _: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> DocumentRead:
    """Get a document by ID."""
    return document

@router.get("/{document_id}/file")
async def get_document_file(
    s3: S3,
    _: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> Response:
    """Download the document file from S3 and return it."""
    file_content = s3.download(document.s3_key)
    return Response(content=file_content, media_type="application/pdf")

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
    target_membership = db.exec(
        select(Membership).where(
            Membership.user_id == session_user.id,
            Membership.group_id == document_update.group_id
        )
    ).first()
    if not target_membership:
        raise HTTPException(status_code=403, detail="Must be a member of the target group.")
    if Permission.ADD_DOCUMENTS not in target_membership.permissions and target_membership.is_owner is False and Permission.ADMINISTRATOR not in target_membership.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions in target group.")

    db.merge(document)
    document.sqlmodel_update(document_update.model_dump(exclude_unset=True))
    db.commit()
    return document

@router.put("/{document_id}", response_model=DocumentRead)
async def update_document(
    db: Database,
    _: User = Authenticate(guards=[Guard.document_access({Permission.ADD_DOCUMENTS})]), # ? Users with add permissions can also update
    document_update: DocumentUpdate = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
) -> DocumentRead:
    """Update a document and return the updated document."""
    db.merge(document)
    document.sqlmodel_update(document_update.model_dump(exclude_unset=True))
    db.commit()
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
    db.delete(document)
    db.commit()

    return Response(status_code=204)

