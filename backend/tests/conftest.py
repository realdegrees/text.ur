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
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any

import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest
from alembic import command as alembic_command
from alembic.config import Config
from api.dependencies.database import SessionFactory, session
from api.dependencies.events import EventManager
from api.dependencies.s3 import S3Manager
from core.auth import parse_jwt
from core.config import DATABASE_URL, DB_CONNECTION_TIMEOUT
from core.logger import get_logger
from factories import models as factory_models
from httpx import AsyncClient
from main import app
from models.tables import User
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from database import init

# TODO maybe override the Authenticate dependency instead of the inner parse_jwt directly
SessionUser = Callable[[factory_models.UserFactory], User]
@pytest_asyncio.fixture(scope="function")
async def override_session_user(db: SQLModelAsyncSession) -> AsyncGenerator[SessionUser, None]:
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


@pytest_asyncio.fixture(scope="function")
async def client(request: SubRequest) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient fixture for pytest.

    Attach the dependency_overrides mark with a dict
    [dependency_fn, override_fn] to bypass dependencies like authentication
    """
    # Allows direct overriding of dependencies in tests for the dependency_overrides mark
    marker = request.node.get_closest_marker("dependency_overrides")
    if marker is not None:
        for dependency_fn_name, override_fn in marker.args[0].items():
            app.dependency_overrides[dependency_fn_name] = override_fn

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def db(request: SubRequest) -> AsyncGenerator[SQLModelAsyncSession, None]:
    """Database fixture for pytest.
    
    Creates a new async engine and session for each test to avoid
    event loop conflicts when using pytest-asyncio.
    """
    # Create a test-specific engine for this test's event loop
    test_engine: AsyncEngine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"timeout": DB_CONNECTION_TIMEOUT},
    )
    
    # Create session factory with the test engine
    test_session_factory = sessionmaker(
        bind=test_engine,
        class_=SQLModelAsyncSession,
        expire_on_commit=False,
    )
    
    async with test_session_factory() as _session:
        # Override the session dependency to use this test session
        async def get_test_db() -> AsyncGenerator[SQLModelAsyncSession, None]:
            yield _session

        app.dependency_overrides[session] = get_test_db

        try:
            yield _session
        finally:
            # Rollback any uncommitted changes
            await _session.rollback()
            app.dependency_overrides.pop(session, None)
    
    # Clean up the test engine
    await test_engine.dispose()

@pytest_asyncio.fixture(autouse=True)
async def set_factory_session_auto(db: SQLModelAsyncSession) -> AsyncGenerator[None, None]:
    """Automatically set session on all factories.
    
    We use run_sync to run the factory creation in a greenlet context,
    which allows the sync session to work with the async database.
    """    
    # Get all factory classes from the factories.models module
    factory_classes = [
        getattr(factory_models, attr)
        for attr in dir(factory_models)
        if attr.endswith("Factory") and hasattr(getattr(factory_models, attr), "_meta")
    ]
    
    # Set the sync session from the async session on all factories
    # Use the sync_session which works within greenlets
    for factory_cls in factory_classes:
        factory_cls._meta.sqlalchemy_session = db.sync_session
    
    yield
    
    # Clean up
    for factory_cls in factory_classes:
        factory_cls._meta.sqlalchemy_session = None
