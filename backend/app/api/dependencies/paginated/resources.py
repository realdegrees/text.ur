"""Handle paginated resource queries with advanced filtering and sorting."""

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.paginated.filters import get_filters_dependency
from api.dependencies.paginated.sorts import get_sorts_dependency
from fastapi import Depends, Request
from fastapi.datastructures import QueryParams
from models.filter import (
    Filter,
    FilterableField,
    FilterMeta,
)
from models.pagination import Paginated, PaginatedBase, Pagination
from models.sort import Sort
from models.tables import User
from sqlalchemy import ColumnElement, func
from sqlalchemy.sql import tuple_
from sqlmodel import SQLModel, select
from sqlmodel.orm.session import SelectOfScalar
from util.queries import EndpointGuard

# Define a generic model type.
Model = TypeVar("Model", bound=SQLModel)
FilterModel = TypeVar("FilterModel", bound=SQLModel)


def build_paginated_description(base_description: str, guards: Sequence[EndpointGuard]) -> str:
    """Build endpoint description with guard exclusion information.
    
    Args:
        base_description: The main endpoint description
        guards: Sequence of guards to extract exclusions from
    
    Returns:
        Complete description with exclusion notices appended
    
    """
    guard_exclusions = []
    for guard in guards:
        excluded = guard.get_excluded_fields()
        if excluded:
            guard_exclusions.extend(excluded)
    
    if guard_exclusions:
        exclusion_notice = (
            f"\\n\\n**Field Exclusions:** The following fields are always excluded from this endpoint's "
            f"responses due to access control rules: `{'`, `'.join(sorted(set(guard_exclusions)))}`"
        )
        return base_description + exclusion_notice
    
    return base_description


