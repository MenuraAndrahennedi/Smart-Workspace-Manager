
from backend.database.db import get_db_session


def get_db():
    with get_db_session() as db:
        yield db