from collections.abc import Callable

from fastapi import Depends, Query, Request
from models.filter import Filter, FilterableField, Operator


def get_filters_dependency(filterable_field_data: list[FilterableField]) -> Callable[[], Depends]:
    """Generate a FastAPI dependency to parse filters from query parameters."""
    async def filters(request: Request, _: str = Query(
            default=None,
            alias="filter",
            description=(
                "<details><summary>Expand to view available filter fields</summary>"
                "<pre>"
                + "\n".join(f"❖ {field.name}" for field in filterable_field_data)
                + "</pre></details>"
            ))) -> list[Filter]:
        """Parse query parameters for filters."""
        filters: list[Filter] = []

        def _parse_filter_key(param: str) -> tuple[str | None, str | None]:
            """Extract field and operator from a filter parameter key."""
            if not param.startswith("filter["):
                return None, None
            inner = param[len("filter"):]  # keeps any bracket structure
            if "][" not in inner:
                return None, None
            field, operator = inner.split("][", 1)
            field = field.replace("[", "").replace("]", "")
            operator = operator.replace("[", "").replace("]", "")
            return field, operator

        for key, value in request.query_params.multi_items():
            field, operator = _parse_filter_key(key)
            if not field or not operator:
                continue

            is_valid_field = next((f for f in filterable_field_data if f.name == field), None)
            if not is_valid_field:
                continue

            # Skip if operator is not in `Operator` Literal
            if operator not in Operator.__args__:
                continue

            try:
                filters.append(Filter(field=field, operator=operator, value=value))
            except Exception as e:
                print(f"Error processing filter '{key}': {e}")

        return filters
    return Depends(filters)