import enum
import json
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

from models.enums import Visibility
from models.tables import (
    Comment,
    Document,
    Group,
    Membership,
    ShareLink,
    User,
)

Base = default_registry.generate_base()
Operator = Literal["==", ">=", "<=", ">", "<", "ilike", "like", "exists", "!=", "in", "notin"]
OperatorMap = {
    "equals": {"==", "!=", "in", "notin"},
    "contains": {"ilike", "like", "==", "!=", "in", "notin"},
    "numeric": {"==", ">=", "<=", ">", "<", "!=", "in", "notin"},
    "exists": {"exists"},
}


class BaseFilterModel(SQLModel):
    """Base class for filter models that provides filter metadata without serialization issues."""
    
    @classmethod
    def get_filter_metadata(cls) -> dict[str, "FilterMeta"]:
        """Return a mapping of field names to FilterMeta objects. Subclasses should override this method to define their filter metadata."""
        return {}


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
    clause: Callable[[Operator, str, User | None], ColumnElement[bool]]
    allowed_operators: list[Operator]
    join: JoinInfo | None = None
    allow_sorting: bool = False
    requires_user: bool = False
    exclude_field: str | None = None
    inferred_type: type = str


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
    user_condition: Callable[[User | None], ColumnElement[bool]] | None = None
    exclude: bool | str | ColumnElement | InstrumentedAttribute | None = None

    @staticmethod
    def _extract_field_name(attr: ColumnElement | InstrumentedAttribute | str) -> str:
        """Extract field name from a ColumnElement, InstrumentedAttribute, or return string as-is."""
        if isinstance(attr, str):
            return attr
        if hasattr(attr, "key"):
            return attr.key
        if hasattr(attr, "name"):
            return attr.name
        raise ValueError(f"Cannot extract field name from {type(attr)}")

    @staticmethod
    def from_filter(filter_model: SQLModel) -> list[FilterableField]:
        """Collect filterable fields from a filter model."""
        fields: list[FilterableField] = []
        
        # Get filter metadata from the model's get_filter_metadata method if available
        filter_metadata_map: dict[str, FilterMeta] = {}
        if hasattr(filter_model, "get_filter_metadata"):
            filter_metadata_map = filter_model.get_filter_metadata()
        
        for field_name, model_field in filter_model.model_fields.items():
            # Try to get filter metadata from the classmethod
            filter_meta = filter_metadata_map.get(field_name)
            
            if not filter_meta:
                continue

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

        def validate_clause(operator: Operator, value: str, user: User | None = None) -> ColumnElement[bool]:
            if operator not in allowed_operators:
                raise ValueError(f"Operator '{operator}' not allowed for field '{field_name}'. Allowed: {allowed_operators}")
            return self._build_clause(operator, value, filter_type, inferred_type, user)

        # Resolve exclude parameter
        exclude_field: str | None = None
        if self.exclude is True:
            exclude_field = field_name
        elif self.exclude is not None and self.exclude is not False:
            exclude_field = FilterMeta._extract_field_name(self.exclude)

        return FilterableField(
            name=field_name,
            field=self.field,
            join=self.join,
            clause=validate_clause,
            allowed_operators=allowed_operators,
            allow_sorting=self.allow_sorting,
            requires_user=self.user_condition is not None,
            exclude_field=exclude_field,
            inferred_type=inferred_type,
        )

    def _convert_value(self, value: Any, inferred_type: type, operator: Operator) -> Any:  # noqa: ANN401, C901
        """Convert value to the appropriate type based on inferred_type."""
        try:
            if inferred_type is bool or operator == "exists":
                return str(value).lower() in ("1", "true")
            elif inferred_type is datetime:
                return datetime.fromisoformat(value)
            elif operator in ("in", "notin"):
                # Parse value into a list
                items: list[Any]
                try:
                    parsed = json.loads(value)
                    if not isinstance(parsed, list):
                        raise ValueError("Parsed JSON is not a list")
                    items = parsed
                except Exception as e:
                    raise ValueError("Value for 'in'/'notin' operator must be a JSON array") from e

                # Only support string and numeric inferred types
                if inferred_type is str:
                    converted: list[str] = []
                    for elem in items:
                        if isinstance(elem, (str, int, float)):
                            converted.append(str(elem))
                        else:
                            raise ValueError(f"Invalid array element type: {type(elem)}")
                    return converted
                elif inferred_type in (int, float):
                    converted: list[Any] = []
                    for elem in items:
                        if isinstance(elem, (int, float)):
                            converted.append(inferred_type(elem))
                        elif isinstance(elem, str):
                            try:
                                converted.append(inferred_type(elem))
                            except Exception as exc:
                                raise ValueError(f"Invalid numeric value '{elem}': {exc}") from exc
                        else:
                            raise ValueError(f"Invalid array element type: {type(elem)}")
                    return converted
                else:
                    raise ValueError("Only string and numeric types supported for 'in'/'notin' operator")
            else:
                return inferred_type(value)
        except Exception as e:
            raise ValueError(f"Invalid value '{value}' for type '{inferred_type.__name__}': {e}") from e

    def _get_base_where_clause(self, operator: Operator, value: Any) -> ColumnElement[bool]:  # noqa: ANN401, C901
        """Build base where clause for a given operator and value."""
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
        if operator == "in":
            return self.field.in_(value)
        if operator == "notin":
            return ~self.field.in_(value)
        raise ValueError(f"Unknown operator: {operator}")

    def _build_clause(self, operator: Operator, value: Any, filter_type: str, inferred_type: type, user: User | None = None) -> ColumnElement[bool]:  # noqa: ANN401
        """Return a SQLAlchemy clause based on the filter type and value."""
        converted_value = self._convert_value(value, inferred_type, operator)
        base_where_clause = self._get_base_where_clause(operator, converted_value)

        if self.join:
            rel_attr: InstrumentedAttribute = self.join.target
            target_mapper = rel_attr.property.mapper.class_
            parent_col = rel_attr.property.primaryjoin.left

            where_clause = base_where_clause
            
            if self.condition is not None:
                where_clause = and_(where_clause, self.condition)
            
            if self.user_condition and user:
                user_clause = self.user_condition(user)
                where_clause = and_(where_clause, user_clause)

            clause = exists(
                select(1)
                .select_from(target_mapper)
                .where(where_clause)
                .where(parent_col == rel_attr.property.primaryjoin.right)
                .correlate_except(target_mapper)
            )
            return ~clause if operator == "!=" else clause
        else:
            if self.user_condition and user:
                user_clause = self.user_condition(user)
                return and_(base_where_clause, user_clause)
            return base_where_clause

