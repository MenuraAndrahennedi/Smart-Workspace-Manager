from backend.database.repositories import create_file


def test_dashboard_returns_summary(client):
    response = client.get("/api/dashboard/")

    assert response.status_code == 200

    data = response.json()
    assert "total_files" in data
    assert "total_size_bytes" in data
    assert "organized_files" in data
    assert "failed_files" in data
    assert "category_summary" in data
    assert "recent_files" in data


def test_dashboard_returns_file_counts_and_recent_files(client, test_session):
    first_file = create_file(
        session=test_session,
        original_name="sales.csv",
        stored_name="stored_sales.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=1200,
        storage_path="uploads/stored_sales.csv",
        status="organized",
    )
    second_file = create_file(
        session=test_session,
        original_name="notes.txt",
        stored_name="stored_notes.txt",
        extension="txt",
        category="documents",
        size_bytes=800,
        storage_path="uploads/stored_notes.txt",
        status="failed",
    )

    response = client.get("/api/dashboard/")

    assert response.status_code == 200

    data = response.json()
    assert data["total_files"] == 2
    assert data["total_size_bytes"] == 2000
    assert data["organized_files"] == 1
    assert data["failed_files"] == 1
    assert data["recent_files"][0]["id"] == second_file.id
    assert data["recent_files"][1]["id"] == first_file.id
