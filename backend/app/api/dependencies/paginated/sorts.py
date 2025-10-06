from collections.abc import Callable

from fastapi import Depends, Query, Request
from models.filter import Filter, FilterableField
from models.sort import Sort


def get_sorts_dependency(filterable_field_data: list[FilterableField]) -> Callable[[], Depends]:
    """Generate a FastAPI dependency to parse sorts from query parameters."""
    async def sorts(request: Request, _: str = Query(
            default=None,
            alias="sort",
            description=(
                "<details><summary>Expand to view available sorting fields</summary>"
                "<pre>"
                + "\n".join(f"❖ {field.name}" for field in filterable_field_data)
                + "</pre></details>"
            ))) -> list[Sort]:
        """Parse query parameters for sorts."""
        sorts: list[Sort] = []

        for key, value in request.query_params.multi_items():
            if not key.startswith("sort[") or value not in ("asc", "desc"):
                continue
            field = key[len("sort"):].replace("[", "").replace("]", "")
            is_valid_field = next((f for f in filterable_field_data if f.name == field), None)
            if is_valid_field:
                sorts.append(Sort(field=field, direction=value))

        return sorts
    return Depends(sorts)