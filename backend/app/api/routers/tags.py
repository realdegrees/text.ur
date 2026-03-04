from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.resource import Resource
from core import config
from core.app_exception import AppException
from core.rate_limit import limiter
from fastapi import Body, Request
from fastapi.responses import Response
from models.enums import AppErrorCode, Permission
from models.tables import Document, Tag, User
from models.tag import TagCreate, TagRead, TagUpdate
from sqlmodel import func, select
from util.api_router import APIRouter
from util.queries import Guard

router = APIRouter(
    prefix="/documents/{document_id}/tags",
    tags=["Tags"],
)


@router.post("/", response_model=TagRead)
@limiter.limit("10/minute")
async def create_tag(
    request: Request,
    db: Database,
    _: User = Authenticate(guards=[Guard.document_access({Permission.ADMINISTRATOR})]),
    tag_create: TagCreate = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
) -> TagRead:
    """Create a new tag for the document.

    Requires MANAGE_TAGS permission in the document's group.
    """
    # Check if document has reached max tag limit
    result = await db.exec(select(func.count(Tag.id)).where(Tag.document_id == document.id))
    tag_count = result.one()
    if tag_count >= config.MAX_TAGS_PER_DOCUMENT:
        raise AppException(
            status_code=400,
            error_code=AppErrorCode.VALIDATION_ERROR,
            detail=f"Document has reached the maximum number of tags ({config.MAX_TAGS_PER_DOCUMENT})",
        )

    tag = Tag(**tag_create.model_dump(), document_id=document.id)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.get("/", response_model=list[TagRead])
async def list_tags(
    db: Database,
    _: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
) -> list[TagRead]:
    """Get all tags for a document.

    Any user with access to the document can view tags.
    """
    result = await db.exec(select(Tag).where(Tag.document_id == document.id))
    tags = result.all()
    return tags


@router.get("/{tag_id}", response_model=TagRead)
async def get_tag(
    db: Database,
    _: User = Authenticate(guards=[Guard.document_access()]),
    document: Document = Resource(Document, param_alias="document_id"),
    tag: Tag = Resource(Tag, param_alias="tag_id"),
) -> TagRead:
    """Get a specific tag by ID.

    Any user with access to the document can view tags.
    """
    # Verify tag belongs to the document
    if tag.document_id != document.id:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Tag not found in this document",
        )
    return tag


@router.put("/{tag_id}", response_model=TagRead)
async def update_tag(
    db: Database,
    _: User = Authenticate(guards=[Guard.document_access({Permission.ADMINISTRATOR})]),
    tag_update: TagUpdate = Body(...),
    document: Document = Resource(Document, param_alias="document_id"),
    tag: Tag = Resource(Tag, param_alias="tag_id"),
) -> TagRead:
    """Update a tag.

    Requires MANAGE_TAGS permission in the document's group.
    """
    # Verify tag belongs to the document
    if tag.document_id != document.id:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Tag not found in this document",
        )

    tag = await db.merge(tag)
    tag.sqlmodel_update(tag_update.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    db: Database,
    _: User = Authenticate(guards=[Guard.document_access({Permission.ADMINISTRATOR})]),
    document: Document = Resource(Document, param_alias="document_id"),
    tag: Tag = Resource(Tag, param_alias="tag_id"),
) -> Response:
    """Delete a tag.

    Requires MANAGE_TAGS permission in the document's group.
    This will also remove the tag from all comments.
    """
    # Verify tag belongs to the document
    if tag.document_id != document.id:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="Tag not found in this document",
        )

    await db.delete(tag)
    await db.commit()
    return Response(status_code=204)
