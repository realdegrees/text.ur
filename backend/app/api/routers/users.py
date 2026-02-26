from datetime import UTC, datetime

from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from api.dependencies.s3 import S3
from core.app_exception import AppException
from core.auth import hash_password, validate_password
from core.logger import get_logger
from core.rate_limit import limiter
from fastapi import Body, Request, Response
from fastapi.responses import JSONResponse
from models.enums import AppErrorCode, Permission
from models.filter import (
    UserFilter,
)
from models.pagination import Paginated
from models.tables import (
    Comment,
    Document,
    Group,
    GroupReaction,
    Membership,
    Reaction,
    Task,
    TaskResponse,
    User,
)
from models.user import (
    ExportComment,
    ExportMembership,
    ExportProfile,
    ExportReaction,
    ExportTaskResponse,
    UserDataExport,
    UserPrivate,
    UserRead,
    UserUpdate,
)
from sqlmodel import select
from util.api_router import APIRouter
from util.group_cleanup import cleanup_s3_keys, prepare_group_deletion
from util.queries import Guard
from util.response import ExcludableFieldsJSONResponse

users_logger = get_logger("app")

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

# region Users


@router.get("/me", response_model=UserPrivate)
async def read_current_user(user: User = Authenticate()) -> User:
    """Get the currently authenticated user."""
    return user


@router.get(
    "/",
    response_model=Paginated[UserRead],
    response_class=ExcludableFieldsJSONResponse,
)
async def list_users(
    _: BasicAuthentication,
    users: Paginated[User] = PaginatedResource(User, UserFilter),
) -> Paginated[UserRead]:
    """Get all users."""
    return users


@router.get("/{user_id}", response_model=UserRead)
async def read_user(_: BasicAuthentication, user: User = Resource(User, param_alias="user_id")) -> User:
    """Get a user by ID."""
    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    db: Database,
    user: User = Authenticate([Guard.is_account_owner()]),
    user_update: UserUpdate = Body(...),
) -> User:
    """Update a user."""
    # Apply updates to the user fields
    await db.merge(user)
    if user_update.new_password:
        # Re-validate the old password
        if not validate_password(user, user_update.old_password):
            raise AppException(
                status_code=403,
                error_code=AppErrorCode.INVALID_CREDENTIALS,
                detail="Invalid old password",
            )
        user.password = hash_password(user_update.new_password)
    user.sqlmodel_update(user_update.model_dump(exclude_unset=True, exclude={"old_password", "new_password"}))
    await db.commit()
    await db.refresh(user)

    return user


@router.get("/{user_id}/export", response_model=UserDataExport)
@limiter.limit("3/hour")
async def export_user_data(
    request: Request,
    db: Database,
    user: User = Authenticate([Guard.is_account_owner()]),
) -> JSONResponse:
    """Export all personal data for GDPR portability (Art. 20).

    Returns a JSON file containing the user's profile,
    memberships, comments, reactions, and task responses.
    Rate limited to 3 requests per hour.
    """
    user_id = user.id

    # Memberships with group names
    result = await db.exec(select(Membership, Group.name).join(Group, Membership.group_id == Group.id).where(Membership.user_id == user_id))
    memberships = [
        ExportMembership(
            group_name=group_name,
            is_owner=m.is_owner,
            accepted=m.accepted,
            permissions=[str(p) for p in m.permissions],
            joined_at=m.created_at,
        )
        for m, group_name in result.all()
    ]

    # Comments with document/group context
    result = await db.exec(
        select(Comment, Document.name, Group.name)
        .join(Document, Comment.document_id == Document.id)
        .join(Group, Document.group_id == Group.id)
        .where(Comment.user_id == user_id)
    )
    comments = [
        ExportComment(
            document_name=doc_name,
            group_name=grp_name,
            content=c.content,
            annotation=c.annotation,
            visibility=str(c.visibility),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c, doc_name, grp_name in result.all()
    ]

    # Reactions with emoji and comment preview
    result = await db.exec(
        select(Reaction, GroupReaction.emoji, Comment.content)
        .join(
            GroupReaction,
            Reaction.group_reaction_id == GroupReaction.id,
        )
        .join(Comment, Reaction.comment_id == Comment.id)
        .where(Reaction.user_id == user_id)
    )
    reactions = [
        ExportReaction(
            emoji=str(emoji),
            comment_content_preview=(content[:80] + "..." if content and len(content) > 80 else content),
            created_at=r.created_at,
        )
        for r, emoji, content in result.all()
    ]

    # Task responses with question context
    result = await db.exec(
        select(TaskResponse, Task.question, Document.name)
        .join(Task, TaskResponse.task_id == Task.id)
        .join(Document, Task.document_id == Document.id)
        .where(TaskResponse.user_id == user_id)
    )
    task_responses = [
        ExportTaskResponse(
            document_name=doc_name,
            task_question=question,
            answer=tr.answer,
            is_correct=tr.is_correct,
            attempts=tr.attempts,
            created_at=tr.created_at,
        )
        for tr, question, doc_name in result.all()
    ]

    export = UserDataExport(
        exported_at=datetime.now(UTC),
        profile=ExportProfile.model_validate(user.model_dump()),
        memberships=memberships,
        comments=comments,
        reactions=reactions,
        task_responses=task_responses,
    )

    return JSONResponse(
        content=export.model_dump(mode="json"),
        headers={
            "Content-Disposition": ('attachment; filename="text-ur-data-export.json"'),
        },
    )


@router.delete("/{user_id}")
async def delete_user(
    db: Database,
    s3: S3,
    _: User = Authenticate([Guard.is_account_owner()]),
    user: User = Resource(User, param_alias="user_id"),
) -> Response:
    """Delete a user and handle owned groups.

    For each group the user owns:
    - If another admin exists, transfer ownership to them.
    - Otherwise, delete the group (with S3 cleanup).
    """
    # Find all groups this user owns
    result = await db.exec(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.is_owner.is_(True),
        )
    )
    owned_memberships = list(result.all())

    s3_keys_to_delete: list[str] = []

    for owner_membership in owned_memberships:
        group_id = owner_membership.group_id

        # Find another admin in the group to transfer to
        result = await db.exec(
            select(Membership).where(
                Membership.group_id == group_id,
                Membership.user_id != user.id,
                Membership.accepted.is_(True),
                Membership.permissions.contains([Permission.ADMINISTRATOR.value]),
            )
        )
        next_admin = result.first()

        if next_admin:
            # Transfer ownership to the next admin
            next_admin.is_owner = True
            db.add(next_admin)
        else:
            # No admin available — stage group for deletion
            s3_keys_to_delete.extend(await prepare_group_deletion(db, group_id))

    await db.delete(user)
    await db.commit()

    # Clean up S3 objects after successful DB commit
    cleanup_s3_keys(
        s3,
        s3_keys_to_delete,
        users_logger,
        f"user {user.id} account deletion",
    )

    return Response(status_code=204)


# endregion
