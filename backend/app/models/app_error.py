from pydantic import BaseModel

from models.enums import AppErrorCode


class AppError(BaseModel):
    """Base class for all custom exceptions in the application."""

    status_code: int
    error_code: AppErrorCode
    detail: str
