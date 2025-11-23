import core.config as cfg
from api.dependencies.database import Database
from api.dependencies.mail import Mail
from core.auth import (
    Token,
    generate_token,
    hash_password,
)
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from models.tables import User
from models.user import UserCreate
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from util.api_router import APIRouter

router = APIRouter(
    prefix="/register",
    tags=["Register"]
)


@router.post("/")
async def register(request: Request, db: Database, mail: Mail, user_create: UserCreate) -> None:
    """Register a new user."""
    existing_user = db.exec(
        select(User).where((User.email == user_create.email) | (User.username == user_create.username))
    ).first()

    if existing_user:
        if not existing_user.verified:
            db.delete(existing_user)
            db.commit()
        elif existing_user.username == user_create.username:
            raise HTTPException(
                status_code=400, detail="Username already registered")
        else:
            raise HTTPException(
                status_code=400, detail="Email already registered")

    user = User(**user_create.model_dump())
    user.password = hash_password(user_create.password)

    # Attempt to create user
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as e:
        raise HTTPException(
            status_code=400, detail="Username or email already exists") from e


    # Send verification email
    try:
        verification_link = mail.generate_verification_link(
            user.email, request.base_url, router, salt="email-verification", confirm_route="verify")
        mail.send_email(user.email, subject="Email Verification", template="register.jinja", template_vars={
            "verification_link": verification_link,
            "expiry_minutes": cfg.EMAIL_PRESIGN_EXPIRY // 60
        })
    except Exception as e:
        db.delete(user)
        db.commit()
        raise e


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
