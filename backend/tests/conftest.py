# These 3 lines must stay at the top of the file
# fmt: on
import os  # noq: I001
import sys  # noq: I001

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
)
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
# fmt: off

import inspect
from collections.abc import Callable, Generator

import pytest
from _pytest.fixtures import SubRequest
from alembic import command as alembic_command
from alembic.config import Config
from api.dependencies.database import SessionFactory
from api.dependencies.events import EventManager
from api.dependencies.s3 import S3Manager
from core.auth import parse_jwt
from core.logger import get_logger
from factories import models as factory_models
from fastapi.testclient import TestClient
from main import app
from models.tables import User
from sqlmodel import Session

from database import init

# TODO maybe override the Authenticate dependency instead of the inner parse_jwt directly
SessionUser = Callable[[factory_models.UserFactory], User]
@pytest.fixture(scope="function")
def override_session_user(db: Session) -> Generator[SessionUser]:
    """Automatically create a user per test and override the auth dependency."""
    def _create_user(user: User) -> User:
        # Override auth dependency for this test
        app.dependency_overrides[parse_jwt] = lambda: user
        return user

    yield _create_user

    # Cleanup: remove dependency override after test
    app.dependency_overrides.pop(parse_jwt, None)
    

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
    try:
        init.drop_and_recreate_database()
        init.run_alembic_commands("head")
    except Exception as e:
        # Abort tests if database initialization fails
        raise RuntimeError("Failed to initialize test database") from e


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

@pytest.fixture(autouse=True) 
def set_factory_session_auto(db: Session) -> Generator[None]:
    """Automatically set session on all factories."""
    set_session_on_all_factories(db)
    yield
    set_session_on_all_factories(None)
    
def set_session_on_all_factories(session: Session) -> None:
    """Set session on all factory classes."""
    # Get all factory classes
    for _, obj in inspect.getmembers(factory_models):
        if (inspect.isclass(obj) and 
            hasattr(obj, '_meta') and 
            hasattr(obj._meta, 'sqlalchemy_session')):
            obj._meta.sqlalchemy_session = session
