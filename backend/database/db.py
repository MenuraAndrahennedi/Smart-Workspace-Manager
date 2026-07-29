from contextlib import contextmanager
import logging

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config.settings import DATABASE_URL

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _set_sqlite_foreign_keys(
    dbapi_connection,
    connection_record,
) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def enable_sqlite_foreign_keys(engine: Engine) -> None:
    if engine.url.get_backend_name() != "sqlite":
        return

    if not event.contains(engine, "connect", _set_sqlite_foreign_keys):
        event.listen(engine, "connect", _set_sqlite_foreign_keys)


# Engine
engine = create_engine(
    DATABASE_URL,
    echo=True,
)
enable_sqlite_foreign_keys(engine)

# Session Factory 
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

@contextmanager
def get_db_session():
    session = SessionLocal()

    try:
        yield session
        session.commit()

    except Exception:
        session.rollback()
        _restore_pending_file_deletions(session)
        raise

    else:
        _finalize_pending_file_deletions(session)

    finally:
        session.close()


def _restore_pending_file_deletions(session: Session) -> None:
    from backend.services.storage_service import (
        PENDING_FILE_DELETIONS_KEY,
        restore_staged_files,
    )

    staged_deletions = session.info.pop(PENDING_FILE_DELETIONS_KEY, [])
    if staged_deletions:
        restore_staged_files(staged_deletions)


def _finalize_pending_file_deletions(session: Session) -> None:
    from backend.services.storage_service import (
        PENDING_FILE_DELETIONS_KEY,
        finalize_staged_files,
    )

    staged_deletions = session.info.pop(PENDING_FILE_DELETIONS_KEY, [])
    if not staged_deletions:
        return

    try:
        finalize_staged_files(staged_deletions)
    except OSError:
        logger.exception(
            "Database deletion committed, but staged files could not be "
            "fully removed."
        )


def initialize_database() -> None:
    from backend.database import models
    Base.metadata.create_all(bind=engine)
