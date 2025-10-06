from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Column, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import column_property, declared_attr
from sqlmodel import Field, Relationship, func, select

from models.base import BaseModel
from models.enums import Permission, ViewMode, Visibility


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

    def rotate_secret(self) -> None:
        """Rotate the user secret to invalidate existing tokens."""
        self.secret = str(uuid4())
        


class Membership(BaseModel, table=True):
    """Association table for user-group relationships with permissions."""

    user_id: int = Field(foreign_key="user.id",
                         ondelete="CASCADE", primary_key=True)
    group_id: int = Field(foreign_key="group.id",
                          ondelete="CASCADE", primary_key=True)
    permissions: list[Permission] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    is_owner: bool = Field(default=False)
    accepted: bool = Field(default=False)
    user: User = Relationship(back_populates="memberships")
    group: "Group" = Relationship(back_populates="memberships")


class Group(BaseModel, table=True):
    """Group entity for shared document management."""

    id: int = Field(default=None, primary_key=True)
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

    # ondelete behavior for the owner needs to programmatically implemented in routers.users.delete (transfer ownership)
    @property
    def owner(self) -> User | None:
        """Get the owner user of the group."""
        for membership in self.memberships:
            if membership.is_owner:
                return membership.user
        return None
        
    documents: list["Document"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "noload"})
    memberships: list["Membership"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "selectin"})
    share_links: list["ShareLink"] = Relationship(
        back_populates="group", sa_relationship_kwargs={"lazy": "noload"})
    
    def rotate_secret(self) -> None:
        """Rotate the group secret to invalidate existing tokens."""
        self.secret = str(uuid4())


class Document(BaseModel, table=True):
    """Document entity representing uploaded files."""

    id: int = Field(default=None, primary_key=True)
    s3_key: str = Field(index=True, unique=True)
    size_bytes: int = Field(default=0)
    visibility: Visibility = Field(default=Visibility.PRIVATE, sa_column=Column(String, server_default=Visibility.PRIVATE.value))
    view_mode: ViewMode = Field(
        default=ViewMode.PUBLIC,
        sa_column=Column(String, server_default=ViewMode.PUBLIC.value)
    )
    secret: UUID = Field(default_factory=func.gen_random_uuid, sa_column=Column(PGUUID(as_uuid=True)))

    group_id: int = Field(
        foreign_key="group.id", nullable=True, ondelete="CASCADE")

    group: Group = Relationship(back_populates="documents")

    comments: list["Comment"] = Relationship(
        back_populates="document", sa_relationship_kwargs={"lazy": "noload"})

    __table_args__ = (
        CheckConstraint(
            "NOT (user_id IS NOT NULL AND group_id IS NOT NULL)",
            name="owner_xor"
        ),
    )

class Comment(BaseModel, table=True):
    """Comment entity for annotations and discussions."""

    id: int = Field(default=None, primary_key=True)
    visibility: Visibility = Field()
    document_id: int = Field(foreign_key="document.id", ondelete="CASCADE")
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
        sa_relationship_kwargs={"lazy": "noload"}
    )
    reactions: list["Reaction"] = Relationship(
        back_populates="comment",
        sa_relationship_kwargs={"lazy": "noload"}
    )

class Reaction(BaseModel, table=True):
    """Reaction entity for user reactions to comments."""
    
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE", primary_key=True)
    comment_id: int = Field(foreign_key="comment.id", ondelete="CASCADE", primary_key=True)
    type: str = Field()  # e.g. "like", "heart", "laugh"

    user: "User" = Relationship(back_populates="reactions")
    comment: "Comment" = Relationship(back_populates="reactions")

class ShareLink(BaseModel, table=True):
    """A link granting access to a group with specified permissions."""

    id: int = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id", ondelete="CASCADE")
    created_by_id: int = Field(foreign_key="user.id", ondelete="SET NULL", nullable=True)
    permissions: list[Permission] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String))
    )

    token: str = Field(
        default_factory=func.gen_random_uuid,
        sa_column=Column(String, unique=True, index=True)
    )
    
    expires_at: datetime | None = Field(default=None, nullable=True)
    label: str | None = Field(default=None, nullable=True)  # e.g. "Link for review team"

    group: "Group" = Relationship(back_populates="share_links")
    created_by: Optional["User"] = Relationship(sa_relationship_kwargs={"lazy": "noload"})

    def rotate_token(self) -> None:
        """Invalidate this share link by rotating its token."""
        self.token = str(uuid4())[:8]
