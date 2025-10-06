import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Literal

from core.config import LOG_FILE_DIR

default_log_dir = log_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "logs")
)


class LoggerExtra(dict):
    """A helper class to add extra information to the logger."""

    def __init__(
        self,
        ip: str | None = None,
        path: str | None = None,
        method: str | None = None,
        user: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Initialize the LoggerExtra object."""
        super().__init__(ip=ip, path=path, method=method, user=user, tags=tags)


class JSONFormatter(logging.Formatter):
    """A custom formatter to format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_dict = {
            "time": self.formatTime(record, "%d/%b/%Y:%H:%M:%S %z"),
            "level": record.levelname,
            "name": record.name,
            "method": getattr(record, "method", None),
            "ip": getattr(record, "ip", None),
            "path": getattr(record, "path", None),
            "user": getattr(record, "user", None),
            "tags": getattr(record, "tags", None),
            "message": record.getMessage(),
        }
        # Remove None values
        log_dict = {k: v for k, v in log_dict.items() if v is not None}
        return json.dumps(log_dict)


def get_logger(name: Literal["requests", "database", "app"]) -> logging.Logger:
    """Return a logger with the specified name."""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    log_directory = LOG_FILE_DIR if LOG_FILE_DIR else default_log_dir

    os.makedirs(log_directory, exist_ok=True)

    file_handler = RotatingFileHandler(
        os.path.join(log_directory, f"{name}.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(JSONFormatter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s] %(message)s")
    )

    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
