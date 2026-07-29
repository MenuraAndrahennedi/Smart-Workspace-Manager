from backend.database.repositories import create_file
from backend.services.dashboard_service import get_dashboard_data


def test_get_dashboard_data_returns_summary_counts_and_recent_files(test_session):
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
        original_name="backup.zip",
        stored_name="stored_backup.zip",
        extension="zip",
        category="others",
        size_bytes=8000,
        storage_path="uploads/backup.zip",
        status="failed",
    )

    dashboard_data = get_dashboard_data(
        session=test_session,
        recent_limit=1,
    )

    assert dashboard_data["total_files"] == 2
    assert dashboard_data["total_size_bytes"] == 9200
    assert dashboard_data["organized_files"] == 1
    assert dashboard_data["failed_files"] == 1
    assert dashboard_data["recent_files"] == [
        {
            "id": second.id,
            "original_name": "backup.zip",
            "stored_name": "stored_backup.zip",
            "extension": "zip",
            "category": "others",
            "size_bytes": 8000,
            "status": "failed",
            "created_at": second.created_at,
            "updated_at": second.updated_at,
        }
    ]
    assert first.id is not None
