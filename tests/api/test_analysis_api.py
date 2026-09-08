from backend.database.repositories import create_analysis_job, create_file


def test_analyzable_files_returns_owned_organized_csv(client, uploaded_csv):
    response = client.get("/api/analyzer/analyzable_files")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [uploaded_csv["id"]]


def test_create_analysis_and_get_recorded_job(client, uploaded_csv):
    analysis_response = client.post(
        f"/api/analyzer/analysis/{uploaded_csv['id']}",
        params={"preview_rows": 2},
    )

    assert analysis_response.status_code == 201
    analysis = analysis_response.json()
    assert analysis["job_id"] > 0
    assert analysis["result"]["row_count"] == 3
    assert analysis["result"]["column_count"] == 3
    assert len(analysis["result"]["preview"]) == 2

    job_response = client.get(
        f"/api/analyzer/analysis_job/{analysis['job_id']}"
    )

    assert job_response.status_code == 200
    assert job_response.json()["status"] == "completed"
    assert job_response.json()["file_id"] == uploaded_csv["id"]


def test_filter_csv_uses_repeated_query_parameters(client, uploaded_csv):
    response = client.get(
        f"/api/analyzer/files/{uploaded_csv['id']}/filter",
        params=[
            ("selected_columns", "name"),
            ("selected_columns", "score"),
            ("filter_column", "score"),
            ("operator", "Greater than"),
            ("filter_value", "80"),
        ],
    )

    assert response.status_code == 200
    assert response.json() == [
        {"name": "Asha", "score": 95},
        {"name": "Cara", "score": 95},
    ]


def test_analysis_rejects_invalid_preview_count(client, uploaded_csv):
    response = client.post(
        f"/api/analyzer/analysis/{uploaded_csv['id']}",
        params={"preview_rows": 0},
    )

    assert response.status_code == 422


def test_analysis_of_another_users_file_returns_403(
    client,
    test_session,
    other_user,
):
    other_file = create_file(
        session=test_session,
        user_id=other_user.id,
        original_name="private.csv",
        stored_name="private-analysis.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=10,
        storage_path="processed/spreadsheets/private-analysis.csv",
        status="organized",
    )

    response = client.post(f"/api/analyzer/analysis/{other_file.id}")

    assert response.status_code == 403


def test_analysis_job_owned_by_another_user_returns_403(
    client,
    test_session,
    other_user,
):
    other_file = create_file(
        session=test_session,
        user_id=other_user.id,
        original_name="private-job.csv",
        stored_name="private-job-owned.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=10,
        storage_path="processed/spreadsheets/private-job-owned.csv",
        status="organized",
    )
    other_job = create_analysis_job(
        session=test_session,
        file_id=other_file.id,
        user_id=other_user.id,
        status="completed",
    )

    response = client.get(f"/api/analyzer/analysis_job/{other_job.id}")

    assert response.status_code == 403
