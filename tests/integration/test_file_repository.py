from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.db import Base, enable_sqlite_foreign_keys
from backend.database.repositories import (
    create_file,
    read_file_by_id,
    get_all_files,
    update_file,
    delete_file,
    search_files,
    filter_files_by_category,
    filter_files_by_status,
    query_files,
    count_files,
    get_file_summary,
    group_files_by_category,
    group_files_by_status,
    get_recent_files,
)

def test_file_repository_CRUD(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    enable_sqlite_foreign_keys(engine)

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


def test_file_repository_query_helpers(test_session):
    first = create_file(
        session=test_session,
        original_name="sales_2026.csv",
        stored_name="stored_sales_2026.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=1200,
        storage_path="processed/spreadsheets/sales_2026.csv",
        status="organized",
    )
    second = create_file(
        session=test_session,
        original_name="research_report.pdf",
        stored_name="stored_research_report.pdf",
        extension="pdf",
        category="pdf",
        size_bytes=5000,
        storage_path="processed/pdf/research_report.pdf",
        status="organized",
    )
    third = create_file(
        session=test_session,
        original_name="draft_notes.txt",
        stored_name="stored_draft_notes.txt",
        extension="txt",
        category="documents",
        size_bytes=600,
        storage_path="uploads/draft_notes.txt",
        status="uploaded",
    )

    search_results = search_files(test_session, "report")
    assert [file_record.id for file_record in search_results] == [second.id]
    assert search_files(test_session, "%") == []
    assert [record.id for record in search_files(test_session, "_")] == [
        third.id,
        second.id,
        first.id,
    ]

    category_results = filter_files_by_category(test_session, "spreadsheets")
    assert [file_record.id for file_record in category_results] == [first.id]

    status_results = filter_files_by_status(test_session, "organized")
    assert [file_record.id for file_record in status_results] == [
        second.id,
        first.id,
    ]

    combined_results = query_files(
        test_session,
        search_term="sales",
        category="spreadsheets",
        status="organized",
    )
    assert [file_record.id for file_record in combined_results] == [first.id]

    assert query_files(test_session, category="documents") == [third]

    multi_filter_results = query_files(
        test_session,
        category=["spreadsheets", "pdf"],
        status=["organized"],
    )
    assert [file_record.id for file_record in multi_filter_results] == [
        second.id,
        first.id,
    ]

    assert count_files(test_session) == 3
    assert get_file_summary(test_session) == {
        "total_files": 3,
        "total_size_bytes": 6800,
    }
    assert group_files_by_category(test_session) == [
        {
            "category": "documents",
            "file_count": 1,
            "total_size_bytes": 600,
        },
        {
            "category": "pdf",
            "file_count": 1,
            "total_size_bytes": 5000,
        },
        {
            "category": "spreadsheets",
            "file_count": 1,
            "total_size_bytes": 1200,
        },
    ]
    assert group_files_by_status(test_session) == [
        {
            "status": "organized",
            "file_count": 2,
        },
        {
            "status": "uploaded",
            "file_count": 1,
        },
    ]
    assert [file_record.id for file_record in get_recent_files(test_session, limit=2)] == [
        third.id,
        second.id,
    ]
