from datetime import UTC, datetime
from typing import ClassVar, Optional
from uuid import UUID, uuid4

from nanoid import generate
from sqlalchemy import Boolean, Column, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import aliased, column_property, declared_attr
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Field, Relationship, func, select

from models.base import BaseModel
from models.enums import Emoji, Permission, ViewMode, Visibility

# TABLES


class User(BaseModel, table=True):
    id: int = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    first_name: str | None = Field(nullable=True, default=None)
    last_name: str | None = Field(nullable=True, default=None)
    password: str | None = Field(nullable=True, default=None)  # hashed
    email: str | None = Field(
        nullable=True, default=None, index=True, unique=True)
    verified: bool = Field(default=False)
    # TODO this can probably just be removed and inferred from presence of password/email, can also be dropped from existing db entries
    is_guest: bool = Field(default=False, sa_column=Column(
        Boolean, server_default="false"))
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
    sharelink_id: int | None = Field(
        foreign_key="sharelink.id", nullable=True, default=None, ondelete="SET NULL")
    accepted: bool = Field(default=False)
    user: User = Relationship(back_populates="memberships", sa_relationship_kwargs={"lazy": "selectin"})
    group: "Group" = Relationship(back_populates="memberships", sa_relationship_kwargs={"lazy": "selectin"})
    share_link: Optional["ShareLink"] = Relationship(
        back_populates="memberships", sa_relationship_kwargs={"lazy": "selectin"})

    is_expired: ClassVar[bool]

    @hybrid_property
    def is_expired(self) -> bool:
        """Return whether the share link associated with this membership is expired (Python-side)."""
        if self.share_link is None:
            return False  # If no share link, the membership is not expired
        return self.share_link.is_expired

    @is_expired.expression
    def is_expired(cls) -> select:
        """Return SQL expression returning whether the share link associated with this membership is expired."""
        return func.coalesce(
            select(ShareLink.is_expired)
            .where(ShareLink.id == cls.sharelink_id)
            .correlate_except(ShareLink)
            .scalar_subquery(),
            False  # Default to False if ShareLink.is_expired is NULL
        )


class Document(BaseModel, table=True):
    """Document entity representing uploaded files."""

    id: str = Field(default_factory=lambda: generate(
        size=10), primary_key=True, index=True)
    name: str = Field()
    description: str | None = Field(nullable=True, default=None)
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

    group: "Group" = Relationship(back_populates="documents", sa_relationship_kwargs={"lazy": "selectin"})

    comments: list["Comment"] = Relationship(
        back_populates="document", sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True})
    tags: list["Tag"] = Relationship(
        back_populates="document", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True})


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
        
    document_count: ClassVar[int]
    
    @declared_attr
    def document_count(self) -> int:
        """Count of documents in the group."""
        return column_property(
            select(func.count(Document.id))
            .where(Document.group_id == self.id)
            .correlate_except(Document)
            .scalar_subquery()
        )

    _owners: list["User"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",
            "secondary": "membership",
            "primaryjoin": "Group.id == Membership.group_id",
            "secondaryjoin": "and_(Membership.user_id == User.id, Membership.is_owner == True)",
            "uselist": True,
            "viewonly": True,
            "order_by": "Membership.created_at",
        }
    )
    
    @property
    def owner(self) -> Optional["User"]:
        """Return the first owner of the group (by creation date)."""
        return self._owners[0] if self._owners else None

    documents: list["Document"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True})
    memberships: list["Membership"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True})
    share_links: list["ShareLink"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True})

    def rotate_secret(self) -> None:
        """Rotate the group secret to invalidate existing tokens."""
        self.secret = str(uuid4())



class ScoreConfig(BaseModel, table=True):
    """Per-group scoring configuration for highlights, comments, and tags."""

    group_id: str = Field(
        foreign_key="group.id",
        ondelete="CASCADE",
        primary_key=True,
    )
    highlight_points: int = Field(default=1)
    comment_points: int = Field(default=5)
    tag_points: int = Field(default=2)

    group: "Group" = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )


