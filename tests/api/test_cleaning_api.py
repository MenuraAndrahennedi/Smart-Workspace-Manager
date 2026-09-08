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
        json=[
            {"name": "Asha", "score": 95},
            {"name": "Ben", "score": 70},
        ],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["csv_file_id"] > 0
    assert data["excel_file_id"] > 0
    assert data["row_count"] == 2
    assert data["column_count"] == 2

    csv_download = client.get(f"/api/files/{data['csv_file_id']}/download")
    xlsx_download = client.get(f"/api/files/{data['excel_file_id']}/download")
    assert csv_download.status_code == 200
    assert xlsx_download.status_code == 200


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
