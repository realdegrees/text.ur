# fmt: on
import os  # noq: I001
import sys  # noq: I001

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# fmt: off

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from api.dependencies.events import EventManager
from api.routers.comments import router as CommentRouter
from api.routers.documents import router as DocumentsRouter
from api.routers.groups import router as GroupRouter
from api.routers.login import router as LoginRouter
from api.routers.register import router as RegisterRouter
from api.routers.users import router as UserRouter
from core import config
from core.app_exception import AppException
from core.logger import get_logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from models.app_error import AppError
from models.enums import AppErrorCode
from util.api_router import APIRouter
from util.openapi import custom_openapi

routers = [RegisterRouter, LoginRouter, UserRouter, GroupRouter, DocumentsRouter, CommentRouter]

logger = get_logger("requests")
app_logger = get_logger("app")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize on app start."""
    app.state.event_manager = EventManager()
    await app.state.event_manager.connect()
    try:
        yield
    finally:
        await app.state.event_manager.disconnect()
        app.state.event_manager = None


app = FastAPI(
    lifespan=lifespan,
    title="Annotation Software API",
    description="This API allows interfacing with the Annotation Software database",
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
