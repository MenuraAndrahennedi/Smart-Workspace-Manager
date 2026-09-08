from backend.database.repositories import create_file, create_report


def _create_report(client, file_id):
    return client.post(
        f"/api/reports/{file_id}",
        json={
            "chart_configurations": [
                {
                    "chart_type": "histogram",
                    "title": "Score distribution",
                    "x_column": "score",
                    "histogram_bins": 5,
                }
            ]
        },
    )


def test_create_list_get_and_download_reports(client, uploaded_csv):
    create_response = _create_report(client, uploaded_csv["id"])

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["html_status"] == "completed"
    assert created["pdf_status"] == "completed"
    assert created["chart_count"] == 1

    list_response = client.get(f"/api/reports/files/{uploaded_csv['id']}")
    assert list_response.status_code == 200
    assert {report["id"] for report in list_response.json()} == {
        created["html_report_id"],
        created["pdf_report_id"],
    }

    get_response = client.get(f"/api/reports/{created['html_report_id']}")
    assert get_response.status_code == 200
    assert get_response.json()["report_type"] == "html"

    html_download = client.get(
        f"/api/reports/{created['html_report_id']}/download"
    )
    pdf_download = client.get(
        f"/api/reports/{created['pdf_report_id']}/download"
    )
    assert html_download.status_code == 200
    assert html_download.headers["content-type"].startswith("text/html")
    assert pdf_download.status_code == 200
    assert pdf_download.headers["content-type"].startswith("application/pdf")


def test_report_requires_at_least_one_chart(client, uploaded_csv):
    response = client.post(
        f"/api/reports/{uploaded_csv['id']}",
        json={"chart_configurations": []},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "Bad Request"


def test_get_missing_report_returns_404(client):
    response = client.get("/api/reports/999999")

    assert response.status_code == 404


def test_report_owned_by_another_user_returns_403(
    client,
    test_session,
    other_user,
):
    other_file = create_file(
        session=test_session,
        user_id=other_user.id,
        original_name="private-report.csv",
        stored_name="private-report-source.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=10,
        storage_path="processed/spreadsheets/private-report-source.csv",
        status="organized",
    )
    other_report = create_report(
        session=test_session,
        file_id=other_file.id,
        user_id=other_user.id,
        report_type="html",
        status="completed",
        report_path="reports/html/private-report.html",
    )

    response = client.get(f"/api/reports/{other_report.id}")

    assert response.status_code == 403
