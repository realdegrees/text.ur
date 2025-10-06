"""Exports the Resource dependency which is a dependency factory for complex filter queries."""

from collections.abc import Callable
from typing import TypeVar, cast, overload

from api.dependencies.authentication import BasicAuthentication
from api.dependencies.database import Database
from core.logger import get_logger
from fastapi import Depends, HTTPException, Path
from models.base import BaseModel
from models.tables import User

ResourceModel = TypeVar("ResourceModel", bound=BaseModel)
IndexFieldType = TypeVar("IndexFieldType")

DEFAULT_ID_ALIAS: str = "id"

logger = get_logger("app")

@overload
def Resource(
    resource: type[ResourceModel],
    *,
    param_alias: str = DEFAULT_ID_ALIAS,
    index_field_type: type = int,
    model_validator: Callable[[ResourceModel, User], ResourceModel] | None = None,
    raise_on_not_found: bool = True,
) -> Callable[..., ResourceModel]:
    ...

@overload
def Resource(
    resource: type[ResourceModel],
    *,
    param_alias: str = DEFAULT_ID_ALIAS,
    index_field_type: type = int,
    model_validator: Callable[[ResourceModel, User], ResourceModel] | None = None,
    raise_on_not_found: bool = False,
) -> Callable[..., ResourceModel | None]:
    ...


def Resource(
    resource: type[ResourceModel],
    *,
    param_alias: str = DEFAULT_ID_ALIAS,
    index_field_type: type = int,
    model_validator: Callable[[ResourceModel, User], ResourceModel] | None = None,
    raise_on_not_found: bool = True,
) -> Callable[..., ResourceModel] | Callable[..., ResourceModel | None]:
    """Customizable resource dependency."""

    def resource_dependency(
        db: Database,
        resource_id: index_field_type = Path(alias=param_alias, description=f"{resource.__name__} identifier"),  # type: ignore[valid-type]
    ) -> ResourceModel | None:
        """Load a single resource instance."""        
        queried_resource = db.get(resource, resource_id)  # type: ignore[operator]
        if queried_resource is None and raise_on_not_found:
            raise HTTPException(status_code=404, detail=f"{resource.__name__} not found")
        return cast(ResourceModel, queried_resource) if queried_resource else None

    async def dependency(
        user: BasicAuthentication,
        res: ResourceModel | None = Depends(resource_dependency),
    ) -> ResourceModel | None:
        """Validate access and optionally post-process the resource."""
        return model_validator(res, user) if model_validator else res

    return Depends(dependency)

