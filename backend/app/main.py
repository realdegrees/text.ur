# fmt: on
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# fmt: off
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

import api.dependencies.database as db_dep
import uvicorn
from api.dependencies.startup import (
    verify_all_dependencies_async,
)
from api.routers.comments import router as CommentRouter
from api.routers.documents import router as DocumentsRouter
from api.routers.groups import router as GroupRouter
from api.routers.login import router as LoginRouter
from api.routers.logout import router as LogoutRouter
from api.routers.memberships import membership_router as MembershipRouter
from api.routers.register import router as RegisterRouter
from api.routers.sharelinks import root_router as ShareLinkRouter
from api.routers.tags import router as TagRouter
from api.routers.users import router as UserRouter
from core import config
from core.app_exception import AppException
from core.logger import get_current_user, get_logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from models.app_error import AppError
from models.enums import AppErrorCode
from util.api_router import APIRouter
from util.openapi import custom_openapi

routers = [RegisterRouter, LoginRouter, LogoutRouter, UserRouter, MembershipRouter, GroupRouter, ShareLinkRouter, DocumentsRouter, CommentRouter, TagRouter]

logger = get_logger("requests")
app_logger = get_logger("app")

def get_client_ip(request: Request) -> str:
    """Extract client IP from proxy headers or direct connection.

    Checks headers in order:
    1. X-Forwarded-For (set by reverse proxies like Traefik)
    2. X-Real-IP (alternative proxy header)
    3. Direct connection IP (fallback for non-proxied requests)
    """
    # X-Forwarded-For contains comma-separated list, first is original client
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # Fallback to X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Last resort: direct connection (works for non-proxied requests)
    return request.client.host if request.client else "unknown"

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize on app start."""
    app_logger.info("Starting application...")

    # Run all dependency verification using the shared verification function
    try:
        # Await the async verification in lifespan to avoid blocking the event loop
        mgrs = await verify_all_dependencies_async()
        await mgrs["event_manager"].connect()
    except Exception as e:
        app_logger.critical("One or more critical dependencies failed verification. Check logs for details and restart the service.")
        app_logger.error("Error during dependency verification: %s", e, exc_info=True)
        sys.exit(1)

    app_logger.info("Application started successfully")
    try:
        yield
    finally:
        app_logger.info("Shutting down application...")
        await mgrs["event_manager"].disconnect()
        app_logger.info("Application shutdown complete")


app = FastAPI(
    lifespan=lifespan,
    title="Annotation Software API",
    description=(
        "This API allows interfacing with the Annotation Software database.\n\n"
        "## Pagination\n"
        "All list endpoints are paginated and return results in a standardized format with metadata.\n\n"
        "## Filter Exclusions\n"
        "When using equality filters (`==` operator), redundant fields are automatically excluded from responses. "
        "For example, filtering memberships by `user_id == 1` will exclude the full `user` object from each result, "
        "since all results would contain the same user.\n\n"
        "**Note:** Field exclusions only apply to equality filters. Other operators (e.g., `!=`, `>`, `<`) "
        "do not trigger exclusions.\n\n"
        "Filter parameters that support exclusions are marked with a 🚫 indicator in their descriptions below. "
        "The excluded field name is shown in parentheses."
    ),
    openapi_url="/api/openapi.json",
    redirect_slashes=False,
    docs_url=None,  # Swagger doc is manually adjusted at /docs below
    redoc_url=None,  # Redoc is disabled
)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Transform uncaught exceptions into AppException."""
    return JSONResponse(
        status_code=exc.status_code,
        content=AppError(
            status_code=exc.status_code,
            error_code=exc.error_code, 
            detail=exc.detail
        ).model_dump()
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Transform uncaught exceptions into AppException"""
    error_detail: str = str(exc) if config.DEBUG else "Unknown error occurred. Please contact an administrator to check the logs."
    return JSONResponse(
        status_code=400,
        content=AppError(
            status_code=400,
            error_code=AppErrorCode.INVALID_INPUT,
            detail=error_detail
        ).model_dump()
    )
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Transform uncaught exceptions into AppException."""
    error_detail: str = str(exc) if config.DEBUG else "Unknown error occurred. Please contact an administrator to check the logs."
    return JSONResponse(
        status_code=500,
        content=AppError(
            status_code=500,
            error_code=AppErrorCode.UNKNOWN_ERROR,
            detail=error_detail
        ).model_dump()
    )

static_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "static")
)
app.mount("/static", StaticFiles(directory=static_path), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*" if config.DEBUG else config.FRONTEND_BASEURL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log all incoming HTTP requests."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    # Skip logging for static files and health checks
    path = request.url.path
    if not path.startswith("/static"):
        client_ip = get_client_ip(request)
        logger.info(
            "%s %s %s %.2fms",
            request.method,
            path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": path,
                "ip": client_ip,
                "user": get_current_user(),
            },
        )

    return response


router = APIRouter(prefix="/api")

for sub_router in routers:
    if hasattr(sub_router, "websocket_config"):
        websocket_path, websocket_handler = sub_router.websocket_config
        app.websocket("/api" + websocket_path)(websocket_handler)
    router.include_router(sub_router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirects to the Swagger UI."""
    return RedirectResponse(url="/api/docs")


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Health check endpoint for monitoring backend availability."""
    return {"status": "ok"}

@router.get("/docs", include_in_schema=False)
def docs(req: Request) -> HTMLResponse:
    """Return Custom Swagger UI."""
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Annotation Software Docs",
        swagger_ui_parameters={"displayRequestDuration": True, "persistAuthorization": True},
    )
    css: str = """
        <link rel="stylesheet" type="text/css" href="/static/openapi.css">
        </head>
    """
    body: bytes = response.body.replace(b"</head>", css.encode("utf-8"))
    response.body = body
    response.headers["content-length"] = str(len(body))
    return response




app.include_router(router)
app._original_openapi = app.openapi
app.openapi = lambda: custom_openapi(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
