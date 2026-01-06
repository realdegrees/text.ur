from datetime import UTC, datetime, timedelta

import core.config as cfg
from api.dependencies.authentication import Authenticate
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


async def _upgrade_guest_account(
    db: Database,
    mail: Mail,
    user: User,
    user_create: UserCreate
) -> None:
    """Upgrade a guest account to a permanent account with email verification."""
    if not user.is_guest:
        raise AppException(
            status_code=400,
            detail="Account is already a permanent account",
            error_code=AppErrorCode.INVALID_INPUT
        )

    # Check if email is already taken
    result = await db.exec(
        select(User).where(User.email == user_create.email)
    )
    existing_user = result.first()

    if existing_user and existing_user.id != user.id:
        raise AppException(
            status_code=400,
            detail="Email already registered",
            error_code=AppErrorCode.EMAIL_TAKEN
        )

    # Update user with email and password
    user.email = user_create.email
    user.password = hash_password(user_create.password)
    user.verified = False  # Require email verification

    # Update optional fields if provided
    if user_create.first_name is not None:
        user.first_name = user_create.first_name
    if user_create.last_name is not None:
        user.last_name = user_create.last_name

    await db.commit()
    await db.refresh(user)

    # Send verification email
    try:
        verification_link = mail.generate_verification_link(
            user.email, router, salt="email-verification", confirm_route="verify"
        )
        expiry_time = datetime.now(UTC) + timedelta(days=cfg.REGISTER_LINK_EXPIRY_DAYS)
        mail.send_email(
            user.email,
            subject="Email Verification - Upgrade Your Account",
            template="register.jinja",
            template_vars={
                "verification_link": verification_link,
                "expiry_time": expiry_time.strftime("%B %d, %Y at %H:%M UTC"),
                "username": user.username,
                "email": user.email,
                "current_year": datetime.now().year
            }
        )
    except Exception as e:
        # Rollback the changes if email fails
        await db.rollback()
        raise e


async def _register_regular_user(
    db: Database,
    mail: Mail,
    user_create: UserCreate
) -> None:
    """Handle regular user registration with email verification."""
    result = await db.exec(
        select(User).where(
            (User.email == user_create.email) | (
                User.username == user_create.username)
        )
    )
    existing_user = result.first()

    if existing_user:
        if not existing_user.verified and not existing_user.is_guest:
            await db.delete(existing_user)
            await db.commit()
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
        await db.commit()
        await db.refresh(user)
    except IntegrityError as e:
        raise HTTPException(
            status_code=400, detail="Username or email already exists"
        ) from e

    # Send verification email
    try:
        verification_link = mail.generate_verification_link(
            user.email, router, salt="email-verification", confirm_route="verify"
        )
        expiry_time = datetime.now(UTC) + timedelta(days=cfg.REGISTER_LINK_EXPIRY_DAYS)
        mail.send_email(
            user.email,
            subject="Verify Your Email - text.ur",
            template="register.jinja",
            template_vars={
                "verification_link": verification_link,
                "expiry_time": expiry_time.strftime("%B %d, %Y at %H:%M UTC"),
                "username": user.username,
                "email": user.email,
                "current_year": datetime.now().year
            }
        )
    except Exception as e:
        await db.delete(user)
        await db.commit()
        raise e


