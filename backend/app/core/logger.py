from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from multiprocessing import Queue
from typing import Literal

from core.config import LOG_FILE_DIR

# Context variable to store the current user for request-scoped logging
current_user_context: ContextVar[str | None] = ContextVar("current_user", default=None)

# Global queue and listener for multi-process safe logging
_log_queue: Queue | None = None
_queue_listener: QueueListener | None = None


def set_current_user(user_identifier: str | None) -> None:
    """Set the current user for logging context."""
    current_user_context.set(user_identifier)


def get_current_user() -> str | None:
    """Get the current user from logging context."""
    return current_user_context.get()

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
        # Get user from record extra, or fall back to context variable
        user = getattr(record, "user", None) or get_current_user()

        log_dict = {
            "time": self.formatTime(record, "%d/%b/%Y:%H:%M:%S %z"),
            "level": record.levelname,
            "name": record.name,
            "method": getattr(record, "method", None),
            "ip": getattr(record, "ip", None),
            "path": getattr(record, "path", None),
            "user": user,
            "tags": getattr(record, "tags", None),
            "message": record.getMessage(),
        }
        # Remove None values
        log_dict = {k: v for k, v in log_dict.items() if v is not None}
        return json.dumps(log_dict)


def setup_queue_listener() -> None:
    """Initialize the queue listener for multi-process safe logging.

    Should be called once on application startup (before workers fork).
    """
    global _log_queue, _queue_listener

    if _queue_listener is not None:
        return  # Already initialized

    log_directory = LOG_FILE_DIR if LOG_FILE_DIR else default_log_dir
    os.makedirs(log_directory, exist_ok=True)

    # Create handlers that will actually write logs (used by listener)
    handlers: list[logging.Handler] = []

    # Console handler (always enabled)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s] %(message)s")
    )
    handlers.append(console_handler)

    # File handlers (one per logger name)
    for logger_name in ["requests", "database", "app", "mails", "events", "s3"]:
        file_handler = RotatingFileHandler(
            os.path.join(log_directory, f"{logger_name}.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
        )
        file_handler.setFormatter(JSONFormatter())
        # Add filter to only handle records from this logger
        file_handler.addFilter(lambda record, name=logger_name: record.name == name)
        handlers.append(file_handler)

    # Create queue and listener
    _log_queue = Queue(-1)  # Unlimited size
    _queue_listener = QueueListener(_log_queue, *handlers, respect_handler_level=True)
    _queue_listener.start()


def stop_queue_listener() -> None:
    """Stop the queue listener and clean up resources.

    Should be called on application shutdown.
    """
    global _queue_listener
    if _queue_listener is not None:
        _queue_listener.stop()
        _queue_listener = None


def get_logger(name: Literal["requests", "database", "app", "mails", "events", "s3"]) -> logging.Logger:
    """Return a logger with the specified name.

    When using multiple workers, logs are sent through a queue to a listener
    process that handles file I/O, avoiding file locking issues.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # If queue listener is set up (multi-worker mode), use QueueHandler
    if _log_queue is not None:
        queue_handler = QueueHandler(_log_queue)
        logger.addHandler(queue_handler)
    else:
        # Fallback to direct handlers (single worker mode)
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

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
