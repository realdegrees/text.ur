from __future__ import annotations

from collections.abc import Callable
from http.client import HTTPException
from typing import Any, Literal

from fastapi.datastructures import QueryParams
from models.enums import Permission, ViewMode, Visibility
from models.pagination import Paginated
from models.tables import (
    Comment,
    Document,
    Group,
    Membership,
    Reaction,
    User,
)
from sqlalchemy import and_, or_, select, true
from sqlalchemy.sql import ColumnElement
from sqlmodel import SQLModel

# TODO: I feel like there is a lot of duplicate code here that could be refactored by reusing guards, e.g. comment_access could reuse group_access to check group membership and then just add the visibility logic on top of that.


class EndpointGuard[T]:
    """Encapsulates a permission rule with both a SQLAlchemy clause and a Python predicate."""

    def __init__(
        self,
        clause_factory: Callable[[User, dict[str, Any]], ColumnElement[bool]],
        predicate: Callable[[T, User, dict[str, Any]], bool],
        exclude_fields: list[ColumnElement] | None = None,
    ) -> None:
        """Initialize the Guard with a clause factory, predicate, and optional field exclusions.
        
        Args:
            clause_factory: Function to generate SQLAlchemy WHERE clause
            predicate: Function to validate access on Python objects
            exclude_fields: List of model fields (e.g., Membership.user) to exclude from responses
        
        """
        self._clause_factory = clause_factory
        self._predicate = predicate
        self._exclude_fields = exclude_fields or []

    def clause(
        self,
        user: User,
        params: dict[str, Any],
        multi: bool = False
    ) -> ColumnElement[bool]:
        """Generate the SQLAlchemy clause for this guard."""
        return self._clause_factory(user, params, multi=multi)

    def predicate(
        self,
        obj: T,
        user: User,
    ) -> bool:
        """Run the Python-side predicate for this guard."""
        return self._predicate(obj, user)
    
    def get_excluded_fields(self) -> list[str]:
        """Get field names that should be excluded from responses."""
        return [field.key for field in self._exclude_fields]

    def validate(self, predicate_false_model: SQLModel, predicate_true_model: SQLModel) -> Callable[[Any, User], Any]:
        """Return a validator function that casts to one of the supplied models based on the guard's predicate result.

        If this is used on a PaginatedResource, it will automatically map over the items in the pagination.
        """

        def validator(obj: Paginated[T] | T, user: User | None) -> SQLModel:
            if isinstance(obj, Paginated):
                obj.data = [self.validate(predicate_false_model, predicate_true_model)(
                    item, user) for item in obj.data]
                return obj
            if user and self.predicate(obj, user):
                return predicate_true_model.model_validate(obj)
            else:
                return predicate_false_model.model_validate(obj)

        return lambda obj, user: validator(obj, user)


