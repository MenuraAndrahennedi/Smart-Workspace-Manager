import pytest

from backend.database.repositories import (
    create_file,
    get_file_by_id,
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

def test_file_repository_CRUD(test_session, test_user):
        created_file = create_file(
            session=test_session,
            user_id=test_user.id,
            original_name="report.csv",
            stored_name="stored_report.csv",
            extension="csv",
            category="spreadsheet",
            size_bytes=100,
            storage_path="uploads/stored_report.csv",
        )

        assert created_file.id is not None

        read_file = get_file_by_id(test_session, created_file.id, test_user.id)
        assert read_file is not None
        assert read_file.original_name == "report.csv"

        all_files = get_all_files(test_session, test_user.id)
        assert len(all_files) == 1

        updated = update_file(
            session=test_session,
            file_id=created_file.id,
            user_id=test_user.id,
            stored_name="organized_report.csv",
            storage_path="processed/csv/organized_report.csv",
            category="spreadsheet",
            status="organized",
        )

        assert updated is not None
        assert updated.status == "organized"

        deleted_file = delete_file(test_session, created_file.id, test_user.id)
        assert deleted_file is True

        with pytest.raises(FileNotFoundError):
            get_file_by_id(test_session, created_file.id, test_user.id)


def test_file_repository_query_helpers(test_session, test_user):
    first = create_file(
        session=test_session,
        user_id=test_user.id,
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
        user_id=test_user.id,
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
        user_id=test_user.id,
        original_name="draft_notes.txt",
        stored_name="stored_draft_notes.txt",
        extension="txt",
        category="documents",
        size_bytes=600,
        storage_path="uploads/draft_notes.txt",
        status="uploaded",
    )

    search_results = search_files(test_session, test_user.id, "report")
    assert [file_record.id for file_record in search_results] == [second.id]
    assert [
        file_record.id
        for file_record in search_files(test_session, test_user.id, "RESEARCH")
    ] == [second.id]
    assert search_files(test_session, test_user.id, "%") == []
    assert [record.id for record in search_files(test_session, test_user.id, "_")] == [
        third.id,
        second.id,
        first.id,
    ]

    category_results = filter_files_by_category(
        test_session,
        test_user.id,
        "spreadsheets",
    )
    assert [file_record.id for file_record in category_results] == [first.id]

    status_results = filter_files_by_status(
        test_session,
        test_user.id,
        "organized",
    )
    assert [file_record.id for file_record in status_results] == [
        second.id,
        first.id,
    ]

    combined_results = query_files(
        test_session,
        user_id=test_user.id,
        search_term="sales",
        category="spreadsheets",
        status="organized",
    )
    assert [file_record.id for file_record in combined_results] == [first.id]

    assert query_files(
        test_session,
        user_id=test_user.id,
        category="documents",
    ) == [third]

    multi_filter_results = query_files(
        test_session,
        user_id=test_user.id,
        category=["spreadsheets", "pdf"],
        status=["organized"],
    )
    assert [file_record.id for file_record in multi_filter_results] == [
        second.id,
        first.id,
    ]

    assert count_files(test_session, test_user.id) == 3
    assert get_file_summary(test_session, test_user.id) == {
        "total_files": 3,
        "total_size_bytes": 6800,
    }
    assert group_files_by_category(test_session, test_user.id) == [
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
    assert group_files_by_status(test_session, test_user.id) == [
        {
            "status": "organized",
            "file_count": 2,
        },
        {
            "status": "uploaded",
            "file_count": 1,
        },
    ]
    assert [
        file_record.id
        for file_record in get_recent_files(test_session, test_user.id, limit=2)
    ] == [
        third.id,
        second.id,
    ]