# ================================================================
# ========================= GROUP FILTER =========================
# ================================================================


class GroupFilter(BaseFilterModel):
    """Declarative filter model for Group with filter metadata."""

    name: str = Field()
    member_count: int = Field()
    accepted: bool = Field()

    @classmethod
    def get_filter_metadata(cls) -> dict[str, FilterMeta]:
        """Return filter metadata for GroupFilter fields."""
        return {
            "name": FilterMeta(field=Group.name),
            "member_count": FilterMeta(field=Group.member_count),
            "accepted": FilterMeta(
                field=Membership.accepted,
                join=JoinInfo(target=Group.memberships),
                user_condition=lambda user: Membership.user_id == user.id if user else None,
                exclude=True,
            ),
        }


# ================================================================
# ========================= DOCUMENT FILTER ======================
# ================================================================

class DocumentFilter(BaseFilterModel):
    size_bytes: int = Field()
    group_id: str = Field()

    @classmethod
    def get_filter_metadata(cls) -> dict[str, FilterMeta]:
        """Return filter metadata for DocumentFilter fields."""
        return {
            "size_bytes": FilterMeta(field=Document.size_bytes),
            "group_id": FilterMeta(field=Document.group_id, exclude=Document.group),
        }


# ================================================================
# ========================= GROUPMEMBERSHIP FILTER ===============
# ================================================================


class MembershipFilter(BaseFilterModel):
    user_id: int = Field()
    group_id: str = Field()
    accepted: bool = Field()
    sharelink_id: str = Field()

    @classmethod
    def get_filter_metadata(cls) -> dict[str, FilterMeta]:
        """Return filter metadata for MembershipFilter fields."""
        return {
            "user_id": FilterMeta(field=Membership.user_id, exclude=Membership.user),
            "group_id": FilterMeta(field=Membership.group_id, exclude=Membership.group),
            "accepted": FilterMeta(field=Membership.accepted),
            "sharelink_id": FilterMeta(field=Membership.sharelink_id, exclude=Membership.share_link),
        }


# ================================================================
# ========================= COMMENT FILTER ====================
# ================================================================


class CommentFilter(BaseFilterModel):    
    visibility: Visibility = Field()
    user_id: int = Field()
    document_id: str = Field()
    parent_id: int = Field()
    annotation: dict = Field()
    id: int = Field()
    
    @classmethod
    def get_filter_metadata(cls) -> dict[str, FilterMeta]:
        """Return filter metadata for Comment fields."""
        return {
            "visibility": FilterMeta(field=Comment.visibility),
            "user_id": FilterMeta(field=Comment.user_id, exclude=Comment.user),
            "document_id": FilterMeta(field=Comment.document_id, exclude=Comment.document),
            "parent_id": FilterMeta(field=Comment.parent_id, exclude=Comment.parent, include_operators={"exists"}),
            "has_annotations": FilterMeta(
                field=Comment.annotation,
                include_operators={"exists"},
            ),
            "id": FilterMeta(field=Comment.id),
        }

# ================================================================
# ========================= USER FILTER ==========================
# ================================================================


class UserFilter(BaseFilterModel):
    username: str = Field()
    first_name: str = Field()
    last_name: str = Field()
    group_id: str = Field()

    @classmethod
    def get_filter_metadata(cls) -> dict[str, FilterMeta]:
        """Return filter metadata for UserFilter fields."""
        return {
            "username": FilterMeta(field=User.username),
            "first_name": FilterMeta(field=User.first_name),
            "last_name": FilterMeta(field=User.last_name),
            "group_id": FilterMeta(
                field=Membership.group_id,
                join=JoinInfo(target=User.memberships),
            ),
        }

# ================================================================
# ========================= SHARELINK FILTER =====================
# ================================================================

class ShareLinkFilter(BaseFilterModel):
    label: str = Field()
    expires_at: datetime = Field()
    author_id: int = Field()

    @classmethod
    def get_filter_metadata(cls) -> dict[str, FilterMeta]:
        """Return filter metadata for ShareLinkFilter fields."""
        return {
            "label": FilterMeta(field=ShareLink.label),
            "expires_at": FilterMeta(field=ShareLink.expires_at),
            "author_id": FilterMeta(field=ShareLink.author_id, exclude=ShareLink.author),
        }