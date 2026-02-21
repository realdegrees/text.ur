from enum import Enum, StrEnum


# ENUMS
class ReactionType(StrEnum):
    """Types of reactions users can give to comments.

    .. deprecated::
        Kept only for migration compatibility. Use ``Emoji`` and
        ``GroupReaction`` for new code.
    """

    THUMBS_UP = "thumbs_up"
    SMILE = "smile"
    HEART = "heart"
    FIRE = "fire"
    PINCH = "pinch"
    NERD = "nerd"


class Emoji(StrEnum):
    """Available emoji characters that admins can pick from."""

    THUMBS_UP = "\U0001f44d"
    THUMBS_DOWN = "\U0001f44e"
    CLAP = "\U0001f44f"
    WAVE = "\U0001f44b"
    HEART = "\u2764\ufe0f"
    FIRE = "\U0001f525"
    STAR = "\u2b50"
    SPARKLES = "\u2728"
    PARTY = "\U0001f389"
    ROCKET = "\U0001f680"
    SMILE = "\U0001f60a"
    LAUGH = "\U0001f602"
    THINKING = "\U0001f914"
    NERD = "\U0001f913"
    COOL = "\U0001f60e"
    CRY = "\U0001f622"
    ANGRY = "\U0001f621"
    SURPRISED = "\U0001f632"
    MINDBLOWN = "\U0001f92f"
    EYES = "\U0001f440"
    HUNDRED = "\U0001f4af"
    CHECK = "\u2705"
    CROSS = "\u274c"
    WARNING = "\u26a0\ufe0f"
    QUESTION = "\u2753"
    BULB = "\U0001f4a1"
    PIN = "\U0001f4cc"
    BOOKMARK = "\U0001f516"
    TROPHY = "\U0001f3c6"
    MEDAL = "\U0001f3c5"
    CROWN = "\U0001f451"
    GEM = "\U0001f48e"
    PINCH = "\U0001faf0"
    BRAIN = "\U0001f9e0"


class Permission(StrEnum):
    """Available permissions for group members.

    Only four granular permissions exist. Every other privileged
    action (managing members, documents, tags, etc.) requires
    ADMINISTRATOR.
    """

    ADMINISTRATOR = "administrator"
    ADD_COMMENTS = "add_comments"
    VIEW_RESTRICTED_COMMENTS = "view_restricted_comments"
    ADD_REACTIONS = "add_reactions"

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


class DocumentVisibility(StrEnum):
    """Visibility levels for documents (private or public only)."""

    PRIVATE = "private"
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
    
    # Resource Not Found
    NOT_FOUND = "not_found"  # use when a requested resource does not exist

    # Reactions
    SELF_REACTION = "self_reaction"  # use when a user tries to react to their own comment
    REPLY_REACTION = "reply_reaction"  # use when a user tries to react to a reply (only root comments allowed)

    # Rate Limiting
    RATE_LIMITED = "rate_limited"  # use when a client has exceeded the request rate limit

    # Registration Errors
    USERNAME_TAKEN = "username_taken"  # use when the username is already registered
    EMAIL_TAKEN = "email_taken"  # use when the email is already registered
    SHARELINK_ANONYMOUS_DISABLED = "sharelink_anonymous_disabled"  # use when sharelink does not allow anonymous access

