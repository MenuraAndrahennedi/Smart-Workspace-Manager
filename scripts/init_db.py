from sqlalchemy import inspect

from backend.database.db import initialize_database, engine
from backend.utils.logging_config import configure_logging



if __name__ == "__main__":
    configure_logging()
    initialize_database()

    inspector = inspect(engine)
    print(f"Schema {inspector.get_schema_names()}")  
    print(f"Tables {inspector.get_table_names()}")


