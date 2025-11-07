from collections.abc import Sequence
from typing import Annotated, Any, Literal

from api.dependencies.database import Database
from core.app_exception import AppException
from core.auth import oauth2_scheme, parse_jwt
from core.logger import get_logger
from fastapi import Depends, Request, WebSocket
from models.enums import AppErrorCode
from models.tables import User
from sqlmodel import select
from util.queries import EndpointGuard

logger = get_logger("app")

def Authenticate( # noqa: C901
    guards: Sequence[EndpointGuard] = (),
    *,
    endpoint: Literal["ws", "http"] = "http",
    strict: bool = True,
    token_type: Literal["access", "refresh"] = "access",  # noqa: S107
) -> Depends:
    """Provide a dependency that checks if the user is authenticated and has the required roles.

    Args:
        guards: A sequence of EndpointGuard instances. A user.id == User.id guard is always appended for authentication.
        endpoint: The endpoint type ("ws" or "http").
        strict: Whether to enforce strict token validation. If validation fails, an exception is raised.
        token_type: The type of token to validate ("access" or "refresh").

    Returns:
        A FastAPI dependency that returns the authenticated user.

    Raises:
        HTTPException: If the user is not authenticated or does not pass custom validation.

    """
    async def dependency(
        db: Database,
        context: Request | WebSocket,
        token: str | None = None,
    ) -> User | None:
        if not token:
            if strict:
                raise AppException(status_code=401, detail="Unauthorized: No access token provided", error_code=AppErrorCode.NOT_AUTHENTICATED)
            return None

        user = parse_jwt(token, db, for_type=token_type, strict=strict)
        
        if not user.verified:
            raise AppException(status_code=403, detail="Forbidden: Email not verified", error_code=AppErrorCode.EMAIL_NOT_VERIFIED)

        context_path_params: dict[str, Any] = context.path_params
        body_data: dict[str, Any] = {}
        
        if hasattr(context, "json"):
            try:
                body_data = await context.json()
                # if body_data is not a dict, ignore it
                if not isinstance(body_data, dict):
                    body_data = {}
            except Exception:
                body_data = {}
                
        # merge context_path_params and body_data, path takes precedence
        merged_params = {**body_data, **context_path_params}

        if guards:
            query = select(User).where(User.id == int(user.id))
            for guard in guards:
                query = query.where(guard.clause(user, merged_params, context.query_params))

            user = db.exec(query).first()
            if not user:
                raise AppException(status_code=403, detail="Forbidden: Insufficient permissions", error_code=AppErrorCode.NOT_AUTHORIZED)
        else:
            user = db.get(User, user.id)

        context.state.user = user 
        return user

    async def dependency_ws(
        ws: WebSocket,
        db: Database,
    ) -> User | None:
        token: str | None = ws.cookies.get(f"{token_type}_token")
        return await dependency(db, ws, token)

    async def dependency_http(
        request: Request,
        db: Database,
        token: Annotated[str | None, Depends(oauth2_scheme)],
    ) -> User | None:
        token = token or request.cookies.get(f"{token_type}_token")
        return await dependency(db, request, token)

    # TODO check if try: return dependency_http() except FastApiExceptionThatHappensWhenRequestDependencyIsUsedInWebSocketEndpoint: return dependency_ws() is possible to get rid of the parameter

    return Depends(dependency_ws if endpoint == "ws" else dependency_http)


BasicAuthentication = Annotated[User, Authenticate()]
