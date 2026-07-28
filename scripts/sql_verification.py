from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.database.db import Base
from backend.database.models import time_now, FileRecord
from backend.database import models
from backend.database.repositories import (
    create_file,
    read_file_by_id,
    get_all_files,
    update_file,
    delete_file,
)


# Definition of INSERT operation to files. Here Values are only placeholders. : means the placeholder in SQLAlchemy text()
# Equal to create_file in repositories.py
INSERT_FILE_SQL = text("""
    INSERT INTO files (
        original_name,
        stored_name,
        extension,
        category,
        size_bytes,
        storage_path,
        status,
        created_at,
        updated_at
    )
    VALUES (
        :original_name,
        :stored_name,
        :extension,
        :category,
        :size_bytes,
        :storage_path,
        :status,
        :created_at,
        :updated_at
    )
""").bindparams(
    bindparam("created_at", type_=DateTime()),
    bindparam("updated_at", type_=DateTime()),
)

# Definition of SELECT operation to files by id. Here Values are only placeholders. : means the placeholder in SQLAlchemy text()
# Equal to read_file_by_id in repositories.py
READ_FILE_BY_ID_SQL = text("""
    SELECT *
    FROM files
    WHERE id = :file_id
""")

# Definition of SELECT operation to all files. Here Values are only placeholders. : means the placeholder in SQLAlchemy text()
# Equal to get_all_files in repositories.py
GET_ALL_FILES_SQL = text("""
    SELECT *
    FROM files
    ORDER BY created_at DESC
""")

# Definition of UPDATE operation to a file. Here Values are only placeholders. : means the placeholder in SQLAlchemy text()
# Equal to update_file in repositories.py
UPDATE_FILE_SQL = text("""
    UPDATE files
    SET
        stored_name = :stored_name,
        storage_path = :storage_path,
        category = :category,
        status = :status,
        updated_at = :updated_at
    WHERE id = :file_id
""").bindparams(
    bindparam("updated_at", type_=DateTime()),
)

# Definition of DELETE operation to a file. Here Values are only placeholders. : means the placeholder in SQLAlchemy text()
# Equal to delete_file in repositories.py
DELETE_FILE_SQL = text("""
    DELETE FROM files
    WHERE id = :file_id
""")



def sql_insert_file(
    session: Session,
    original_name: str,
    stored_name: str,
    extension: str,
    category: str,
    size_bytes: int,
    storage_path: str,
    status: str = "uploaded",
) -> int:
    current_time = time_now()

    parameters = {
        "original_name": original_name,
        "stored_name": stored_name,
        "extension": extension,
        "category": category,
        "size_bytes": size_bytes,
        "storage_path": storage_path,
        "status": status,
        "created_at": current_time,
        "updated_at": current_time,
    }

    result = session.execute(INSERT_FILE_SQL, parameters)
    session.flush()

    if result.lastrowid is None:
        raise RuntimeError("Could not retrieve the inserted file ID.")

    return int(result.lastrowid)


def sql_read_file_by_id(
    session: Session,
    file_id: int
) -> dict | None:
    result = session.execute(READ_FILE_BY_ID_SQL, {"file_id": file_id}) 

    row = result.mappings().first() # Changes the rows into key-value style results, and recieve the first matching row

    return dict(row) if row is not None else None 


def sql_get_all_files(
        session: Session
) -> list[dict]:
    result = session.execute(GET_ALL_FILES_SQL)
    session.flush()

    rows = result.mappings().all()

    return [dict(row) for row in rows]


def sql_update_file(
    session: Session,
    file_id: int,
    stored_name: str,
    storage_path: str,
    category: str,
    status: str,
) -> bool:
    current_time = time_now()
    
    parameters = {
        "file_id": file_id,
        "stored_name": stored_name,
        "category": category,
        "storage_path": storage_path,
        "status": status,
        "updated_at": current_time,
    }

    result = session.execute(UPDATE_FILE_SQL, parameters)
    session.flush()

    return result.rowcount == 1


def sql_delete_file(
    session: Session,
    file_id: int
) -> bool:
    result = session.execute(DELETE_FILE_SQL, {"file_id": file_id})
    session.flush()

    return result.rowcount > 0




def normalise_sql_file(
        file_data: dict | None
) -> dict | None:
    if file_data is None:
        return None

    return {
        "id": file_data["id"],
        "original_name": file_data["original_name"],
        "stored_name": file_data["stored_name"],
        "extension": file_data["extension"],
        "category": file_data["category"],
        "size_bytes": file_data["size_bytes"],
        "storage_path": file_data["storage_path"],
        "status": file_data["status"],
    }


def normalise_orm_file(
    file_record: FileRecord | None
) -> dict | None:
    if file_record is None:
        return None

    return {
        "id": file_record.id,
        "original_name": file_record.original_name,
        "stored_name": file_record.stored_name,
        "extension": file_record.extension,
        "category": file_record.category,
        "size_bytes": file_record.size_bytes,
        "storage_path": file_record.storage_path,
        "status": file_record.status,
    }


