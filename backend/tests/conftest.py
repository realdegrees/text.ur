# These 3 lines must stay at the top of the file
# fmt: on
import os  # noq: I001
import sys  # noq: I001

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
)
# fmt: off

from collections.abc import Generator

import pytest
from _pytest.fixtures import SubRequest
from api.dependencies.database import SessionFactory
from api.dependencies.events import EventManager
from api.dependencies.s3 import S3Manager
from core.logger import get_logger
from fastapi.testclient import TestClient
from main import app
from sqlmodel import Session

logger = get_logger("database")


@pytest.fixture(scope="function")
def s3_client() -> Generator:
    """S3 client fixture for tests using the real S3/MinIO service."""
    client = S3Manager()
    yield client
    
@pytest.fixture(scope="function")
def event_client() -> Generator:
    """Event client fixture for tests using the real Event service."""
    client = EventManager()
    yield client

def pytest_configure(config: pytest.Config) -> None:
    """Add custom markers to pytest configuration."""
    config.addinivalue_line(
        "markers",
        "dependency_overrides: set overrides like auth for the test client",
    )


@pytest.fixture(scope="function")
def client(request: SubRequest) -> Generator[TestClient]:
    """TestClient fixture for pytest.
    
    Attach the dependency_overrides mark with a dict
    [dependency_fn, override_fn] to bypass dependencies like authentication
    """
    # Allows direct overriding of dependencies in tests for the dependency_overrides mark
    marker = request.node.get_closest_marker("dependency_overrides")
    if marker is not None:
        for dependency_fn_name, override_fn in marker.args[0].items():
            app.dependency_overrides[dependency_fn_name] = override_fn
    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def db(request: SubRequest) -> Generator[Session]:
    """Database fixture for pytest."""
    _session = SessionFactory()

    try:
        yield _session
    finally:
        _session.close()
