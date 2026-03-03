import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated

import core.config as cfg
from api.dependencies.authentication import Authenticate
from api.dependencies.database import Database
from api.dependencies.mail import Mail
from core.app_exception import AppException
from core.auth import (
    Token,
    generate_token,
    hash_password,
    validate_password,
)
from core.logger import get_logger
from core.rate_limit import get_cache_key, limiter
from fastapi import Body, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from models.enums import AppErrorCode
from models.tables import Membership, User
from models.user import PasswordResetVerify
from sqlmodel import or_, select
from util.api_router import APIRouter

login_logger = get_logger("app")

router = APIRouter(
    prefix="/login",
    tags=["Login"],
)


@router.post("/")
@limiter.limit("30/minute", key_func=get_cache_key)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Database,
    response: Response,
) -> Token:
    """Return a JWT if the user is authenticated successfully."""
    login_input = form_data.username
    query = select(User).where(
        or_(
            User.username == login_input,
            User.email == login_input.lower().strip(),
        )
    )
    result = await db.exec(query)
    user = result.first()
    if user is None or not validate_password(user, form_data.password):
        raise AppException(
            status_code=401,
            error_code=AppErrorCode.INVALID_CREDENTIALS,
            detail="Incorrect username or password",
        )

    if not user.verified:
        raise AppException(
            status_code=403,
            detail="Forbidden: Email not verified",
            error_code=AppErrorCode.EMAIL_NOT_VERIFIED,
        )

    token = Token(
        access_token=generate_token(user, "access"),
        refresh_token=generate_token(user, "refresh"),
        token_type="bearer",
    )
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=int(cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60),
    )
    response.set_cookie(
        key="refresh_token",
        value=token.refresh_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=int(cfg.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60),
    )
    return token


@router.post("/refresh")
@limiter.limit("30/minute", key_func=get_cache_key)
async def refresh(
    request: Request,
    response: Response,
    db: Database,
    user: User = Authenticate(token_type="refresh"),
) -> Token:
    """Refresh the access token given a valid refresh token."""
    token = Token(
        access_token=generate_token(user, "access"),
        token_type="bearer",
    )

    # Find all memberships for the user where a share_link is present and delete the membership if the share_link is expired or if
    result = await db.exec(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.is_expired == True,  # noqa: E712
        )
    )
    invalid_memberships = result.all()
    for membership in invalid_memberships:
        await db.delete(membership)
    await db.commit()

    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=int(cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60),
    )

    return token


@router.post("/reset")
@limiter.limit("10/minute", key_func=get_cache_key)
async def reset_password(
    request: Request,
    db: Database,
    mail: Mail,
    email: str = Body(..., embed=True),
) -> None:
    """Send a password reset email with a presigned URL."""
    email = email.lower().strip()
    query = select(User).where(User.email == email)
    result = await db.exec(query)
    user: User | None = result.first()
    if not user:
        # Return silently to avoid leaking whether an email is registered
        return
    # Generate token with email and password hash (for one-time use)
    serializer = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET)
    pwd_hash = hashlib.sha256(user.password[:16].encode()).hexdigest()[:16]
    token_data = {"email": email, "pwd": pwd_hash}
    token = serializer.dumps(token_data, salt="password-reset")
    reset_link = f"{cfg.FRONTEND_BASEURL}/password-reset/{token}"
    expiry_time = datetime.now(UTC) + timedelta(minutes=cfg.PASSWORD_RESET_LINK_EXPIRY_MINUTES)
    try:
        mail.send_email(
            target_email=email,
            subject="Reset Your Password - text.ur",
            template="reset_password.jinja",
            template_vars={
                "reset_link": reset_link,
                "expiry_time": expiry_time.strftime("%B %d, %Y at %H:%M UTC"),
                "email": email,
                "username": user.username,
                "current_year": datetime.now(UTC).year,
            },
        )
    except Exception as e:
        if cfg.DEBUG and cfg.DEBUG_ALLOW_REGISTRATION_WITHOUT_EMAIL:
            login_logger.warning(
                "Email delivery failed but"
                " DEBUG_ALLOW_REGISTRATION_WITHOUT_EMAIL"
                " is set. Password reset email for '%s'"
                " not sent.\n[Reset link: %s]",
                email,
                reset_link,
            )
            return
        raise AppException(
            status_code=500,
            error_code=AppErrorCode.MAIL_SEND_FAILED,
            detail="Failed to send reset email",
        ) from e


@router.put("/reset/verify/{token}")
@limiter.limit("20/minute", key_func=get_cache_key)
async def reset_verify(
    request: Request,
    token: str,
    db: Database,
    body: PasswordResetVerify = Body(...),
) -> None:
    """Confirm password reset using the presigned URL and update the user's password."""
    try:
        # Deserialize token to get token data (email + password hash for one-time use)
        serializer = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET)
        token_data = serializer.loads(
            token,
            max_age=int(cfg.PASSWORD_RESET_LINK_EXPIRY_MINUTES * 60),
            salt="password-reset",
        )

        email = token_data["email"]
        pwd_hash_check = token_data.get("pwd")

    except (BadSignature, SignatureExpired) as e:
        raise AppException(
            status_code=403,
            error_code=AppErrorCode.INVALID_TOKEN,
            detail="Invalid or expired token",
        ) from e

    query = select(User).where(User.email == email)
    result = await db.exec(query)
    user: User | None = result.first()
    if not user:
        raise AppException(
            status_code=404,
            error_code=AppErrorCode.NOT_FOUND,
            detail="User not found",
        )

    # Check if token has already been used (password changed since token was issued)
    current_pwd_hash = hashlib.sha256(user.password[:16].encode()).hexdigest()[:16]
    if pwd_hash_check and current_pwd_hash != pwd_hash_check:
        raise AppException(
            status_code=403,
            error_code=AppErrorCode.TOKEN_ALREADY_USED,
            detail="Reset link has already been used",
        )

    # Update password and rotate user secret to invalidate all sessions
    user.password = hash_password(body.password)
    user.rotate_secret()
    db.add(user)
    await db.commit()
