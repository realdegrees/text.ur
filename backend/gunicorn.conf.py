"""Gunicorn configuration file for multi-worker setup with proper logging."""
import logging
import os
import sys
import time

# Add app directory to Python path so we can import core.logger
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from api.dependencies.startup import verify_all_dependencies_sync
from core.logger import setup_queue_listener, stop_queue_listener

# Get gunicorn logger
gunicorn_logger = logging.getLogger("gunicorn.error")

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = int(os.getenv("UVICORN_WORKERS", 4))
worker_class = "uvicorn.workers.UvicornWorker"

# Preload app before forking workers (required for shared queue)
preload_app = True

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Timeout
timeout = 120
keepalive = 5

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None


def on_starting(server) -> None:  # noqa: ANN001
    """Call just before the master process is initialized.

    This runs ONCE in the master process before workers are forked.
    Perfect place to set up the queue listener for multi-process logging.
    """
    server.log.info("Setting up queue listener for multi-process logging")
    setup_queue_listener()
    
    server.log.info("Starting workers with sequential startup coordination")
    # Run lightweight dependency checks in the master process to avoid forking
    # many workers that will all fail when dependencies are down. These checks
    # use synchronous operations to avoid event loop conflicts with async workers.
    try:
        verify_all_dependencies_sync()
    except Exception as e:
        server.log.critical("External dependency verification failed in master; aborting startup: %s", e, exc_info=True)
        sys.exit(1)


def post_worker_init(worker) -> None:  # noqa: ANN001
    """Call just after a worker has initialized the application.

    Stagger worker startup to make logs more readable.
    """
    # Post worker initialization log - worker has started
    gunicorn_logger.info(f"############ Worker online (PID: {worker.pid}) ############")


def on_exit(server) -> None:  # noqa: ANN001
    """Call just before the master process exits.

    Clean up the queue listener.
    """
    server.log.info("Stopping queue listener...")
    stop_queue_listener()


def worker_exit(server, worker) -> None:  # noqa: ANN001
    """Handle a worker exit.

    If a worker exits early with a non-zero exit code (likely due to startup
    failure), abort the master to avoid repeatedly spawning more failing
    workers.
    """
    exitcode = getattr(worker, "exitcode", None)
    if exitcode is None or exitcode == 0:
        return

    worker_age = getattr(worker, "age", 0)
    threshold = int(os.getenv("WORKER_STARTUP_ABORT_THRESHOLD", "10"))
    if worker_age <= threshold:
        server.log.critical(
            "Worker %s (pid=%s) exited early during startup (age=%ss, exitcode=%s). Aborting master.",
            getattr(worker, "pid", "?"),
            getattr(worker, "pid", "?"),
            worker_age,
            exitcode,
        )
        stop_queue_listener()
        sys.exit(1)
