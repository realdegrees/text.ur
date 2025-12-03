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
    user = db.exec(query).first()
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
    invalid_memberships = db.exec(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.is_expired == True,  # noqa: E712
            )
        ).all()
    for membership in invalid_memberships:
        db.delete(membership)
    db.commit()

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
    user: User | None = db.exec(query).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    reset_link: str = mail.generate_verification_link(
        email, router, salt="password-reset", confirm_route="verify")
    expiry_time = datetime.now(UTC) + timedelta(days=cfg.REGISTER_LINK_EXPIRY_DAYS)
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


@router.put("/reset/verify/{token}", response_class=RedirectResponse)
async def reset_verify(token: str, db: Database, password: str = Body(..., embed=True)) -> RedirectResponse:
    """Confirm password reset using the presigned URL and update the user's password."""
    try:
        email: str = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET).loads(
            token, max_age=int(cfg.REGISTER_LINK_EXPIRY_DAYS * 24 * 60 * 60), salt="password-reset")
    except (BadSignature, SignatureExpired) as e:
        raise HTTPException(
            status_code=403, detail="Invalid or expired token") from e
    query = select(User).where(User.email == email)
    user: User | None = db.exec(query).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = hash_password(password)
    db.commit()
    return RedirectResponse(url="/login")
