from enum import Enum, StrEnum


# ENUMS
class ReactionType(StrEnum):
    """Types of reactions users can give to comments."""

    THUMBS_UP = "thumbs_up"
    SMILE = "smile"
    HEART = "heart"
    FIRE = "fire"
    PINCH = "pinch"
    NERD = "nerd"


class Permission(StrEnum):
    """Available permissions for group members."""

    ADMINISTRATOR = "administrator"
    
    # Comments
    ADD_COMMENTS = "add_comments"
    REMOVE_COMMENTS = "remove_comments"
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

    # Tags
    MANAGE_TAGS = "manage_tags"

class ViewMode(StrEnum):
    """Document view mode settings.

    RESTRICTED: Only owner, admins, and users with VIEW_RESTRICTED_COMMENTS can see comments
    PUBLIC: Comments visible based on individual comment visibility settings
    """

    RESTRICTED = "restricted"
    PUBLIC = "public"


class Visibility(StrEnum):
    """Visibility levels for comments."""

    PRIVATE = "private"
    RESTRICTED = "restricted"
    PUBLIC = "public"

class AppErrorCode(StrEnum):
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
    EMAIL_NOT_VERIFIED = "email_not_verified"  # use when user has not verified their email address
    SHARELINK_INVALID = "sharelink_invalid"  # use when sharelink token is invalid
    SHARELINK_EXPIRED = "sharelink_expired"  # use when sharelink has
    
    # Group Membership Errors
    MEMBERSHIP_NOT_FOUND = "membership_not_found"  # use when membership invite is not found or has been revoked or user is not a member of the group
    OWNER_CANNOT_LEAVE_GROUP = "owner_cannot_leave_group"  # use when the owner tries to leave the group instead of deleting it
    CANNOT_REMOVE_PERMISSION_REASON_DEFAULT_GROUP = "cannot_remove_permission_reason_default_group"  # use when trying to remove a permission that is included in the group's default permission reason
    CANNOT_REMOVE_PERMISSION_REASON_SHARELINK = "cannot_remove_permission_reason_sharelink"  # use when trying to remove a permission that is included in the related sharelink's permission reason
    
    # Reactions
    SELF_REACTION = "self_reaction"  # use when a user tries to react to their own comment
    REPLY_REACTION = "reply_reaction"  # use when a user tries to react to a reply (only root comments allowed)

    # Rate Limiting
    RATE_LIMITED = "rate_limited"  # use when a client has exceeded the request rate limit

    # Registration Errors
    USERNAME_TAKEN = "username_taken"  # use when the username is already registered
    EMAIL_TAKEN = "email_taken"  # use when the email is already registered
    SHARELINK_ANONYMOUS_DISABLED = "sharelink_anonymous_disabled"  # use when sharelink does not allow anonymous access

