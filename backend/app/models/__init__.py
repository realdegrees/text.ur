"""Exports all models and schemas that need to be either rebuilt on start OR included in the pydantic2ts scope for frontend model generation"""

from models.auth import GlobalJWTPayload, Token, UserJWTPayload
from models.comment import (
    CommentCreate,
    CommentRead,
    CommentUpdate,
)
from models.document import (
    DocumentCreate,
    DocumentRead,
    DocumentTransfer,
)
from models.filter import (
    CommentFilter,
    DocumentFilter,
    GroupFilter,
    GroupMembershipFilter,
    UserFilter,
)
from models.group import (
    GroupCreate,
    GroupMembershipRead,
    GroupRead,
    GroupUpdate,
    UserMembershipRead,
)
from models.pagination import PaginatedBase
from models.reaction import ReactionCreate, ReactionRead
from models.sharelink import ShareLinkCreate, ShareLinkRead, ShareLinkUpdate
from models.tables import Comment, Document, Group, Membership, User
from models.user import UserCreate, UserPrivate, UserRead, UserUpdate

# ! Models that use TYPE_CHECKING for string type hints need to be imported and rebuilt here to avoid runtime errors

Document.model_rebuild()
Group.model_rebuild()
User.model_rebuild()
Comment.model_rebuild()
Membership.model_rebuild()

CommentCreate.model_rebuild()
CommentRead.model_rebuild()
CommentUpdate.model_rebuild()
CommentFilter.model_rebuild()

ReactionCreate.model_rebuild()
ReactionRead.model_rebuild()

DocumentCreate.model_rebuild()
DocumentRead.model_rebuild()
DocumentTransfer.model_rebuild()
DocumentFilter.model_rebuild()

GroupCreate.model_rebuild()
GroupRead.model_rebuild()
GroupUpdate.model_rebuild()
GroupFilter.model_rebuild()
GroupMembershipFilter.model_rebuild()
GroupMembershipRead.model_rebuild()
UserMembershipRead.model_rebuild()

ShareLinkCreate.model_rebuild()
ShareLinkRead.model_rebuild()
ShareLinkUpdate.model_rebuild()

UserCreate.model_rebuild()
UserRead.model_rebuild()
UserUpdate.model_rebuild()
UserFilter.model_rebuild()
UserPrivate.model_rebuild()