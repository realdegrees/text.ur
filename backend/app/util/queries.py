from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import HTTPException
from fastapi.datastructures import QueryParams
from models.enums import DocumentVisibility, Permission, ViewMode, Visibility
from models.pagination import Paginated
from models.tables import (
    Comment,
    Document,
    Group,
    Membership,
    Reaction,
    ShareLink,
    User,
)
from sqlalchemy import and_, false, or_, select, true
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
            # Convert user_id to int if it's a string (from path params)
            if target_user_id is not None and isinstance(target_user_id, str):
                try:
                    target_user_id = int(target_user_id)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=400, detail="Invalid user_id: must be an integer"
                    ) from None

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

        def predicate(membership: Membership, user: User) -> bool:
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
            # Convert user_id to int if it's a string (from path params)
            if isinstance(target_user_id, str):
                try:
                    target_user_id = int(target_user_id)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=400, detail="Invalid user_id: must be an integer"
                    ) from None
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
        """User can access a document based on its visibility and required permissions.

        - PRIVATE: only the group owner and administrators.
        - PUBLIC: any accepted group member (with optional extra permissions).

        Args:
            require_permissions: Set of permissions required to access documents
            exclude_fields: List of model fields to exclude from responses

        """

        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            document_id = params.get("document_id", None)
            if not document_id and not multi:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing document_id parameter")

            def has_required_permissions_for_public() -> ColumnElement[bool]:
                """Verify membership has required permissions for public docs."""
                if not require_permissions:
                    return true()
                return and_(*(Membership.permissions.contains([p.value]) for p in require_permissions))

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
                        Document.visibility == DocumentVisibility.PRIVATE,
                        Document.group_id.in_(
                            select(Membership.group_id).where(
                                Membership.user_id == user.id,
                                admin_bypass,
                            ))
                    ),
                    # Public documents: owner/admins OR accepted members with required permissions
                    and_(
                        *base_conditions,
                        Document.visibility == DocumentVisibility.PUBLIC,
                        Document.group_id.in_(
                            select(Membership.group_id).where(
                                Membership.user_id == user.id,
                                Membership.accepted.is_(True),
                                or_(
                                    admin_bypass,
                                    has_required_permissions_for_public(),
                                )
                            )
                        ),
                    ),
                )

            if multi and document_id is None:
                return build_visibility_clause()
            elif not multi:
                return select(Document).where(
                    build_visibility_clause(Document.id == document_id)
                ).exists()
            else:
                return build_visibility_clause()

        def predicate(doc: Document, user: User) -> bool:
            if doc.group is None:
                return False

            if doc.visibility == DocumentVisibility.PRIVATE:
                return any(
                    m.user_id == user.id and (
                        m.is_owner or
                        Permission.ADMINISTRATOR.value in m.permissions
                    )
                    for m in doc.group.memberships
                )
            elif doc.visibility == DocumentVisibility.PUBLIC:
                if not require_permissions:
                    return any(
                        m.accepted and m.user_id == user.id
                        for m in doc.group.memberships
                    )
                return any(
                    m.accepted and m.user_id == user.id and (
                        m.is_owner or
                        Permission.ADMINISTRATOR.value in m.permissions or
                        all(p.value in m.permissions for p in require_permissions)
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
            required_vals: list[str] = [] if require_permissions is None else [p.value for p in require_permissions]

            return any(
                (m.user_id == user.id)
                and (m.is_owner if only_owner else True)
                and all(p in m.permissions for p in required_vals)
                for m in group.memberships
            )

        return EndpointGuard(clause, predicate, exclude_fields=exclude_fields)

    @staticmethod
    def sharelink_access( # noqa: C901
        *,
        exclude_fields: list[ColumnElement] | None = None,
    ) -> EndpointGuard[ShareLink]:
        """User can access a share link if they have access to its group. Can be used on routes with token or id param optionally filtered by group_id param.

        Args:
            require_permissions: Set of permissions required to access share links
            exclude_fields: List of model fields to exclude from responses
            
        """

        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            share_link_id = params.get("share_link_id", None)
            token = params.get("token", None)
            group_id = params.get("group_id", None)
            
            if (not share_link_id or not token) and not multi:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing share_link_id parameter")
            # Convert share_link_id to int if it's a string (from path params)
            if share_link_id is not None and isinstance(share_link_id, str):
                try:
                    share_link_id = int(share_link_id)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=400, detail="Invalid share_link_id: must be an integer"
                    ) from None

            def build_permission_clause() -> ColumnElement[bool]:
                """Build permission check clause."""
                return (
                    Membership.is_owner.is_(True) |
                    Membership.permissions.contains([Permission.ADMINISTRATOR.value])
                )

            if multi:
                # For multi-sharelink queries (filtering ShareLink table directly)
                return ShareLink.group_id.in_(
                    select(Membership.group_id).where(
                        Membership.user_id == user.id,
                        Membership.accepted.is_(True),
                        Membership.group_id == group_id if group_id is not None else true(),
                        build_permission_clause()
                    )
                )
            elif share_link_id is not None:
                # For single share link access checks - use EXISTS to avoid cross join
                return select(ShareLink).where(
                    (ShareLink.id == share_link_id) &
                    ShareLink.group_id.in_(
                        select(Membership.group_id).where(
                            Membership.user_id == user.id,
                            Membership.accepted.is_(True),
                            Membership.group_id == group_id if group_id is not None else true(),
                            build_permission_clause()
                        )
                    )
                ).exists()
            elif token is not None:
                return select(ShareLink).where(
                    (ShareLink.token == token) &
                    ShareLink.group_id.in_(
                        select(Membership.group_id).where(
                            Membership.user_id == user.id,
                            Membership.accepted.is_(True),
                            Membership.group_id == group_id if group_id is not None else true(),
                            build_permission_clause()
                        )
                    )
                ).exists()
            else:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: invalid configuration for multi parameter")

        def predicate(share_link: ShareLink, user: User) -> bool:
            if share_link.group is None:
                return False

            return any(
                (m.user_id == user.id)
                and m.accepted
                and (m.is_owner or Permission.ADMINISTRATOR.value in m.permissions)
                for m in share_link.group.memberships
            )

        return EndpointGuard(clause, predicate, exclude_fields=exclude_fields)


    # Access Rules Truth Table
    #
    # Legend:
    # user_has_perm: Does the user have "view_restricted_comments"?
    # document_view_mode: Document view mode ("public" or "restricted")
    # comment_visibility: Comment visibility ("public", "restricted", "private")
    # is_author: Is the user the author of the comment?
    # allowed: Does the user get access to the comment?
    #
    # Rules summary (admin and owner bypass all besides private rule):
    # - Private comments are only visible to the author.
    # - Private comments are always visible to the author regardless of document view_mode.
    # - Restricted comments are only visible to users with "view_restricted_comments" permission
    # - Public comments are always visible unless document view_mode is "restricted".
    # - Comment authors always see their own comments.
    #
    # -------------------------------------------------------------------------------
    # | user_has_perm | document_view_mode  | comment_visibility  | is_author | passes |
    # -------------------------------------------------------------------------------
    # | False         | public              | public              | False     | True   |
    # | False         | public              | public              | True      | True   |
    # | False         | public              | restricted          | False     | False  |
    # | False         | public              | restricted          | True      | True   |
    # | False         | public              | private             | False     | False  |
    # | False         | public              | private             | True      | True   |
    # -------------------------------------------------------------------------------
    # | False         | restricted          | public              | False     | False  |
    # | False         | restricted          | public              | True      | True   |
    # | False         | restricted          | restricted          | False     | False  |
    # | False         | restricted          | restricted          | True      | True   |
    # | False         | restricted          | private             | False     | False  |
    # | False         | restricted          | private             | True      | True   |
    # -------------------------------------------------------------------------------
    # | True          | public              | public              | False     | True   |
    # | True          | public              | public              | True      | True   |
    # | True          | public              | restricted          | False     | True   |
    # | True          | public              | restricted          | True      | True   |
    # | True          | public              | private             | False     | False  |
    # | True          | public              | private             | True      | True   |
    # -------------------------------------------------------------------------------
    # | True          | restricted          | public              | False     | True   |
    # | True          | restricted          | public              | True      | True   |
    # | True          | restricted          | restricted          | False     | True   |
    # | True          | restricted          | restricted          | True      | True   |
    # | True          | restricted          | private             | False     | False  |
    # | True          | restricted          | private             | True      | True   |
    # -------------------------------------------------------------------------------

    @staticmethod
    def comment_access( # noqa: C901
        require_permissions: set[Permission] | None = None,
        *,
        only_owner: bool = False,
        exclude_fields: list[ColumnElement] | None = None,
    ) -> EndpointGuard[Comment]:
        """User can access a comment based on its visibility, the document view_mode and the given required permissions."""

        def clause(user: User, params: dict[str, Any], multi: bool = False) -> ColumnElement[bool]:
            """Generate the SQLAlchemy clause for comment access, following the truth table exactly."""
            comment_id = params.get("comment_id", None)
            if not comment_id and not multi:
                raise HTTPException(
                    status_code=500, detail="Endpoint Guard misconfiguration: missing comment_id parameter"
                )
            # Convert comment_id to int if it's a string (from path params)
            if comment_id is not None and isinstance(comment_id, str):
                try:
                    comment_id = int(comment_id)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=400, detail="Invalid comment_id: must be an integer"
                    ) from None

            def build_visibility_clause(comment_id_filter: ColumnElement[bool] | None = None) -> ColumnElement[bool]:
                """Build the visibility clause following the truth table exactly."""
                base_conditions: list[ColumnElement[bool]] = [comment_id_filter] if comment_id_filter is not None else []

                if only_owner:
                    # If only_owner is True, restrict to comments owned by the user
                    return and_(*base_conditions, Comment.user_id == user.id)

                # Helper: users with VIEW_RESTRICTED_COMMENTS permission (or admin/owner)
                has_view_restricted_perm = or_(
                    Membership.is_owner.is_(True),
                    Membership.permissions.contains([Permission.VIEW_RESTRICTED_COMMENTS.value]),
                    Membership.permissions.contains([Permission.ADMINISTRATOR.value]),
                )

                # Rule 1: Private comments are only visible to the author (always)
                private_comment_clause = and_(
                    *base_conditions,
                    Comment.visibility == Visibility.PRIVATE,
                    Comment.user_id == user.id,
                )

                # Rule 2: Restricted comments are only visible to users with VIEW_RESTRICTED_COMMENTS (or author)
                restricted_comment_clause = and_(
                    *base_conditions,
                    Comment.visibility == Visibility.RESTRICTED,
                    or_(
                        Comment.user_id == user.id,
                        Comment.document.has(
                            Document.group_id.in_(
                                select(Membership.group_id).where(
                                    Membership.user_id == user.id,
                                    Membership.accepted.is_(True),
                                    has_view_restricted_perm,
                                )
                            )
                        ),
                    ),
                )

                # Helper for public comments: member check with optional required permissions
                def public_comment_member_check() -> ColumnElement[bool]:
                    if not require_permissions:
                        # No additional permissions required, any accepted member can access
                        return or_(
                            Comment.user_id == user.id,
                            Comment.document.has(
                                Document.group_id.in_(
                                    select(Membership.group_id).where(
                                        Membership.user_id == user.id,
                                        Membership.accepted.is_(True),
                                    )
                                )
                            ),
                        )
                    else:
                        # Additional permissions required (owner/admin bypass)
                        return or_(
                            Comment.user_id == user.id,
                            Comment.document.has(
                                Document.group_id.in_(
                                    select(Membership.group_id).where(
                                        Membership.user_id == user.id,
                                        Membership.accepted.is_(True),
                                        or_(
                                            Membership.is_owner.is_(True),
                                            Membership.permissions.contains([Permission.ADMINISTRATOR.value]),
                                            and_(*(Membership.permissions.contains([p.value]) for p in require_permissions)),
                                        ),
                                    )
                                )
                            ),
                        )

                # Rule 3: Public comments when document view_mode is PUBLIC
                # - Visible to all accepted members (or author)
                public_comment_public_doc_clause = and_(
                    *base_conditions,
                    Comment.visibility == Visibility.PUBLIC,
                    Comment.document.has(Document.view_mode == ViewMode.PUBLIC),
                    public_comment_member_check(),
                )

                # Rule 4: Public comments when document view_mode is RESTRICTED
                # - Only visible to users with VIEW_RESTRICTED_COMMENTS (or author)
                public_comment_restricted_doc_clause = and_(
                    *base_conditions,
                    Comment.visibility == Visibility.PUBLIC,
                    Comment.document.has(Document.view_mode == ViewMode.RESTRICTED),
                    or_(
                        Comment.user_id == user.id,
                        Comment.document.has(
                            Document.group_id.in_(
                                select(Membership.group_id).where(
                                    Membership.user_id == user.id,
                                    Membership.accepted.is_(True),
                                    has_view_restricted_perm,
                                )
                            )
                        ),
                    ),
                )

                # Rule 5: Handle NULL view_mode as PUBLIC
                public_comment_null_doc_clause = and_(
                    *base_conditions,
                    Comment.visibility == Visibility.PUBLIC,
                    Comment.document.has(Document.view_mode.is_(None)),
                    public_comment_member_check(),
                )

                return or_(
                    private_comment_clause,
                    restricted_comment_clause,
                    public_comment_public_doc_clause,
                    public_comment_restricted_doc_clause,
                    public_comment_null_doc_clause,
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
            """Run Python-side predicate for comment access, following the truth table exactly."""
            if only_owner:
                return comment.user_id == user.id

            document = comment.document
            if document is None:
                return False

            # Helper: check if user has VIEW_RESTRICTED_COMMENTS permission (or admin/owner)
            def user_has_view_restricted_perm() -> bool:
                if document.group is None:
                    return False
                return any(
                    m.accepted and m.user_id == user.id and (
                        m.is_owner or
                        Permission.VIEW_RESTRICTED_COMMENTS in m.permissions or
                        Permission.ADMINISTRATOR in m.permissions
                    )
                    for m in document.group.memberships
                )

            # Helper: check if user satisfies requirements for public comments
            def user_satisfies_public_comment_requirements() -> bool:
                if document.group is None:
                    return False
                # If no required permissions, any accepted member can access
                if not require_permissions:
                    return any(
                        m.accepted and m.user_id == user.id
                        for m in document.group.memberships
                    )
                # If required permissions provided, need to be owner/admin OR have those permissions
                return any(
                    m.accepted and m.user_id == user.id and (
                        m.is_owner or
                        Permission.ADMINISTRATOR in m.permissions or
                        all(p in m.permissions for p in require_permissions)
                    )
                    for m in document.group.memberships
                )

            # Rule 1: Authors always see their own comments
            if comment.user_id == user.id:
                return True

            # Rule 2: Private comments are only visible to the author
            if comment.visibility == Visibility.PRIVATE:
                return False

            # Rule 3: Restricted comments are only visible to users with VIEW_RESTRICTED_COMMENTS
            if comment.visibility == Visibility.RESTRICTED:
                return user_has_view_restricted_perm()

            # Rule 4: Public comments
            if comment.visibility == Visibility.PUBLIC:
                document_view_mode = getattr(document, "view_mode", None)
                if document_view_mode == ViewMode.RESTRICTED:
                    # Public comments in restricted documents need VIEW_RESTRICTED_COMMENTS
                    return user_has_view_restricted_perm()
                else:
                    # Public comments in public documents are visible to accepted members (with required permissions if any)
                    return user_satisfies_public_comment_requirements()

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
            # Convert reaction_id to int if it's a string (from path params)
            if reaction_id is not None and isinstance(reaction_id, str):
                try:
                    reaction_id = int(reaction_id)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=400, detail="Invalid reaction_id: must be an integer"
                    ) from None

            def build_clause(reaction_id_filter: ColumnElement[bool] | None = None) -> ColumnElement[bool]:
                """Build the clause for reaction access."""
                base_conditions = [
                    reaction_id_filter] if reaction_id_filter is not None else []
                return and_(
                    *base_conditions,
                    Reaction.comment_id.in_(
                        select(Comment.id).where(
                            Guard.comment_access(None, only_owner=only_owner).clause(
                                user, params, multi=True
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
