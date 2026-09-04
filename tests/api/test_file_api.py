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
    assert data["status"] == "uploaded"


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