def PaginatedResource(  # noqa: C901
    base_model: type[Model],
    filter_model: type[FilterModel],
    *,
    key_columns: list[ColumnElement] | None = None,
    validate: Callable[[Paginated[Model], User | None], Paginated[Model]] | None = None,
    guards: Sequence[EndpointGuard] = (),
    description_suffix: str | None = None,
) -> Callable[..., Paginated[Model]]:
    """Generate an advanced filter+sort query dependency with pagination.
    
    Args:
        base_model: The SQLModel class to query
        filter_model: The filter model class defining available filters
        key_columns: Custom primary key columns (defaults to base_model.id)
        validate: Optional validator function to transform results
        guards: Sequence of EndpointGuard instances for access control
        description_suffix: Additional text to append to auto-generated description
    
    """
    filterable_field_data = FilterMeta.from_filter(filter_model)

    def build_conditions(
        filters: list[Filter], 
        filterable_field_data: list[FilterableField] = filterable_field_data,
        session_user: User | None = None,
    ) -> list[ColumnElement[bool]]:
        """Transform filters into joins, conditions, and options for build_query using join and clause from FilterableField."""
        conditions: list[ColumnElement[bool]] = []

        for filter_item in filters:
            field_data = next((f for f in filterable_field_data if f.name == filter_item.field), None)

            if field_data is None:
                continue

            conditions.append(field_data.clause(filter_item.operator, filter_item.value, session_user))

        return conditions

    def apply_joins(query: SelectOfScalar[Model], fields: list[str], filterable_field_data: list[FilterableField]) -> SelectOfScalar[Model]:
        """Apply necessary joins to the query based on the filters."""
        for field in fields:
            filterable_field = next((f for f in filterable_field_data if f.name == field), None)
            if filterable_field and filterable_field.join:
                join_target = filterable_field.join.target
                join_type = filterable_field.join.join_type.lower()

                if join_type == "inner":
                    query = query.join(join_target)
                elif join_type == "outer":
                    query = query.outerjoin(join_target)
        return query

    # Build order expressions
    def build_order_expressions(
        sorts: list[Sort], filterable_field_data: list[FilterableField] = filterable_field_data
    ) -> tuple[list[ColumnElement], list[ColumnElement]]:
        """Turn Sort objects into SQLAlchemy order expressions and labeled columns."""
        columns: list[ColumnElement] = []
        order_expressions: list[ColumnElement] = []

        for sort in sorts:
            field_data = next((f for f in filterable_field_data if f.name == sort.field), None)
            if field_data is None:
                continue
            column = field_data.field
            columns.append(column.label(f"order_{len(columns)}"))  # Labeled column for SELECT
            order_expressions.append(
                column.desc() if sort.direction.lower() == "desc" else column.asc()
            )  # Direction for ORDER BY

        return columns, order_expressions
    

    async def dependency( # noqa: C901
        db: Database,
        request: Request,
        pagination: Pagination = Depends(),
        filters: list[Filter] = get_filters_dependency(filterable_field_data),
        sorts: list[Sort] = get_sorts_dependency(filterable_field_data),
        session_user: User | None = Authenticate(strict=False),
    ) -> Paginated[Model]:            
        # Resolve primary key(s)
        resolved_key_columns: list[ColumnElement] = key_columns if key_columns else [base_model.id]

        # Collect fields to exclude from response
        excluded_fields: list[str] = []
        
        # 1. Guard-based exclusions (static, based on endpoint access rules)
        for guard in guards:
            excluded_fields.extend(guard.get_excluded_fields())
        
        # 2. Filter-based exclusions (dynamic, based on active equality filters)
        for filter_item in filters:
            # Only exclude fields when using the equality operator
            if filter_item.operator == "==":
                field_data = next((f for f in filterable_field_data if f.name == filter_item.field), None)
                if field_data and field_data.exclude_field:
                    excluded_fields.append(field_data.exclude_field)

        # Build filter conditions
        filter_conditions = build_conditions(filters, session_user=session_user)

        # Map Sort -> Column
        labeled_order_columns, order_expressions = build_order_expressions(sorts)

        # Base query with filters (distinct primary keys + order columns)
        base_query = select(*resolved_key_columns, *labeled_order_columns).distinct()
        base_query = apply_joins(
            base_query,
            [*[f.field for f in filters], *[s.field for s in sorts]],
            filterable_field_data,
        )
        if filter_conditions:
            base_query = base_query.where(*filter_conditions)
            
        params: dict[str, Any] = {}
        # Add filters to params as dict entries
        for filter_item in filters:
            params[filter_item.field] = filter_item.value
        
        # Add query parameters from request (excluding filters)
        if isinstance(request.query_params, QueryParams):
            for key, value in request.query_params.multi_items():
                if key not in params and not key.startswith("filter[["):
                    params[key] = value
                    
        # Add path parameters from request
        for key, value in request.path_params.items():
            if key not in params:
                params[key] = value

        # Add custom query modifications
        if guards:
            for guard in guards:
                base_query = base_query.where(guard.clause(session_user, params, multi=True))

        # Ensure GROUP BY includes all selected columns
        group_by_columns = resolved_key_columns + list(labeled_order_columns)
        base_query = base_query.group_by(*group_by_columns)

        # Apply sorting before pagination
        sorted_query = base_query.order_by(*order_expressions, *resolved_key_columns)

        # Count total results after filtering and sorting
        total_count = db.scalar(select(func.count()).select_from(sorted_query.subquery()))

        # Apply pagination after sorting
        paginated_subq = sorted_query.offset(pagination.offset).limit(pagination.limit).subquery("paginated_subq")

        # Build ordering expressions using the labeled columns
        subq_order_cols = [
            getattr(paginated_subq.c, f"order_{i}").desc()
            if sorts[i].direction.lower() == "desc"
            else getattr(paginated_subq.c, f"order_{i}").asc()
            for i in range(len(order_expressions))
        ]

        # Join back to full table rows
        if len(resolved_key_columns) == 1:
            pk_col = resolved_key_columns[0]
            join_condition = pk_col == getattr(paginated_subq.c, pk_col.name)
        else:
            join_condition = tuple_(*resolved_key_columns) == tuple_(*[getattr(paginated_subq.c, col.name) for col in resolved_key_columns])

        # Final selection with ordering
        selection = select(base_model).join(paginated_subq, join_condition).order_by(*subq_order_cols)
        rows = db.exec(selection).all()

        # Return paginated result
        paginated_payload = PaginatedBase(
            data=rows,
            total=total_count,
            offset=pagination.offset,
            limit=pagination.limit,
            filters=filters,
            order_by=sorts,
            excluded_fields=excluded_fields,
        )

        if validate:
            paginated_payload = validate(paginated_payload, session_user)

        return paginated_payload

    return Depends(dependency)
