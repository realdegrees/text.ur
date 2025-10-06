import enum
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, get_args, get_origin

from pydantic import EmailStr, Field
from pydantic.fields import FieldInfo
from sqlalchemy import ColumnElement, and_
from sqlalchemy.orm import InstrumentedAttribute
from sqlmodel import SQLModel, exists, select
from sqlmodel.main import default_registry

from models.tables import (
    Document,
    Group,
    Membership,
    ShareLink,
    User,
)

Base = default_registry.generate_base()
Operator = Literal["==", ">=", "<=", ">", "<", "ilike", "like", "exists", "!="]
OperatorMap = {
    "equals": {"==", "!="},
    "contains": {"ilike", "like", "==", "!="},
    "numeric": {"==", ">=", "<=", ">", "<", "!="},
    "exists": {"exists"},
}


class Filter(SQLModel):
    field: str = Field()
    operator: Operator = Field()
    value: str = Field()


@dataclass
class JoinInfo:
    target: InstrumentedAttribute
    join_type: Literal["inner", "outer"] = "outer"


@dataclass
class FilterableField:
    """Represents a filterable field with dot path, join path (list of join functions), and clause."""

    name: str
    field: ColumnElement
    clause: Callable[[Operator, str], ColumnElement[bool]]
    allowed_operators: list[Operator]
    join: JoinInfo | None = None
    allow_sorting: bool = False


@dataclass
class FilterMeta:
    """Metadata for a filterable field, encapsulating clause logic."""

    container_name: str | None = None
    field: ColumnElement = None
    exclude_operators: set[str] | None = None
    include_operators: set[str] | None = None
    join: JoinInfo | None = None
    condition: ColumnElement[bool] | None = None
    allow_sorting: bool = False

    @staticmethod
    def from_filter(filter_model: SQLModel) -> list[FilterableField]:
        """Collect filterable fields from a filter model."""
        fields: list[FilterableField] = []
        for field_name, model_field in filter_model.model_fields.items():
            if not model_field.json_schema_extra:
                continue
            filter_meta: FilterMeta = model_field.json_schema_extra.get("filter")

            if not filter_meta:
                raise ValueError(f"Field '{field_name}' is missing 'filter' metadata.")

            filterable_field = filter_meta.to_filterable_field(field_name, model_field)
            if filterable_field:
                fields.append(filterable_field)
        return fields

    @staticmethod
    def infer_type(annotation: type) -> tuple[type, str]:
        """Infer the filter type from a field annotation."""
        # Handle Union types (including Optional)
        origin = get_origin(annotation)
        if origin is not None:
            args = get_args(annotation)
            # Recursively check all types in the union, ignoring NoneType
            for arg in args:
                if arg is type(None):
                    continue
                return FilterMeta.infer_type(arg)
            raise ValueError(f"Cannot infer filter type from annotation: {annotation}")
        if isinstance(annotation, type):
            if issubclass(annotation, SQLModel):
                return bool, "exists"
            if issubclass(annotation, enum.Enum) or issubclass(annotation, bool):
                return annotation, "equals"
            if issubclass(annotation, int | datetime):
                return annotation, "numeric"
            if issubclass(annotation, str) or issubclass(annotation, EmailStr):
                return annotation, "contains"

            if annotation == None.__class__:
                return bool, "exists"
        raise ValueError(f"Cannot infer filter type from annotation: {annotation}")

    def _allowed_operators(self, filter_type: str) -> list[Operator]:
        """Return allowed operators for this filter type, minus any excluded."""
        ops = set(OperatorMap.get(filter_type, set()))
        if self.exclude_operators:
            ops -= set(self.exclude_operators)
        if self.include_operators:
            ops |= set(self.include_operators)
        return list(ops)

    def to_filterable_field(self, field_name: str, field_info: FieldInfo) -> FilterableField | None:
        """Get FilterableField instance for this filter metadata."""
        field_annotation = field_info.annotation
        inferred_type, filter_type = FilterMeta.infer_type(field_annotation)
        allowed_operators = self._allowed_operators(filter_type)

        def validate_clause(operator: Operator, value: str) -> ColumnElement[bool]:
            if operator not in allowed_operators:
                raise ValueError(f"Operator '{operator}' not allowed for field '{field_name}'. Allowed: {allowed_operators}")
            return self._build_clause(operator, value, filter_type, inferred_type)

        # Only allow direct fields, no joins or recursion
        return FilterableField(
            name=field_name,
            field=self.field,
            join=self.join,
            clause=validate_clause,
            allowed_operators=allowed_operators,
            allow_sorting=self.allow_sorting,
        )

    def _build_clause(self, operator: Operator, value: Any, filter_type: str, inferred_type: type) -> ColumnElement[bool]:  # noqa: ANN401, C901
        """Return a SQLAlchemy clause based on the filter type and value."""
        # Convert value to the appropriate type based on inferred_type
        try:
            if inferred_type is bool or operator == "exists":
                # For 'exists' operator, value should be a string indicating truthiness
                value = str(value).lower() in ("1", "true")
            elif inferred_type is datetime:
                value = datetime.fromisoformat(value)
            else:
                value = inferred_type(value)
        except Exception as e:
            raise ValueError(f"Invalid value '{value}' for type '{inferred_type.__name__}': {e}") from e

        def get_where_clause(operator: Operator = operator, value: Any = value) -> ColumnElement[bool]:  # noqa: ANN401, C901
            if operator == "==":
                return self.field == value
            if operator == "!=" and self.join is None:
                return (self.field != value) | (self.field == None)  # noqa: E711
            if operator == "!=" and self.join is not None:
                return self.field == value
            if operator == "ilike":
                return self.field.ilike(f"%{value}%")
            if operator == "like":
                return self.field.like(f"%{value}%")
            if operator == ">=":
                return self.field >= value
            if operator == "<=":
                return self.field <= value
            if operator == ">":
                return self.field > value
            if operator == "<":
                return self.field < value
            if operator == "exists":
                exists_flag = str(value).lower() in ("1", "true", "yes", "on")
                return self.field != None if exists_flag else self.field == None  # noqa: E711
            raise ValueError(f"Unknown filter type or operator: {filter_type}, {operator}")

        if self.join:
            # self.field is the linked column, e.g. AssetSetLink.asset_id
            # self.join.target is the relationship attribute, e.g. AssetSet.asset_set_links
            rel_attr: InstrumentedAttribute = self.join.target

            # get the target (child) entity class
            target_mapper = rel_attr.property.mapper.class_

            # parent column (primary key) of the outer entity
            parent_col = rel_attr.property.primaryjoin.left

            where_clause = get_where_clause()
            if self.condition is not None:
                where_clause = and_(where_clause, self.condition)

            clause = exists(
                select(1)
                .select_from(target_mapper)
                .where(where_clause)
                .where(parent_col == rel_attr.property.primaryjoin.right)
                .correlate_except(target_mapper)
            )
            return ~clause if operator == "!=" else clause
        else:
            return get_where_clause()

