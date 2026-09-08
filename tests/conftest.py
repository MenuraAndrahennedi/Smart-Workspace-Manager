from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from backend.database.db import Base, enable_sqlite_foreign_keys
from backend.database.models import User
from backend.dependencies.auth_dependency import get_current_user
from backend.dependencies.database_dependency import get_db
from backend.main import app


@pytest.fixture
def temporary_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()

    monkeypatch.setattr("backend.config.settings.DATA_ROOT", data_root)

    return data_root


@pytest.fixture
def test_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_session(test_engine) -> Generator[Session, None, None]:
    testing_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(test_session) -> User:
    user = User(
        email="owner@example.com",
        password_hash="not-a-real-password-hash",
    )
    test_session.add(user)
    test_session.flush()
    return user


@pytest.fixture
def other_user(test_session) -> User:
    user = User(
        email="other@example.com",
        password_hash="not-a-real-password-hash",
    )
    test_session.add(user)
    test_session.flush()
    return user


@pytest.fixture
def client(test_session, test_user):
    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(test_session):
    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def uploaded_csv(client, temporary_data_root):
    response = client.post(
        "/api/files/upload",
        files={
            "file": (
                "scores.csv",
                b"name,score,group\nAsha,95,A\nBen,70,B\nCara,95,A\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    return response.json()
