from pathlib import Path
from sqlite3 import Connection as SQLite3Connection
import sys

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import import_models

import_models()


@pytest.fixture(scope="session")
def engine():
    """Create an isolated in-memory SQLite engine for the test suite."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    """Provide a transactional database session rolled back after each test case."""
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )
    session = TestingSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a default test user record."""
    from app.models.user import User

    user = User(
        email="testuser@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def client(db_session, test_user):
    """FastAPI TestClient authenticated as test_user by default."""
    from app.api.deps import get_current_user

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    def _override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauth_client(db_session):
    """Unauthenticated FastAPI TestClient without current_user override."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
