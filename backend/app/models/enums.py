from enum import Enum


# ENUMS
class ReactionType(str, Enum):
    """Types of reactions users can give to comments."""

    LIKE = "like"
    DISLIKE = "dislike"
    LAUGH = "laugh"
    CONFUSED = "confused"
    FIRE = "fire"


class Permission(str, Enum):
    """Available permissions for group members."""

    ADMINISTRATOR = "administrator"
    
    # Comments
    ADD_COMMENTS = "add_comments"
    REMOVE_COMMENTS = "remove_comments"
    VIEW_PUBLIC_COMMENTS = "view_public_comments"
    VIEW_RESTRICTED_COMMENTS = "view_restricted_comments"
    
    # Members
    ADD_MEMBERS = "add_members"
    REMOVE_MEMBERS = "remove_members"
    MANAGE_PERMISSIONS = "manage_permissions"
    
    # Documents
    ADD_DOCUMENTS = "upload_documents"
    VIEW_RESTRICTED_DOCUMENTS = "view_restricted_documents"
    REMOVE_DOCUMENTS = "delete_documents"

    # Reactions
    REMOVE_REACTIONS = "remove_reactions"
    ADD_REACTIONS = "add_reactions"
    
    # Share Links
    MANAGE_SHARE_LINKS = "manage_share_links"


class ViewMode(str, Enum):
    """Document view mode settings."""

    PRIVATE = "private"
    ANONYMOUS = "anonymous"
    PUBLIC = "public"


class Visibility(str, Enum):
    """Visibility levels for comments."""

    PRIVATE = "private"
    RESTRICTED = "restricted"
    PUBLIC = "public"

class AppErrorCode(str, Enum):
    """Types of custom application exceptions."""

    UNKNOWN_ERROR = "unknown_error"
    VALIDATION_ERROR = "validation_error"
    INVALID_INPUT = "invalid_input"  # use when user input is faulty e.g. a value error when hitting db constraints like string length

    # Database Errors
    DATABASE_UNAVAILABLE = "database_unavailable"  # use when the database is down or unreachable

    # Authentication & Authorization Errors
    INVALID_TOKEN = "invalid_token"  # use when JWT is invalid/expired
    NOT_AUTHENTICATED = "not_authenticated"  # use when user is not logged in (no bearer token)
    NOT_AUTHORIZED = "not_authorized"  # use when user lacks necessary permissions
    INVALID_CREDENTIALS = "invalid_credentials"  # use when username/password is incorrect
    NOT_IN_GROUP = "not_in_group"  # use when user is not a member of the group they are trying to access
