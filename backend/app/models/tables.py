from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID, uuid4

from nanoid import generate
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property, declared_attr
from sqlmodel import Field, Relationship, func, select

from models.base import BaseModel
from models.enums import Permission, ReactionType, ViewMode, Visibility

# TABLES


class User(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    first_name: str | None = Field(nullable=True, default=None)
    last_name: str | None = Field(nullable=True, default=None)
    password: str  # hashed
    email: str = Field(index=True, unique=True)
    verified: bool = Field(default=False)
    # For personally signed URLs, JWT encryption etc.
    secret: str = Field(
        default_factory=func.gen_random_uuid,
        sa_column=Column(String, server_default=func.gen_random_uuid())
    )

    memberships: list["Membership"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "noload"})
    comments: list["Comment"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "noload"})
    groups: list["Group"] = Relationship(
        back_populates=None,
        sa_relationship_kwargs={
            "secondary": "membership",
            "primaryjoin": "User.id == Membership.user_id",
            "secondaryjoin": "Membership.group_id == Group.id",
            "viewonly": True,
            "lazy": "noload"
        }
    )
    reactions: list["Reaction"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "noload"}
    )
    share_links: list["ShareLink"] = Relationship(
        back_populates="author",
        sa_relationship_kwargs={"lazy": "noload"}
    )

    def rotate_secret(self) -> None:
        """Rotate the user secret to invalidate existing tokens."""
        self.secret = str(uuid4())


class Membership(BaseModel, table=True):
    """Association table for user-group relationships with permissions."""

    user_id: int = Field(foreign_key="user.id",
                         ondelete="CASCADE", primary_key=True)
    group_id: str = Field(foreign_key="group.id",
                          ondelete="CASCADE", primary_key=True)
    permissions: list[Permission] = Field(
        default_factory=list, sa_column=Column(ARRAY(String)))
    is_owner: bool = Field(default=False)
    accepted: bool = Field(default=False)
    user: User = Relationship(back_populates="memberships")
    group: "Group" = Relationship(back_populates="memberships")


class Group(BaseModel, table=True):
    """Group entity for shared document management."""

    id: str = Field(default_factory=lambda: generate(
        size=10), primary_key=True, index=True)
    name: str = Field(index=True, unique=True)
    # For group signed URLs, JWT encryption etc.
    secret: str = Field(default_factory=func.gen_random_uuid)
    default_permissions: list[Permission] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String))
    )
    member_count: ClassVar[int]

    @declared_attr
    def member_count(self) -> int:
        """Count of members in the group."""
        return column_property(
            select(func.count(Membership.user_id))
            .where(Membership.group_id == self.id)
            .correlate_except(Membership)
            .scalar_subquery()
        )

    owner: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "secondary": "membership",
            "primaryjoin": "Group.id == Membership.group_id",
            "secondaryjoin": "and_(Membership.user_id == User.id, Membership.is_owner == True)",
            "uselist": False,
            "viewonly": True,
        }
    )

    documents: list["Document"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True})
    memberships: list["Membership"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True})
    share_links: list["ShareLink"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True})

    def rotate_secret(self) -> None:
        """Rotate the group secret to invalidate existing tokens."""
        self.secret = str(uuid4())


class Document(BaseModel, table=True):
    """Document entity representing uploaded files."""

    id: str = Field(default_factory=lambda: generate(
        size=10), primary_key=True, index=True)
    name: str = Field()
    s3_key: str = Field(index=True, unique=True)
    size_bytes: int = Field(default=0)
    visibility: Visibility = Field(default=Visibility.PRIVATE, sa_column=Column(
        String, server_default=Visibility.PRIVATE.value))
    view_mode: ViewMode = Field(
        default=ViewMode.PUBLIC,
        sa_column=Column(String, server_default=ViewMode.PUBLIC.value)
    )
    secret: UUID = Field(default_factory=func.gen_random_uuid,
                         sa_column=Column(PGUUID(as_uuid=True)))

    group_id: str = Field(
        foreign_key="group.id", nullable=True, ondelete="CASCADE")

    group: Group = Relationship(back_populates="documents")

    comments: list["Comment"] = Relationship(
        back_populates="document", sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True})


class Comment(BaseModel, table=True):
    """Comment entity for annotations and discussions."""

    id: int = Field(default=None, primary_key=True)
    visibility: Visibility = Field()
    document_id: str = Field(foreign_key="document.id", ondelete="CASCADE")
    user_id: int = Field(
        foreign_key="user.id")
    parent_id: int | None = Field(
        foreign_key="comment.id", nullable=True, default=None, ondelete="CASCADE")
    content: str | None = Field(nullable=True, default=None)
    annotation: dict = Field(default_factory=dict, sa_column=Column(JSONB))

    document: Document = Relationship(back_populates="comments")
    user: User | None = Relationship(back_populates="comments")
    parent: Optional["Comment"] = Relationship(
        back_populates="replies",
        sa_relationship_kwargs={
            "remote_side": "Comment.id",
            "lazy": "noload"
        }
    )
    replies: list["Comment"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True}
    )
    reactions: list["Reaction"] = Relationship(
        back_populates="comment",
        sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True}
    )

    num_replies: ClassVar[int]

    @hybrid_property
    def num_replies(self) -> int:
        """Return the number of replies to this comment (Python-side)."""
        # Use the relationship to provide a Python-side count when replies
        # are loaded; this avoids referencing the mapped class during mapping.
        return len(self.replies or [])

    @num_replies.expression
    def num_replies(cls) -> select:
        """Return SQL expression returning number of replies to this comment."""
        # Now that the class is mapped, reference Comment to build a
        # DB-level expression used in queries.
        return (
            select(func.count(Comment.id))
            .where(Comment.parent_id == cls.id)
            .correlate_except(Comment)
            .scalar_subquery()
        )

class Reaction(BaseModel, table=True):
    """Reaction entity for user reactions to comments."""

    user_id: int = Field(foreign_key="user.id",
                         ondelete="CASCADE", primary_key=True)
    comment_id: int = Field(foreign_key="comment.id",
                            ondelete="CASCADE", primary_key=True)
    type: ReactionType = Field(sa_column=Column(String))

    user: "User" = Relationship(back_populates="reactions")
    comment: "Comment" = Relationship(back_populates="reactions")


class ShareLink(BaseModel, table=True):
    """A link granting access to a group with specified permissions."""

    id: int = Field(default=None, primary_key=True)
    group_id: str = Field(foreign_key="group.id", ondelete="CASCADE")
    author_id: int | None = Field(
        foreign_key="user.id", ondelete="SET NULL", nullable=True)
    permissions: list[Permission] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String))
    )
    allow_anonymous_access: bool = Field(default=False, sa_column=Column(Boolean, server_default="false"))

    token: str = Field(
        default_factory=func.gen_random_uuid,
        sa_column=Column(String, unique=True, index=True)
    )

    expires_at: datetime | None = Field(default=None, nullable=True)
    # e.g. "Link for review team"
    label: str | None = Field(default=None, nullable=True)

    group: "Group" = Relationship(back_populates="share_links")
    author: Optional["User"] = Relationship(back_populates="share_links")

    def rotate_token(self) -> None:
        """Invalidate this share link by rotating its token."""
        self.token = str(uuid4())[:8]
