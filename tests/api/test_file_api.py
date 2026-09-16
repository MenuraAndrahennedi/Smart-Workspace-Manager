def test_list_files_returns_empty_list(client):
    response = client.get("/api/files/")

    assert response.status_code == 200
    assert response.json() == []


def test_upload_file_returns_created_file(client, temporary_data_root):
    response = client.post(
        "/api/files/upload",
        files={
            "file": (
                "report.csv",
                b"name,score\nMenura,95\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] > 0
    assert data["original_name"] == "report.csv"
    assert data["extension"] == "csv"
    assert data["status"] == "organized"


def test_get_file_by_id_returns_uploaded_file(client, temporary_data_root):
    upload_response = client.post(
        "/api/files/upload",
        files={
            "file": (
                "report.csv",
                b"name,score\nMenura,95\n",
                "text/csv",
            )
        },
    )
    uploaded_file = upload_response.json()

    response = client.get(f"/api/files/{uploaded_file['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == uploaded_file["id"]
    assert response.json()["original_name"] == "report.csv"


def test_get_missing_file_returns_404(client):
    response = client.get("/api/files/999999")

    assert response.status_code == 404


def test_delete_file_returns_success_message(client, temporary_data_root):
    upload_response = client.post(
        "/api/files/upload",
        files={
            "file": (
                "report.csv",
                b"name,score\nMenura,95\n",
                "text/csv",
            )
        },
    )
    uploaded_file = upload_response.json()

    response = client.delete(f"/api/files/{uploaded_file['id']}")

    assert response.status_code == 200
    assert response.json() == {
        "id": uploaded_file["id"],
        "message": "File deleted successfully",
    }


def test_upload_invalid_file_returns_400(client, temporary_data_root):
    response = client.post(
        "/api/files/upload",
        files={
            "file": (
                "malware.exe",
                b"bad",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400


def test_list_files_supports_search_category_and_status(client, temporary_data_root):
    client.post(
        "/api/files/upload",
        files={"file": ("sales.csv", b"amount\n10\n", "text/csv")},
    )
    client.post(
        "/api/files/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    response = client.get(
        "/api/files/",
        params={
            "search_term": "sales",
            "category": "spreadsheets",
            "status": "organized",
        },
    )

    assert response.status_code == 200
    assert [item["original_name"] for item in response.json()] == ["sales.csv"]


def test_download_file_returns_original_contents(client, uploaded_csv):
    response = client.get(f"/api/files/{uploaded_csv['id']}/download")

    assert response.status_code == 200
    assert response.content.startswith(b"name,score,group")
    assert 'filename="scores.csv"' in response.headers["content-disposition"]


def test_missing_stored_file_returns_clear_reupload_message(
    client,
    test_session,
    test_user,
    temporary_data_root,
):
    from backend.database.repositories import create_file

    stale_file = create_file(
        session=test_session,
        user_id=test_user.id,
        original_name="missing.csv",
        stored_name="missing-stored.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=10,
        storage_path="processed/spreadsheets/missing-stored.csv",
        status="organized",
    )

    response = client.get(f"/api/files/{stale_file.id}/download")

    assert response.status_code == 409
    assert response.json() == {
        "error": "Stored File Unavailable",
        "message": "The stored file is unavailable; please re-upload it.",
    }


def test_delete_removes_stale_windows_path_record(
    client,
    test_session,
    test_user,
    temporary_data_root,
):
    from backend.database.repositories import create_file

    stale_file = create_file(
        session=test_session,
        user_id=test_user.id,
        original_name="legacy.csv",
        stored_name="legacy-stored.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=10,
        storage_path=r"C:\old-workspace\data\legacy-stored.csv",
        status="organized",
    )
    stale_file_id = stale_file.id

    response = client.delete(f"/api/files/{stale_file_id}")

    assert response.status_code == 200
    assert test_session.get(type(stale_file), stale_file_id) is None


def test_file_owned_by_another_user_returns_403(
    client,
    test_session,
    other_user,
):
    from backend.database.repositories import create_file

    other_file = create_file(
        session=test_session,
        user_id=other_user.id,
        original_name="private.csv",
        stored_name="private-owned.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=10,
        storage_path="processed/spreadsheets/private-owned.csv",
        status="organized",
    )

    response = client.get(f"/api/files/{other_file.id}")

    assert response.status_code == 403
    assert response.json()["error"] == "Forbidden"


def test_protected_file_route_requires_authentication(unauthenticated_client):
    response = unauthenticated_client.get("/api/files/")

    assert response.status_code == 401