class Guard:
    """Utility class for permission guards."""

    @staticmethod
    def must_share_group() -> EndpointGuard[Membership]:
        """User can only access memberships of users that share at least one group with them."""
        # def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
        #     target_user_id = params.get("user_id", None)
        #     if not target_user_id:
        #         raise HTTPException(
        #             status_code=500, detail="Endpoint Guard misconfiguration: missing user_id parameter")
        #     return select(Membership).where(
        #         (Membership.user_id == target_user_id) &
        #         (Membership.group_id.in_(
        #             select(Membership.group_id).where(
        #                 Membership.accepted.is_(True),
        #                 Membership.user_id == user.id)
        #         ))
        #     ).exists()

        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            target_user_id = params.get("user_id", None)
            if not target_user_id and not multi:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing user_id parameter")

            if multi and target_user_id is None:
                # For multi-user queries (filtering Membership table directly)
                return Membership.group_id.in_(
                    select(Membership.group_id).where(
                        Membership.accepted.is_(True),
                        Membership.user_id == user.id
                    )
                )
            elif not multi:
                # For single user access checks - use EXISTS to avoid cross join
                return select(Membership).where(
                    (Membership.user_id == target_user_id) &
                    (Membership.group_id.in_(
                        select(Membership.group_id).where(
                            Membership.accepted.is_(True),
                            Membership.user_id == user.id)
                    ))
                ).exists()
            else:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: invalid configuration for multi parameter")

        def predicate(membership: Membership, user: User, params: dict[str, Any]) -> bool:
            return any(
                m.accepted and m.user_id == user.id
                for m in membership.group.memberships
            )

        return EndpointGuard(clause, predicate)

    @staticmethod
    def is_account_owner() -> EndpointGuard[User]:
        """User can only access their own account."""

        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            if multi:
                raise HTTPException(
                    # TODO: This should throw an internal error and print it to the logs
                    status_code=500, detail="Endpoint Guard misconfiguration: This Guard is not designed for use in PaginatedQueries!")
            target_user_id = params.get("user_id", None)
            if not target_user_id:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing user_id parameter")
            return (User.id == user.id) & (User.id == target_user_id)

        def predicate(user: User, session_user: User) -> bool:
            return user.id == session_user.id

        return EndpointGuard(clause, predicate)

    @staticmethod
    def document_access(  # noqa: C901
        require_permissions: set[Permission] | None = None,
        *,
        exclude_fields: list[ColumnElement] | None = None,
    ) -> EndpointGuard[Document]:
        """User can access a document based on its visibility and the given required permissions:

        - VisibilityType.private: only the group owner and administrators.
        - VisibilityType.restricted: private + and members with VIEW_RESTRICTED_DOCUMENTS permission.
        - VisibilityType.public: private, restricted + every group member.
        
        Args:
            require_permissions: Set of permissions required to access documents
            exclude_fields: List of model fields to exclude from responses
        
        """

        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            document_id = params.get("document_id", None)
            if not document_id and not multi:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing document_id parameter")

            def has_required_permissions() -> ColumnElement[bool]:
                """Check if user has all required permissions."""
                if not require_permissions:
                    return true()
                return and_(*(Membership.permissions.contains([permission.value]) for permission in require_permissions))

            def build_visibility_clause(doc_id_filter: ColumnElement[bool] | None = None) -> ColumnElement[bool]:
                """Build visibility clause, optionally filtering by document ID."""
                base_conditions = [
                    doc_id_filter] if doc_id_filter is not None else []
                admin_bypass = or_(
                    Membership.is_owner.is_(True),
                    Membership.permissions.contains(
                        [Permission.ADMINISTRATOR.value]),
                )

                return or_(
                    # Private documents: owner and admins only
                    and_(
                        *base_conditions,
                        Document.visibility == Visibility.PRIVATE,
                        Document.group_id.in_(
                            select(Membership.group_id).where(
                                Membership.user_id == user.id,
                                admin_bypass,
                            ))
                    ),
                    # Restricted documents: owner/admins OR members with VIEW_RESTRICTED_DOCUMENTS OR required permissions
                    and_(
                        *base_conditions,
                        Document.visibility == Visibility.RESTRICTED,
                        Document.group_id.in_(
                            select(Membership.group_id).where(
                                Membership.user_id == user.id,
                                Membership.accepted.is_(True),
                                or_(
                                    admin_bypass,
                                    Membership.permissions.contains(
                                        [Permission.VIEW_RESTRICTED_DOCUMENTS.value]),
                                    has_required_permissions()
                                ),
                            )
                        ),
                    ),
                    # Public documents: owner/admins OR members with required permissions
                    and_(
                        *base_conditions,
                        Document.visibility == Visibility.PUBLIC,
                        Document.group_id.in_(
                            select(Membership.group_id).where(
                                Membership.user_id == user.id,
                                Membership.accepted.is_(True),
                                or_(
                                    admin_bypass,
                                    has_required_permissions()
                                )
                            )
                        ),
                    ),
                )

            if multi and document_id is None:
                # For multi-document queries (filtering Document table directly)
                return build_visibility_clause()
            elif not multi:
                # For single document access checks on User queries - use EXISTS to avoid cross join
                return select(Document).where(
                    build_visibility_clause(Document.id == document_id)
                ).exists()
            else:
                return build_visibility_clause()

        def predicate(doc: Document, user: User) -> bool:

            if doc.group is None:
                return False

            # Check if user has required permissions (if any)
            def user_has_required_permissions(membership: Membership) -> bool:
                if not require_permissions:
                    return True
                return all(p in membership.permissions for p in require_permissions)

            if doc.visibility == Visibility.PRIVATE:
                # Private: owner or admin only
                return any(
                    m.user_id == user.id and (
                        m.is_owner or
                        Permission.ADMINISTRATOR in m.permissions
                    )
                    for m in doc.group.memberships
                )
            elif doc.visibility == Visibility.RESTRICTED:
                # Restricted: owner, admin, VIEW_RESTRICTED_DOCUMENTS, or required permissions
                return any(
                    m.accepted and m.user_id == user.id and (
                        m.is_owner or
                        Permission.ADMINISTRATOR in m.permissions or
                        Permission.VIEW_RESTRICTED_DOCUMENTS in m.permissions or
                        user_has_required_permissions(m)
                    )
                    for m in doc.group.memberships
                )
            elif doc.visibility == Visibility.PUBLIC:
                # Public: owner, admin, or required permissions
                return any(
                    m.accepted and m.user_id == user.id and (
                        m.is_owner or
                        Permission.ADMINISTRATOR in m.permissions or
                        user_has_required_permissions(m)
                    )
                    for m in doc.group.memberships
                )
            return False

        return EndpointGuard(clause, predicate, exclude_fields=exclude_fields)

    @staticmethod
    def group_access(
        require_permissions: set[Permission] | None = None,
        *,
        only_owner: bool = False,
        exclude_fields: list[ColumnElement] | None = None,
    ) -> EndpointGuard[Group]:
        """User can access a group if they have at least min_role in it.
        
        Args:
            require_permissions: Set of permissions required to access groups
            only_owner: If True, restrict access to group owners only
            exclude_fields: List of model fields to exclude from responses
        
        """

        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            group_id = params.get("group_id", None)
            if not group_id and not multi:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing group_id parameter")

            def build_permission_clause() -> ColumnElement[bool]:
                """Build permission check clause."""
                if only_owner:
                    return Membership.is_owner.is_(True)
                else:
                    return (
                        Membership.is_owner.is_(True) |
                        Membership.permissions.contains([Permission.ADMINISTRATOR.value]) |
                        (and_(*(Membership.permissions.contains([permission.value])
                                for permission in require_permissions)) if require_permissions else true())
                    )

            if multi and group_id is None:
                # For multi-group queries (filtering Group table directly)
                return Group.id.in_(
                    select(Membership.group_id).where(
                        Membership.user_id == user.id,
                        build_permission_clause()
                    )
                )
            elif not multi:
                # For single group access checks - use EXISTS to avoid cross join
                return select(Membership).where(
                    (Membership.user_id == user.id) &
                    (Membership.group_id == group_id) &
                    build_permission_clause()
                ).exists()
            else:
                return select(Membership).where(
                    (Membership.user_id == user.id) &
                    build_permission_clause()
                ).exists()

        def predicate(group: Group, user: User) -> bool:
            return any(
                (m.user_id == user.id) and
                (m.is_owner if only_owner else True) and
                all(p in require_permissions for p in m.permissions)
                for m in group.memberships
            )

        return EndpointGuard(clause, predicate, exclude_fields=exclude_fields)

    @staticmethod
    def comment_access( # noqa: C901
        require_permissions: set[Permission] | None = None,
        *,
        only_owner: bool = False,
        exclude_fields: list[ColumnElement] | None = None,
    ) -> EndpointGuard[Comment]:
        """User can access a comment based on its visibility, the document view_mode and the given required permissions."""

        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            """Generate the SQLAlchemy clause for comment access, taking document.view_mode into account."""
            comment_id = params.get("comment_id", None)
            if not comment_id and not multi:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing comment_id parameter"
                )

            def has_required_permissions_sql() -> ColumnElement[bool]:
                """Return a SQL clause that checks for all required permissions on Membership."""
                if not require_permissions:
                    return true()
                return and_(
                    *(
                        Membership.permissions.contains([permission.value])
                        for permission in require_permissions
                    )
                )

            def build_visibility_clause(comment_id_filter: ColumnElement[bool] | None = None) -> ColumnElement[bool]:
                """Build the combined visibility clause, also considering document.view_mode."""
                base_conditions: list[ColumnElement[bool]] = [comment_id_filter] if comment_id_filter is not None else []

                # Build the permission OR for restricted-by-view-mode checks. Only include
                # the `require_permissions` clause if `require_permissions` was provided;
                # otherwise omit it so we don't accidentally broaden access.
                restricted_permission_ors = [
                    Membership.is_owner.is_(True),
                    Membership.permissions.contains([Permission.VIEW_RESTRICTED_COMMENTS.value]),
                    Membership.permissions.contains([Permission.ADMINISTRATOR.value]),
                ]
                if require_permissions:
                    restricted_permission_ors.append(has_required_permissions_sql())

                # Clause applied when the document's view_mode forces restricted access for the whole document
                restricted_by_view_mode_clause = and_(
                    *base_conditions,
                    Comment.document.has(Document.view_mode == ViewMode.RESTRICTED),
                    or_(
                        Comment.user_id == user.id,
                        Comment.document.has(
                            Document.group_id.in_(
                                select(Membership.group_id).where(
                                    Membership.user_id == user.id,
                                    Membership.accepted.is_(True),
                                    or_(*restricted_permission_ors),
                                )
                            )
                        ),
                    ),
                )

                if only_owner:
                    # If only_owner is True, restrict to comments owned by the user
                    owner_only_clause = and_(
                        *base_conditions,
                        Comment.user_id == user.id,
                    )
                    return owner_only_clause

                # Original visibility-based clauses (applied when the document view_mode is public or unspecified)
                private_clause = and_(
                    *base_conditions,
                    Comment.visibility == Visibility.PRIVATE,
                    or_(
                        Comment.user_id == user.id,
                        Comment.document.has(
                            Document.group_id.in_(
                                select(Membership.group_id).where(
                                    Membership.user_id == user.id,
                                    or_(
                                        Membership.is_owner.is_(True),
                                        Membership.permissions.contains([Permission.ADMINISTRATOR.value]),
                                    ),
                                    # allow required permissions for private when specified
                                    has_required_permissions_sql(),
                                )
                            )
                        ),
                    ),
                )

                restricted_clause = and_(
                    *base_conditions,
                    Comment.visibility == Visibility.RESTRICTED,
                    or_(
                        Comment.user_id == user.id,
                        Comment.document.has(
                            Document.group_id.in_(
                                select(Membership.group_id).where(
                                    Membership.user_id == user.id,
                                    Membership.accepted.is_(True),
                                    # Only include the "required permissions" clause if specified
                                    or_(*restricted_permission_ors),
                                )
                            )
                        ),
                    ),
                )

                public_clause = and_(
                    *base_conditions,
                    Comment.visibility == Visibility.PUBLIC,
                    or_(
                        Comment.user_id == user.id,
                        Comment.document.has(
                            Document.group_id.in_(
                                select(Membership.group_id).where(
                                    Membership.user_id == user.id,
                                    Membership.accepted.is_(True),
                                )
                            )
                        ),
                    ),
                )

                # Combine carefully:
                # - If document.view_mode == RESTRICTED -> only allow restricted_by_view_mode_clause
                # - If document.view_mode == PUBLIC -> apply comment-level visibility clauses
                # - If document.view_mode is NULL/unspecified -> fall back to comment-level visibility clauses
                return or_(
                    restricted_by_view_mode_clause,
                    and_(
                        Comment.document.has(Document.view_mode == ViewMode.PUBLIC),
                        or_(private_clause, restricted_clause, public_clause),
                    ),
                    and_(
                        Comment.document.has(Document.view_mode.is_(None)),
                        or_(private_clause, restricted_clause, public_clause),
                    ),
                )

            if multi and comment_id is None:
                # For multi-comment queries (filtering Comment table directly)
                return build_visibility_clause()
            elif not multi:
                # For single comment access checks - use EXISTS to avoid cross join
                return select(Comment).where(
                    build_visibility_clause(Comment.id == comment_id)
                ).exists()
            else:
                return build_visibility_clause()

        def predicate(comment: Comment, user: User) -> bool: # noqa: C901
            """Run Python-side predicate for comment access, taking document.view_mode into account."""
            if only_owner:
                return comment.user_id == user.id

            document = comment.document
            if document is None:
                return False

            def membership_satisfies_required_permissions(membership: Membership) -> bool:
                """Check required permissions on a Python Membership object."""
                if not require_permissions:
                    return True
                return all(p in membership.permissions for p in require_permissions)

            # If the document forces restricted view mode, treat all comments as restricted
            if getattr(document, "view_mode", None) == ViewMode.RESTRICTED:
                if comment.user_id == user.id:
                    return True
                if document.group is None:
                    return False
                return any(
                    m.accepted and m.user_id == user.id and (
                        m.is_owner or
                        Permission.VIEW_RESTRICTED_COMMENTS in m.permissions or
                        Permission.ADMINISTRATOR in m.permissions or
                        membership_satisfies_required_permissions(m)
                    )
                    for m in document.group.memberships
                )

            # Otherwise, apply comment-level visibility rules
            if comment.visibility == Visibility.PRIVATE:
                return comment.user_id == user.id or (
                    document.group is not None and any(
                        m.user_id == user.id and (
                            m.is_owner or
                            Permission.ADMINISTRATOR in m.permissions or
                            membership_satisfies_required_permissions(m)
                        )
                        for m in document.group.memberships
                    )
                )
            elif comment.visibility == Visibility.RESTRICTED:
                if comment.user_id == user.id:
                    return True
                if document.group is None:
                    return False
                return any(
                    m.accepted and m.user_id == user.id and (
                        m.is_owner or
                        Permission.VIEW_RESTRICTED_COMMENTS in m.permissions or
                        Permission.ADMINISTRATOR in m.permissions or
                        membership_satisfies_required_permissions(m)
                    )
                    for m in document.group.memberships
                )
            elif comment.visibility == Visibility.PUBLIC:
                if comment.user_id == user.id:
                    return True
                if document.group is None:
                    return False
                return any(
                    m.accepted and m.user_id == user.id and (
                        m.is_owner or
                        Permission.ADMINISTRATOR in m.permissions or
                        membership_satisfies_required_permissions(m)
                    )
                    for m in document.group.memberships
                )
            return False

        return EndpointGuard(clause, predicate, exclude_fields=exclude_fields)

    @staticmethod
    def reaction_access(
        *,
        only_owner: bool = False,
        exclude_fields: list[ColumnElement] | None = None,
    ) -> EndpointGuard[Reaction]:
        """User can access a reaction if they can access the parent comment.
        
        Args:
            only_owner: If True, restrict access to reaction owners only
            exclude_fields: List of model fields to exclude from responses
        
        """
        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            reaction_id = params.get("reaction_id", None)
            if not reaction_id and not multi:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing reaction_id parameter")

            def build_clause(reaction_id_filter: ColumnElement[bool] | None = None) -> ColumnElement[bool]:
                """Build the clause for reaction access."""
                base_conditions = [
                    reaction_id_filter] if reaction_id_filter is not None else []
                return and_(
                    *base_conditions,
                    Reaction.comment_id.in_(
                        select(Comment.id).where(
                            Guard.comment_access(None, only_owner=only_owner).clause(
                                user, params, params, multi=True
                            )
                        ))
                )

            if multi and reaction_id is None:
                # For multi-reaction queries (filtering Reaction table directly)
                return build_clause()
            elif not multi:
                # For single reaction access checks - use EXISTS to avoid cross join
                return select(Reaction).where(
                    build_clause(Reaction.id == reaction_id)
                ).exists()
            else:
                return build_clause()

        def predicate(reaction: Reaction, user: User) -> bool:
            return Guard.comment_access(None, only_owner=only_owner).predicate(reaction.comment, user)
        
        return EndpointGuard(clause, predicate, exclude_fields=exclude_fields)

    @staticmethod
    def combine[T](*, op: Literal["and", "or"] = "and", guards: list[EndpointGuard[T]]) -> EndpointGuard[T]:
        """Combine multiple guards with AND or OR logic."""
        if op not in ("and", "or"):
            raise ValueError("op must be 'and' or 'or'")

        def clause(session_user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            clauses = [guard.clause(session_user, params, multi=multi)
                       for guard in guards]
            if op == "and":
                combined = clauses[0]
                for c in clauses[1:]:
                    combined = combined & c
                return combined
            else:
                combined = clauses[0]
                for c in clauses[1:]:
                    combined = combined | c
                return combined

        def predicate(obj: T | Paginated[T] | list[T], session_user: User) -> bool:
            results = [guard.predicate(obj, session_user) for guard in guards]
            if op == "and":
                return all(results)
            else:
                return any(results)

        return EndpointGuard(clause, predicate)
