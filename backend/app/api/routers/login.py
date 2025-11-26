from datetime import UTC, datetime
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
from models.auth import ShareLinkTokens
from models.enums import AppErrorCode
from models.tables import Membership, ShareLink, User
from sqlmodel import select
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
    query = select(User).where(User.username == form_data.username)
    user = db.exec(query).first()
    if user is None or not validate_password(user, form_data.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.verified:
        raise AppException(status_code=403, detail="Forbidden: Email not verified", error_code=AppErrorCode.EMAIL_NOT_VERIFIED)
        
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
        max_age=cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=token.refresh_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=cfg.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60
    )
    return token


@router.post("/refresh")
async def refresh(response: Response, user: User = Authenticate(token_type="refresh")) -> Token:
    """Refresh the access token given a valid refresh token."""
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
        max_age=cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=token.refresh_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=cfg.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60
    )
    return token


@router.post("/reset")
async def reset_password(request: Request, db: Database, mail: Mail, email: str = Body(..., embed=True)) -> None:
    """Send a password reset email with a presigned URL."""
    query = select(User).where(User.email == email)
    user: User | None = db.exec(query).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    reset_link: str = mail.generate_verification_link(email, router, salt="password-reset", confirm_route="verify")
    try:
        template = cfg.JINJA_ENV.get_template("reset_password.jinja")
        html_body: str = template.render(
            reset_link=f"{request.base_url}reset?url={reset_link}",
            expiry_minutes=cfg.EMAIL_PRESIGN_EXPIRY // 60
        )
        mail.send_email(email, html_body, subject="Password Reset")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send reset email") from e

@router.put("/reset/verify/{token}", response_class=RedirectResponse)
async def reset_verify(token: str, db: Database, password: str = Body(..., embed=True)) -> RedirectResponse:
    """Confirm password reset using the presigned URL and update the user's password."""
    try:
        email: str = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET).loads(token, max_age=cfg.EMAIL_PRESIGN_EXPIRY, salt="password-reset")
    except (BadSignature, SignatureExpired) as e:
        raise HTTPException(status_code=403, detail="Invalid or expired token") from e
    query = select(User).where(User.email == email)
    user: User | None = db.exec(query).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = hash_password(password)
    db.commit()
    return RedirectResponse(url="/login")


@router.post("/anonymous/refresh")
async def anonymous_refresh(
    db: Database,
    response: Response,
    request: Request,
) -> Token:
    """Verify and re-authenticate an anonymous user using their sharelink token from cookies.

    This endpoint is used to re-authenticate anonymous users by checking if their
    stored sharelink token is still valid.
    """
    # Get sharelink token from cookie
    sharelink_token_data: ShareLinkTokens | None = None
    try: 
        sharelink_token_data = ShareLinkTokens.model_validate(request.cookies.get("sharelink_tokens"))
    except Exception as e:
        raise AppException(status_code=401, detail="Invalid sharelink token format", error_code=AppErrorCode.NOT_AUTHENTICATED) from e
        
    if not sharelink_token_data:
        raise HTTPException(status_code=401, detail="No sharelink tokens found")
    
    sharelink_tokens = sharelink_token_data.groups

    # Find all share links by their token
    share_links: list[ShareLink] = db.exec(
        select(ShareLink).where(ShareLink.token.in_(sharelink_tokens.values()))
    ).all()
    
    # Filter out expired share links
    share_links = [sl for sl in share_links if not sl.expires_at or sl.expires_at >= datetime.now(tz=sl.expires_at.tzinfo)]
    
    sharelink_token_data = ShareLinkTokens(
        user_id=sharelink_token_data.user_id,
        groups={str(sl.group_id): str(sl.token) for sl in share_links}
    )

    if not len(share_links):
        raise HTTPException(status_code=404, detail="No valid sharelink tokens found")

    # Check if user exists
    user: User | None = db.exec(select(User).where(User.id == sharelink_token_data.user_id)).first()

    # Generate new tokens
    token = Token(
        access_token=generate_token(user, "access", scopes=[f"/groups/{share_link.group_id}" for share_link in share_links]),
        token_type="bearer",
    )

    # Update cookies
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=cfg.JWT_ACCESS_EXPIRATION_MINUTES * 60
    )
    
    # Refresh the max_age of the sharelink token cookie and update valid groups
    response.set_cookie(
        key="sharelink_tokens",
        value=sharelink_token_data.model_dump_json(),
        httponly=True,
        secure=cfg.COOKIE_SECURE,
        samesite=cfg.COOKIE_SAMESITE,
        max_age=cfg.JWT_REFRESH_EXPIRATION_DAYS * 24 * 60 * 60
    )

    return token
