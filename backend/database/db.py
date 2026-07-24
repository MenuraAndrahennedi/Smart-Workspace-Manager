from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config.settings import DATABASE_URL

class Base(DeclarativeBase):
    pass


# Engine
engine = create_engine(
    DATABASE_URL,
    echo=True,
)

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
        raise

    finally:
        session.close()

