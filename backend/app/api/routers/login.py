from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

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
from fastapi import Body, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from models.enums import AppErrorCode
from models.tables import Membership, User
from sqlmodel import or_, select
from util.api_router import APIRouter

router = APIRouter(
    prefix="/login",
    tags=["Login"],
)


@router.post("/")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Database, response: Response
) -> Token:
    """Return a JWT if the user is authenticated successfully."""
    query = select(User).where(or_(User.username == form_data.username, User.email == form_data.username))
    result = await db.exec(query)
    user = result.first()
    if user is None or not validate_password(user, form_data.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.verified:
        raise AppException(status_code=403, detail="Forbidden: Email not verified",
                           error_code=AppErrorCode.EMAIL_NOT_VERIFIED)

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
        max_age=int(cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60)
    )
    response.set_cookie(
        key="refresh_token",
        value=token.refresh_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=int(cfg.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60)
    )
    return token


@router.post("/refresh")
async def refresh(response: Response, request: Request, db: Database, user: User = Authenticate(token_type="refresh")) -> Token:
    """Refresh the access token given a valid refresh token."""
    token = Token(
        access_token=generate_token(user, "access"),
        refresh_token=generate_token(user, "refresh"),
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
        max_age=int(cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60)
    )

    return token


@router.post("/reset")
async def reset_password(request: Request, db: Database, mail: Mail, email: str = Body(..., embed=True)) -> None:
    """Send a password reset email with a presigned URL."""
    query = select(User).where(User.email == email)
    result = await db.exec(query)
    user: User | None = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Generate token with email and password hash (for one-time use)
    serializer = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET)
    token_data = {"email": email, "pwd": user.password[:16]}
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
                "current_year": datetime.now(UTC).year
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to send reset email") from e


@router.put("/reset/verify/{token}")
async def reset_verify(token: str, db: Database, password: str = Body(..., embed=True)) -> None:
    """Confirm password reset using the presigned URL and update the user's password."""
    try:
        # Deserialize token to get token data (email + password hash for one-time use)
        serializer = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET)
        token_data = serializer.loads(
            token, max_age=int(cfg.PASSWORD_RESET_LINK_EXPIRY_MINUTES * 60), salt="password-reset"
        )

        # Handle both old tokens (string) and new tokens (dict) for backwards compatibility
        if isinstance(token_data, str):
            email = token_data
            pwd_hash_check = None
        else:
            email = token_data["email"]
            pwd_hash_check = token_data.get("pwd")

    except (BadSignature, SignatureExpired) as e:
        raise HTTPException(
            status_code=403, detail="Invalid or expired token") from e

    query = select(User).where(User.email == email)
    result = await db.exec(query)
    user: User | None = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if token has already been used (password changed since token was issued)
    if pwd_hash_check and user.password[:16] != pwd_hash_check:
        raise HTTPException(status_code=403, detail="Reset link has already been used")

    # Update password and rotate user secret to invalidate all sessions
    user.password = hash_password(password)
    user.rotate_secret()
    db.add(user)
    await db.commit()
