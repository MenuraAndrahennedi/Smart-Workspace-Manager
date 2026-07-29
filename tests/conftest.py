from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.db import Base, enable_sqlite_foreign_keys


@pytest.fixture
def temporary_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()

    monkeypatch.setattr("backend.config.settings.DATA_ROOT", data_root)
    monkeypatch.setattr("backend.services.storage_service.DATA_ROOT", data_root)

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
