def test_preview_cleaning_returns_cleaned_rows(client, uploaded_csv):
    response = client.post(
        f"/api/cleaning/{uploaded_csv['id']}",
        json={
            "remove_duplicates": True,
            "duplicate_columns": ["score", "group"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["original_row_count"] == 3
    assert data["cleaned_row_count"] == 2
    assert data["duplicates_removed"] == 1


def test_save_cleaning_results_creates_csv_and_xlsx_records(
    client,
    uploaded_csv,
    temporary_data_root,
):
    response = client.post(
        f"/api/cleaning/save_cleaning_results/{uploaded_csv['id']}",
        json={
            "remove_duplicates": True,
            "duplicate_columns": ["score", "group"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["csv_file_id"] > 0
    assert data["excel_file_id"] > 0
    assert data["row_count"] == 2
    assert data["column_count"] == 3

    csv_download = client.get(f"/api/files/{data['csv_file_id']}/download")
    xlsx_download = client.get(f"/api/files/{data['excel_file_id']}/download")
    assert csv_download.status_code == 200
    assert xlsx_download.status_code == 200
    assert b"Cara" not in csv_download.content


def test_cleaning_rejects_unknown_duplicate_column(client, uploaded_csv):
    response = client.post(
        f"/api/cleaning/{uploaded_csv['id']}",
        json={
            "remove_duplicates": True,
            "duplicate_columns": ["unknown"],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Bad Request"


def test_cleaning_preview_returns_json_safe_missing_values(client):
    upload_response = client.post(
        "/api/files/upload",
        files={
            "file": (
                "clean-missing.csv",
                b"name,score\nAsha,\n,95\n",
                "text/csv",
            )
        },
    )
    file_id = upload_response.json()["id"]

    response = client.post(
        f"/api/cleaning/{file_id}",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["cleaned_dataframe"] == [
        {"name": "Asha", "score": None},
        {"name": None, "score": 95.0},
    ]