async def _register_anonymous_user(
    request: Request,
    db: Database,
    response: Response,
    user_create: UserCreate,
    sharelink_token: str
) -> Token:
    """Handle anonymous user registration with sharelink token."""
    # Find the sharelink by token
    result = await db.exec(
        select(ShareLink).where(ShareLink.token == sharelink_token)
    )
    share_link: ShareLink | None = result.first()

    if not share_link:
        raise AppException(status_code=401, detail="Invalid sharelink token",
                           error_code=AppErrorCode.INVALID_TOKEN)

    # Check if expired
    if share_link.expires_at and share_link.expires_at < datetime.now(share_link.expires_at.tzinfo):
        raise AppException(status_code=403, detail="Share link has expired",
                           error_code=AppErrorCode.SHARELINK_EXPIRED)

    # Check if anonymous access is allowed
    if not share_link.allow_anonymous_access:
        raise AppException(status_code=403, detail="Anonymous access is not allowed with this sharelink",
                           error_code=AppErrorCode.SHARELINK_ANONYMOUS_DISABLED)

    # Check if username already exists
    result = await db.exec(
        select(User).where(User.username == user_create.username)
    )
    existing_user = result.first()
    if existing_user:
        raise AppException(status_code=400, detail="Username already registered",
                           error_code=AppErrorCode.USERNAME_TAKEN)

    # Create anonymous user
    user = User(
        username=user_create.username,
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        verified=True,  # Auto-verify anonymous users
        is_guest=True,  # Mark as guest user
    )
    db.add(user)
    await db.flush()  # Get user.id without committing

    await db.commit()

    # Generate tokens
    token = Token(
        access_token=generate_token(user, "access"),
        refresh_token=generate_token(user, "refresh"),
        token_type="bearer",
    )

    # Set cookies with sharelink token for re-authentication
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=int(cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60)
    )

    response.set_cookie(
        key="refresh_token",
        value=token.refresh_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=int(cfg.JWT_REFRESH_GUEST_EXPIRATION_DAYS * 24 * 60 * 60)
    )

    return token


@router.post("/")
async def register(
    request: Request,
    db: Database,
    mail: Mail,
    response: Response,
    user_create: UserCreate,
    authenticated_user: User | None = Authenticate(strict=False)
) -> Token | None:
    """Register a new user, anonymous user, or upgrade a guest account.

    Supports three registration modes:
    1. Regular registration: Requires email and password, sends verification email
    2. Anonymous registration: Requires sharelink token, auto-verifies and logs in
    3. Guest account upgrade: Authenticated guest user provides email+password to upgrade

    If both email and token are provided, email takes precedence (regular registration).
    If user is authenticated and is_guest=True with email+password, upgrade the account.
    """
    # Check if this is a guest account upgrade
    if authenticated_user and authenticated_user.is_guest and user_create.email and user_create.password:
        await _upgrade_guest_account(db, mail, authenticated_user, user_create)
        return None

    # Validate that at least one of email or token is provided
    if not user_create.email and not user_create.token:
        raise HTTPException(
            status_code=400,
            detail="Either email or token must be provided"
        )

    # Determine registration mode: use email if both are present
    is_anonymous = not user_create.email and user_create.token

    if is_anonymous:
        return await _register_anonymous_user(request, db, response, user_create, user_create.token)
    else:
        # Regular registration requires password
        if not user_create.password:
            raise HTTPException(
                status_code=400,
                detail="Password is required for regular registration"
            )
        await _register_regular_user(db, mail, user_create)
        return None


@router.get("/verify/{token}")
async def verify(token: str, db: Database) -> RedirectResponse:
    """Verify the user's email address."""
    try:
        email = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET).loads(
            token, max_age=int(cfg.REGISTER_LINK_EXPIRY_DAYS * 24 * 60 * 60), salt="email-verification"
        )
    except (BadSignature, SignatureExpired) as e:
        raise HTTPException(
            status_code=403, detail="Invalid or expired token") from e

    query = select(User).filter(User.email == email)
    result = await db.exec(query)
    user: User | None = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.verified:
        raise HTTPException(status_code=400, detail="User is already verified")

    user.verified = True

    # If this is a guest user upgrading their account, set is_guest to False
    if user.is_guest:
        user.is_guest = False

    await db.commit()

    # Generate tokens
    auth_token = Token(
        access_token=generate_token(user, "access"),
        refresh_token=generate_token(user, "refresh"),
        token_type="bearer",
    )

    # Create the redirect response to login page with verified param
    # Login page will redirect authenticated users to dashboard while preserving the param
    redirect_response = RedirectResponse(
        url=f"{cfg.FRONTEND_BASEURL}/login?verified=true", status_code=303)

    # Set cookies on that response
    redirect_response.set_cookie(
        key="access_token",
        value=auth_token.access_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=int(cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60)
    )
    redirect_response.set_cookie(
        key="refresh_token",
        value=auth_token.refresh_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=int(cfg.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60)
    )

    return redirect_response
