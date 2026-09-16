from io import BytesIO

import pandas as pd


def _upload_workbook(client):
    workbook = BytesIO()
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        pd.DataFrame(
            {"name": ["Asha", "Ben"], "score": [95, 70]}
        ).to_excel(writer, sheet_name="Scores", index=False)

    return client.post(
        "/api/files/upload",
        files={
            "file": (
                "scores.xlsx",
                workbook.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )


def test_list_sheets_convert_and_download_xlsx_as_csv(
    client,
    temporary_data_root,
):
    upload_response = _upload_workbook(client)
    assert upload_response.status_code == 201
    workbook = upload_response.json()

    list_response = client.get("/api/xlsx/files")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [workbook["id"]]

    sheets_response = client.get(f"/api/xlsx/files/{workbook['id']}/sheets")
    assert sheets_response.status_code == 200
    assert sheets_response.json() == ["Scores"]

    convert_response = client.post(
        f"/api/xlsx/files/{workbook['id']}/convert",
        json={"sheet_name": "Scores"},
    )
    assert convert_response.status_code == 201
    converted = convert_response.json()
    assert converted["extension"] == "csv"
    assert converted["status"] == "organized"

    download_response = client.get(f"/api/files/{converted['id']}/download")
    assert download_response.status_code == 200
    assert b"name,score" in download_response.content


def test_xlsx_conversion_rejects_unknown_sheet(client, temporary_data_root):
    workbook = _upload_workbook(client).json()

    response = client.post(
        f"/api/xlsx/files/{workbook['id']}/convert",
        json={"sheet_name": "Missing"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Bad Request"