class GroupReaction(BaseModel, table=True):
    """A reaction emoji available within a group, with scoring rules."""

    __table_args__ = (
        UniqueConstraint("group_id", "emoji", name="uq_groupreaction_group_emoji"),
    )

    id: int = Field(default=None, primary_key=True)
    group_id: str = Field(foreign_key="group.id", ondelete="CASCADE")
    emoji: Emoji = Field(sa_column=Column(String, nullable=False))
    points: int = Field(default=2)
    admin_points: int = Field(default=4)
    giver_points: int = Field(default=2)
    order: int = Field(default=0)

    group: "Group" = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    reactions: list["Reaction"] = Relationship(
        back_populates="group_reaction",
        sa_relationship_kwargs={
            "lazy": "noload",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )


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

    document: Document = Relationship(back_populates="comments", sa_relationship_kwargs={"lazy": "selectin"})
    user: User | None = Relationship(back_populates="comments", sa_relationship_kwargs={"lazy": "selectin"})
    parent: Optional["Comment"] = Relationship(
        back_populates="replies",
        sa_relationship_kwargs={
            "remote_side": "Comment.id",
            "lazy": "selectin"
        }
    )
    replies: list["Comment"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True}
    )
    reactions: list["Reaction"] = Relationship(
        back_populates="comment",
        sa_relationship_kwargs={
            "lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True}
    )
    comment_tags: list["CommentTag"] = Relationship(
        back_populates="comment",
        sa_relationship_kwargs={
            "lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True}
    )
    tags: list["Tag"] = Relationship(
        back_populates=None,
        sa_relationship_kwargs={
            "secondary": "commenttag",
            "viewonly": True,
            "lazy": "selectin",
            "order_by": "CommentTag.order"
        }
    )

    num_replies: ClassVar[int]





class Reaction(BaseModel, table=True):
    """Reaction entity for user reactions to comments."""

    user_id: int = Field(foreign_key="user.id",
                         ondelete="CASCADE", primary_key=True)
    comment_id: int = Field(foreign_key="comment.id",
                            ondelete="CASCADE", primary_key=True)
    group_reaction_id: int = Field(
        foreign_key="groupreaction.id", ondelete="CASCADE"
    )

    user: "User" = Relationship(back_populates="reactions", sa_relationship_kwargs={"lazy": "selectin"})
    comment: "Comment" = Relationship(back_populates="reactions", sa_relationship_kwargs={"lazy": "selectin"})
    group_reaction: "GroupReaction" = Relationship(back_populates="reactions", sa_relationship_kwargs={"lazy": "selectin"})


class Tag(BaseModel, table=True):
    """Tag entity for categorizing comments within a document."""

    id: int = Field(default=None, primary_key=True)
    document_id: str = Field(foreign_key="document.id", ondelete="CASCADE")
    label: str = Field(max_length=50)
    description: str | None = Field(nullable=True, default=None, max_length=200)
    color: str = Field(max_length=7)  # Hex color format: #RRGGBB

    document: "Document" = Relationship(back_populates="tags", sa_relationship_kwargs={"lazy": "selectin"})
    comment_tags: list["CommentTag"] = Relationship(
        back_populates="tag",
        sa_relationship_kwargs={
            "lazy": "noload", "cascade": "all, delete-orphan", "passive_deletes": True}
    )
    comments: list["Comment"] = Relationship(
        back_populates=None,
        sa_relationship_kwargs={
            "secondary": "commenttag",
            "viewonly": True,
            "lazy": "noload"
        }
    )


class CommentTag(BaseModel, table=True):
    """Association table for comment-tag relationships."""

    comment_id: int = Field(foreign_key="comment.id",
                            ondelete="CASCADE", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id",
                        ondelete="CASCADE", primary_key=True)
    order: int = Field(default=0)

    comment: "Comment" = Relationship(back_populates="comment_tags")
    tag: "Tag" = Relationship(back_populates="comment_tags")


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
    allow_anonymous_access: bool = Field(
        default=False, sa_column=Column(Boolean, server_default="false"))

    token: str = Field(
        default_factory=lambda: str(uuid4())[:8],
        sa_column=Column(String, unique=True, index=True)
    )

    expires_at: datetime | None = Field(
        default=None,
        nullable=True,
        sa_type=DateTime(timezone=True),
    )
    # e.g. "Link for review team"
    label: str | None = Field(default=None, nullable=True)

    group: "Group" = Relationship(back_populates="share_links", sa_relationship_kwargs={"lazy": "selectin"})
    author: Optional["User"] = Relationship(back_populates="share_links", sa_relationship_kwargs={"lazy": "selectin"})

    is_expired: ClassVar[bool]

    @hybrid_property
    def is_expired(self) -> bool:
        """Return whether the share link is currently valid (Python-side)."""
        if self.expires_at is None:
            return False  # If no expiry date, the link is not expired
        return datetime.now(UTC) > self.expires_at

    @is_expired.expression
    def is_expired(cls) -> ColumnElement[bool]:
        """Return SQL expression returning whether the share link is valid."""
        return func.coalesce(func.now() > cls.expires_at, False)  # Default to False if expires_at is NULL

    # ! WARNING this cascade delete will not handle sharelink expiry,
    # ! WARNING additional checks need to be made in an group guard to validate if the user link is expired
    # ! WARNING but this check is also required to not leave orphaned memberships
    memberships: list["Membership"] = Relationship(
        back_populates="share_link",
        sa_relationship_kwargs={
            "lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True}
    )

    num_memberships: ClassVar[int]

    @hybrid_property
    def num_memberships(self) -> int:
        """Return the number of memberships created via this share link (Python-side)."""
        # Use the relationship to provide a Python-side count when memberships
        # are loaded; this avoids referencing the mapped class during mapping.
        return len(self.memberships or [])

    @num_memberships.expression
    def num_memberships(cls) -> select:
        """Return SQL expression returning number of memberships created via this share link."""
        # Now that the class is mapped, reference Membership to build a
        # DB-level expression used in queries.
        return (
            select(func.count(Membership.user_id))
            .where(Membership.sharelink_id == cls.id)
            .correlate_except(Membership)
            .scalar_subquery()
        )

    def rotate_token(self) -> None:
        """Invalidate this share link by rotating its token."""
        self.token = str(uuid4())[:8]


# Define num_replies column property after class creation to allow aliasing
# We need to use an alias for the inner query to distinguish it from the outer row
_CommentAlias = aliased(Comment)
Comment.num_replies = column_property(
    select(func.count(_CommentAlias.id))
    .where(_CommentAlias.parent_id == Comment.id)
    .correlate_except(_CommentAlias)
    .scalar_subquery()
)