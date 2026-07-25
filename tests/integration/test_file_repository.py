from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.db import Base
from backend.database.repositories import (
    create_file,
    read_file_by_id,
    get_all_files,
    update_file,
    delete_file
)

def test_file_repository_CRUD(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")

    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with TestingSession() as session:
        created_file = create_file(
            session=session,
            original_name="report.csv",
            stored_name="stored_report.csv",
            extension="csv",
            category="spreadsheet",
            size_bytes=100,
            storage_path="uploads/stored_report.csv",
        )

        assert created_file.id is not None

        read_file = read_file_by_id(session, created_file.id)
        assert read_file is not None
        assert read_file.original_name == "report.csv"

        all_files = get_all_files(session)
        assert len(all_files) == 1

        updated = update_file(
            session=session,
            file_id=created_file.id,
            stored_name="organized_report.csv",
            storage_path="processed/csv/organized_report.csv",
            category="spreadsheet",
            status="organized",
        )

        assert updated is not None
        assert updated.status == "organized"

        deleted_file = delete_file(session, created_file.id)
        assert deleted_file is True

        missing_file = read_file_by_id(session, created_file.id)
        assert missing_file is None