import core.config as cfg
from api.dependencies.authentication import BasicAuthentication
from api.dependencies.database import Database
from fastapi import Response
from util.api_router import APIRouter

router = APIRouter(
    prefix="/logout",
    tags=["Logout"],
)


@router.post("/")
async def logout(response: Response) -> None:
    """Log the user out by clearing the authentication cookies."""
    response.set_cookie(key="access_token", value="", httponly=True, secure=cfg.COOKIE_SECURE, samesite=cfg.COOKIE_SAMESITE, max_age=0)
    response.set_cookie(key="refresh_token", value="", httponly=True, secure=cfg.COOKIE_SECURE, samesite=cfg.COOKIE_SAMESITE, max_age=0)


@router.post("/all")
async def logout_all_devices(response: Response, user: BasicAuthentication, db: Database) -> None:
    """Log the user out from all devices by rerolling the user secret."""
    # Use the logout method  to clear cookies on the response
    await logout(response)
    # Rotate the user secret to invalidate all existing tokens
    await db.merge(user)
    user.rotate_secret()
    await db.commit()
