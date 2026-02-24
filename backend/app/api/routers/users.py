from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from api.dependencies.s3 import S3
from core.app_exception import AppException
from core.auth import hash_password, validate_password
from core.logger import get_logger
from fastapi import Body, Response
from models.enums import AppErrorCode, Permission
from models.filter import (
    UserFilter,
)
from models.pagination import Paginated
from models.tables import Membership, User
from models.user import UserPrivate, UserRead, UserUpdate
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
async def read_current_user(
    user: User = Authenticate()
) -> User:
    """Get the currently authenticated user."""
    return user


@router.get("/", response_model=Paginated[UserRead], response_class=ExcludableFieldsJSONResponse)
async def list_users(
    _: BasicAuthentication,
    users: Paginated[User] = PaginatedResource(
        User, UserFilter)
) -> Paginated[UserRead]:
    """Get all users."""
    return users


@router.get("/{user_id}", response_model=UserRead)
async def read_user(
    _: BasicAuthentication,
    user: User = Resource(User, param_alias="user_id")
) -> User:
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
            raise AppException(status_code=403, error_code=AppErrorCode.INVALID_CREDENTIALS, detail="Invalid old password")
        user.password = hash_password(user_update.new_password)
    user.sqlmodel_update(user_update.model_dump(exclude_unset=True, exclude={"old_password", "new_password"}))
    await db.commit()
    await db.refresh(user)

    return user


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
                Membership.permissions.contains(
                    [Permission.ADMINISTRATOR.value]
                ),
            )
        )
        next_admin = result.first()

        if next_admin:
            # Transfer ownership to the next admin
            next_admin.is_owner = True
            db.add(next_admin)
        else:
            # No admin available — stage group for deletion
            s3_keys_to_delete.extend(
                await prepare_group_deletion(db, group_id)
            )

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