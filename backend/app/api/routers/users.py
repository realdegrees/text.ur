from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from api.dependencies.paginated.resources import PaginatedResource
from api.dependencies.resource import Resource
from core.auth import hash_password, validate_password
from fastapi import Body, HTTPException, Response
from models.filter import (
    UserFilter,
)
from models.pagination import Paginated
from models.tables import User
from models.user import UserPrivate, UserRead, UserUpdate
from util.api_router import APIRouter
from util.queries import Guard

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


@router.get("/", response_model=Paginated[UserRead])
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
    db.merge(user)
    if user_update.new_password:
        # Re-validate the old password
        if not validate_password(user_update.old_password, user.password):
            raise HTTPException(status_code=403, detail="Forbidden: Invalid old password")
        user.password = hash_password(user_update.new_password)
    user.sqlmodel_update(*user_update.model_dump(exclude_unset=True, exclude={"old_password", "new_password"}))
    db.commit()
    db.refresh(user)

    return user


@router.delete("/{user_id}")
async def delete_user(
    db: Database,
    _: User = Authenticate([Guard.is_account_owner()]),
    user: User = Resource(User, param_alias="user_id"),
) -> Response:
    """Delete a user."""            
    db.delete(user)
    db.commit()
    return Response(status_code=204)

# endregion