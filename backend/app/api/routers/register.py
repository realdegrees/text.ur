from datetime import datetime

import core.config as cfg
from api.dependencies.database import Database
from api.dependencies.mail import Mail
from core.app_exception import AppException
from core.auth import (
    Token,
    generate_token,
    hash_password,
)
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from models.auth import ShareLinkTokens
from models.enums import AppErrorCode
from models.tables import Membership, ShareLink, User
from models.user import UserCreate
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from util.api_router import APIRouter

router = APIRouter(
    prefix="/register",
    tags=["Register"]
)


def _register_regular_user(
    db: Database,
    mail: Mail,
    user_create: UserCreate
) -> None:
    """Handle regular user registration with email verification."""
    existing_user = db.exec(
        select(User).where(
            (User.email == user_create.email) | (User.username == user_create.username)
        )
    ).first()

    if existing_user:
        if not existing_user.verified:
            db.delete(existing_user)
            db.commit()
        elif existing_user.username == user_create.username:
            raise AppException(
                status_code=400,
                detail="Username already registered",
                error_code=AppErrorCode.USERNAME_TAKEN
            )
        else:
            raise AppException(
                status_code=400,
                detail="Email already registered",
                error_code=AppErrorCode.EMAIL_TAKEN
            )

    user = User(**user_create.model_dump(exclude={'token'}))
    user.password = hash_password(user_create.password)

    # Attempt to create user
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as e:
        raise HTTPException(
            status_code=400, detail="Username or email already exists"
        ) from e

    # Send verification email
    try:
        verification_link = mail.generate_verification_link(
            user.email, router, salt="email-verification", confirm_route="verify"
        )
        mail.send_email(
            user.email,
            subject="Email Verification",
            template="register.jinja",
            template_vars={
                "verification_link": verification_link,
                "expiry_minutes": cfg.EMAIL_PRESIGN_EXPIRY // 60
            }
        )
    except Exception as e:
        db.delete(user)
        db.commit()
        raise e


def _register_anonymous_user(
    request: Request,
    db: Database,
    response: Response,
    user_create: UserCreate,
    sharelink_token: str
) -> Token:
    """Handle anonymous user registration with sharelink token."""
    # Find the sharelink by token
    share_link: ShareLink | None = db.exec(
        select(ShareLink).where(ShareLink.token == sharelink_token)
    ).first()

    if not share_link:
        raise AppException(status_code=401, detail="Invalid sharelink token", error_code=AppErrorCode.INVALID_TOKEN)

    # Check if expired
    if share_link.expires_at and share_link.expires_at < datetime.now(share_link.expires_at.tzinfo):
        raise AppException(status_code=403, detail="Share link has expired", error_code=AppErrorCode.SHARELINK_EXPIRED)
    
    # Check if anonymous access is allowed
    if not share_link.allow_anonymous_access:
        raise AppException(status_code=403, detail="Anonymous access is not allowed with this sharelink", error_code=AppErrorCode.SHARELINK_ANONYMOUS_DISABLED)

    # Check if username already exists
    existing_user = db.exec(
        select(User).where(User.username == user_create.username)
    ).first()
    if existing_user:
        raise AppException(status_code=400, detail="Username already registered", error_code=AppErrorCode.USERNAME_TAKEN)

    # Create anonymous user
    user = User(
        username=user_create.username,
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        verified=True,  # Auto-verify anonymous users
        is_guest=True,  # Mark as guest user
    )
    db.add(user)
    db.flush()  # Get user.id without committing

    # Create membership
    membership = Membership(
        user_id=user.id,
        group_id=share_link.group_id,
        permissions=share_link.permissions,
        is_owner=False,
        accepted=True,
    )
    db.add(membership)
    db.commit()
    db.refresh(user)

    # Generate tokens
    token = Token(
        access_token=generate_token(user, "access"),
        refresh_token=generate_token(user, "refresh"),
        token_type="bearer",
    )

    existing_sharelink_token_data: ShareLinkTokens | None = None
    try:
        existing_sharelink_token_data = ShareLinkTokens.model_validate(
            request.cookies.get("sharelink_tokens")
        )
    except Exception:  # noqa: S110
        pass

    share_link_token_data = ShareLinkTokens(
        user_id=user.id,
        groups={share_link.group_id: sharelink_token} | (
            existing_sharelink_token_data.groups if existing_sharelink_token_data else {}
        )
    )

    # Set cookies with sharelink token for re-authentication
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60
    )
    response.set_cookie(
        key="sharelink_tokens",
        value=share_link_token_data.model_dump_json(),
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE
    )

    return token


@router.post("/")
async def register(
    request: Request,
    db: Database,
    mail: Mail,
    response: Response,
    user_create: UserCreate
) -> Token | None:
    """Register a new user or anonymous user.

    Supports two registration modes:
    1. Regular registration: Requires email and password, sends verification email
    2. Anonymous registration: Requires sharelink token, auto-verifies and logs in

    If both email and token are provided, email takes precedence (regular registration).
    """
    # Validate that at least one of email or token is provided
    if not user_create.email and not user_create.token:
        raise HTTPException(
            status_code=400,
            detail="Either email or token must be provided"
        )

    # Determine registration mode: use email if both are present
    is_anonymous = not user_create.email and user_create.token

    if is_anonymous:
        return _register_anonymous_user(request, db, response, user_create, user_create.token)
    else:
        # Regular registration requires password
        if not user_create.password:
            raise HTTPException(
                status_code=400,
                detail="Password is required for regular registration"
            )
        _register_regular_user(db, mail, user_create)
        return None

@router.get("/verify/{token}")
async def verify(token: str, db: Database) -> RedirectResponse:
    """Verify the user's email address."""
    try:
        email = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET).loads(
            token, max_age=cfg.EMAIL_PRESIGN_EXPIRY, salt="email-verification"
        )
    except (BadSignature, SignatureExpired) as e:
        raise HTTPException(
            status_code=403, detail="Invalid or expired token") from e

    query = select(User).filter(User.email == email)
    user: User | None = db.exec(query).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.verified = True
    db.commit()

    # Generate tokens
    auth_token = Token(
        access_token=generate_token(user, "access"),
        refresh_token=generate_token(user, "refresh"),
        token_type="bearer",
    )

    # Create the redirect response
    redirect_response = RedirectResponse(
        url=f"{cfg.FRONTEND_BASEURL}?verified=true", status_code=303)

    # Set cookies on that response
    redirect_response.set_cookie(
        key="access_token",
        value=auth_token.access_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60
    )
    redirect_response.set_cookie(
        key="refresh_token",
        value=auth_token.refresh_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=cfg.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60
    )

    return redirect_response
