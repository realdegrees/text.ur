"""Exports the Resource dependency which is a dependency factory for complex filter queries."""

from collections.abc import Callable
from typing import cast, overload

from api.dependencies.authentication import Authenticate, BasicAuthentication
from api.dependencies.database import Database
from core.logger import get_logger
from fastapi import Depends, HTTPException, Path
from models.base import BaseModel
from models.tables import User
from sqlalchemy import ColumnElement, Integer, String
from sqlmodel import select

DEFAULT_ID_ALIAS: str = "id"

logger = get_logger("app")

@overload
def Resource[ResourceModel: BaseModel](
    resource: type[ResourceModel],
    *,
    key_column: ColumnElement | None = None,
    param_alias: str = DEFAULT_ID_ALIAS,
    index_field_type: type = int,
    model_validator: Callable[[ResourceModel, User | None], ResourceModel] | None = None,
    raise_on_not_found: bool = True,
) -> Callable[..., ResourceModel]:
    ...

@overload
def Resource[ResourceModel: BaseModel](
    resource: type[ResourceModel],
    *,
    key_column: ColumnElement | None = None,
    param_alias: str = DEFAULT_ID_ALIAS,
    index_field_type: type = int,
    model_validator: Callable[[ResourceModel, User | None], ResourceModel] | None = None,
    raise_on_not_found: bool = False,
) -> Callable[..., ResourceModel | None]:
    ...


def Resource[ResourceModel: BaseModel](
    resource: type[ResourceModel],
    *,
    key_column: ColumnElement | None = None,
    param_alias: str = DEFAULT_ID_ALIAS,
    index_field_type: type = int,
    model_validator: Callable[[ResourceModel, User | None], ResourceModel] | None = None,
    raise_on_not_found: bool = True,
) -> Callable[..., ResourceModel] | Callable[..., ResourceModel | None]:
    """Customizable resource dependency."""
    if key_column is None:
        key_column = resource.id

    async def resource_dependency(
        db: Database,
        resource_id: int | str = Path(alias=param_alias, description=f"{resource.__name__} identifier"),  # type: ignore[valid-type]
    ) -> ResourceModel | None:
        """Load a single resource instance."""
        typed_resource_id = resource_id
        if hasattr(key_column, "type"):
            if isinstance(key_column.type, Integer):
                try:
                    typed_resource_id = int(resource_id)
                except (ValueError, TypeError):
                    pass
            elif isinstance(key_column.type, String):
                typed_resource_id = str(resource_id)

        query = select(resource).where(key_column == typed_resource_id)
        result = await db.exec(query)
        res = result.first()
        if res is None and raise_on_not_found:
            raise HTTPException(status_code=404, detail=f"{resource.__name__} not found")
        return cast(ResourceModel, res) if res else None

    async def dependency(
        user: User | None = Authenticate(strict=False),
        res: ResourceModel | None = Depends(resource_dependency),
    ) -> ResourceModel | None:
        """Validate access and optionally post-process the resource."""
        return model_validator(res, user) if model_validator else res

    return Depends(dependency)