# ================================================================
# ========================= GROUP FILTER =========================
# ================================================================


class GroupFilter(SQLModel):
    """Declarative filter model for Group with filter metadata."""

    name: str = Field(json_schema_extra={"filter": FilterMeta(field=Group.name)})
    member_count: int = Field(json_schema_extra={"filter": FilterMeta(field=Group.member_count)})


# ================================================================
# ========================= DOCUMENT FILTER ======================
# ================================================================

class DocumentFilter(SQLModel):
    size_bytes: int = Field(
        json_schema_extra={"filter": FilterMeta(field=Document.size_bytes)},
    )
    group_id: int = Field(
        json_schema_extra={"filter": FilterMeta(field=Document.group_id)},
    )


# ================================================================
# ========================= GROUPMEMBERSHIP FILTER ===============
# ================================================================


class GroupMembershipFilter(SQLModel):
    user_id: int = Field( # TODO should probably be user name instead
        json_schema_extra={"filter": FilterMeta(field=Membership.user_id)},
    )

class UserMembershipFilter(SQLModel):
    group_id: int = Field( 
        json_schema_extra={"filter": FilterMeta(field=Membership.group_id)},
    )

# ================================================================
# ========================= COMMENT FILTER ====================
# ================================================================


class CommentFilter(SQLModel):
    pass

# ================================================================
# ========================= USER FILTER ==========================
# ================================================================


class UserFilter(SQLModel):
    username: str = Field(json_schema_extra={
        "filter": FilterMeta(field=User.username),
    })
    first_name: str = Field(
        json_schema_extra={"filter": FilterMeta(field=User.first_name)},
    )
    last_name: str = Field(
        json_schema_extra={"filter": FilterMeta(field=User.last_name)},
    )

# ================================================================
# ========================= SHARELINK FILTER =====================
# ================================================================

class ShareLinkFilter(SQLModel):
    label: str = Field(
        json_schema_extra={"filter": FilterMeta(field=ShareLink.label)},
    )
    expires_at: datetime = Field(
        json_schema_extra={"filter": FilterMeta(field=ShareLink.expires_at)},
    )