def run_crud_verification(db_path: Path | str | None = None) -> bool:
    if db_path is None:
        verification_directory = PROJECT_ROOT / "data" / "SQL_verification"
    else:
        verification_directory = Path(db_path) / "SQL_verification"

    verification_directory.mkdir(parents=True, exist_ok=True)

    VERIFICATION_DB_URL_SQL = (
        f"sqlite:///{verification_directory / 'sql_verification.db'}"
    )
    VERIFICATION_DB_URL_ORM = (
        f"sqlite:///{verification_directory / 'orm_verification.db'}"
    )

    verification_engine_sql = create_engine(
        VERIFICATION_DB_URL_SQL,
        echo=True
    )

    verification_engine_orm = create_engine(
        VERIFICATION_DB_URL_ORM,
        echo=True
    )

    SQLVerificationSession = sessionmaker(
        bind=verification_engine_sql,
        autoflush=False,
        expire_on_commit=False,
    )

    OrmVerificationSession = sessionmaker(
        bind=verification_engine_orm,
        autoflush=False,
        expire_on_commit=False,
    )
    def ensure_verification_database(url: str) -> str:
        if "SQL_verification" not in url and "sql_verification" not in url:
            raise ValueError("Refusing to reset a non-verification database.")
        return url

    ensure_verification_database(VERIFICATION_DB_URL_SQL)
    ensure_verification_database(VERIFICATION_DB_URL_ORM)

    Base.metadata.drop_all(bind=verification_engine_orm)
    Base.metadata.drop_all(bind=verification_engine_sql)

    Base.metadata.create_all(bind=verification_engine_orm)
    Base.metadata.create_all(bind=verification_engine_sql)

    verification_results = {
        "INSERT": False,
        "SELECT BY ID": False,
        "SELECT ALL": False,
        "UPDATE": False,
        "DELETE": False,
    }

    original_name = "verification_file.csv"
    stored_name = "verification_file_001.csv"
    extension = "csv"
    category = "spreadsheets"
    size_bytes = 2048
    storage_path = "uploads/verification_file_001.csv"
    status = "uploaded"

    try:
         with (
            OrmVerificationSession() as orm_session,
            SQLVerificationSession() as sql_session,
        ):
            # Insert verification
            orm_created_file = create_file(
                session=orm_session,
                original_name=original_name,
                stored_name=stored_name,
                extension=extension,
                category=category,
                size_bytes=size_bytes,
                storage_path=storage_path,
                status=status,
            )

            sql_created_file_id = sql_insert_file(
                session=sql_session,
                original_name=original_name,
                stored_name=stored_name,
                extension=extension,
                category=category,
                size_bytes=size_bytes,
                storage_path=storage_path,
                status=status,
            )

            orm_inserted_result = normalise_orm_file(
                read_file_by_id(
                    orm_session,
                    orm_created_file.id,
                )
            )

            sql_inserted_result = normalise_sql_file(
                sql_read_file_by_id(
                    sql_session,
                    sql_created_file_id,
                )
            )

            verification_results["INSERT"] = (
                orm_inserted_result == sql_inserted_result
            )

            # Select by ID varification
            orm_selected_result = normalise_orm_file(
                read_file_by_id(
                    orm_session,
                    orm_created_file.id,
                )
            )

            sql_selected_result = normalise_sql_file(
                sql_read_file_by_id(
                    sql_session,
                    sql_created_file_id,
                )
            )

            verification_results["SELECT BY ID"] = (
                orm_selected_result == sql_selected_result
            )

            # Get all files verification
            orm_all_results = [
                normalise_orm_file(file_record)
                for file_record in get_all_files(orm_session)
            ]

            sql_all_results = [
                normalise_sql_file(file_data)
                for file_data in sql_get_all_files(sql_session)
            ]

            verification_results["SELECT ALL"] = (
                orm_all_results == sql_all_results
            )

            # Update verification
            updated_stored_name = "verification_file_updated.csv"
            updated_storage_path = (
                "processed/spreadsheets/verification_file_updated.csv"
            )
            updated_category = "spreadsheets"
            updated_status = "organized"

            orm_update_result = update_file(
                session=orm_session,
                file_id=orm_created_file.id,
                stored_name=updated_stored_name,
                storage_path=updated_storage_path,
                category=updated_category,
                status=updated_status,
            )

            sql_update_result = sql_update_file(
                session=sql_session,
                file_id=sql_created_file_id,
                stored_name=updated_stored_name,
                storage_path=updated_storage_path,
                category=updated_category,
                status=updated_status,
            )

            orm_updated_file = normalise_orm_file(
                read_file_by_id(
                    orm_session,
                    orm_created_file.id,
                )
            )

            sql_updated_file = normalise_sql_file(
                sql_read_file_by_id(
                    sql_session,
                    sql_created_file_id,
                )
            )

            verification_results["UPDATE"] = (
                orm_update_result is not None
                and sql_update_result is True
                and orm_updated_file == sql_updated_file
            )

            # Delete verification
            orm_delete_result = delete_file(
                session=orm_session,
                file_id=orm_created_file.id,
            )

            sql_delete_result = sql_delete_file(
                session=sql_session,
                file_id=sql_created_file_id,
            )

            orm_deleted_file = read_file_by_id(
                orm_session,
                orm_created_file.id,
            )

            sql_deleted_file = sql_read_file_by_id(
                sql_session,
                sql_created_file_id,
            )

            verification_results["DELETE"] = (
                orm_delete_result is True
                and sql_delete_result is True
                and orm_deleted_file is None
                and sql_deleted_file is None
            )

            # Commit both complete verification workflows.
            orm_session.commit()
            sql_session.commit()

    except Exception as error:
        print(f"\nCRUD verification error: {error}")
        return False


    print("\nSQLAlchemy ORM vs Raw SQL Verification")
    print("-" * 25)

    for operation, passed in verification_results.items():
        result_text = "PASSED" if passed else "FAILED"
        print(f"{operation}: {result_text}")

    all_passed = all(verification_results.values())

    print("-" * 25)
    print(
        "Overall result:",
        "PASSED" if all_passed else "FAILED",
    )

    return all_passed
            

if __name__ == "__main__":
    run_crud_verification()
