import core.config as cfg
from api.dependencies.database import Database
from api.dependencies.mail import Mail
from core.auth import hash_password
from fastapi import HTTPException, Request, Response
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
async def register(request: Request, db: Database, mail: Mail, user: UserCreate) -> None:
    """Register a new user."""
    user = User(**user.model_dump())
    user.password = hash_password(user.password)

    # Attempt to create user
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail="Username or email already exists") from e

    # Send verification email
    try:
        verification_link = mail.generate_verification_link(user.email, request.base_url, router, salt="email-verification", confirm_route="verify")
        mail.send_email(user.email, subject="Email Verification", template="register.jinja", template_vars={
            "verification_link": verification_link,
            "expiry_minutes": cfg.EMAIL_PRESIGN_EXPIRY // 60
        })
    except Exception as e:
        db.delete(user)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to send verification email") from e



@router.get("/verify/{token}")
async def verify(token: str, db: Database) -> None:
    """Verify the user's email address."""
    try:
        email = URLSafeTimedSerializer(cfg.EMAIL_PRESIGN_SECRET).loads(token, max_age=cfg.EMAIL_PRESIGN_EXPIRY, salt="email-verification")
    except (BadSignature, SignatureExpired) as e:
        raise HTTPException(status_code=403, detail="Invalid or expired token") from e

    query = select(User).filter(User.email == email)
    user: User | None = db.exec(query).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.verified = True
    db.commit()
    return Response(status_code=204) # TODO: Redirect to the frontend login page with a success message and maybe even attach the Tokens to cookies already