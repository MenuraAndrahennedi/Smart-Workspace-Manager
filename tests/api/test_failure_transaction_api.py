from sqlalchemy import select

from backend.database.models import AnalysisJob, AutomationLog, FileRecord, Report
from backend.services.analysis_service import CSVAnalysisError


def _upload_csv(client):
    return client.post(
        "/api/files/upload",
        files={
            "file": (
                "failure-test.csv",
                b"name,score\nAsha,95\nBen,70\n",
                "text/csv",
            )
        },
    )


def test_analysis_failure_state_survives_request_rollback(
    transactional_client,
    temporary_data_root,
    monkeypatch,
):
    client, session_factory, _ = transactional_client
    uploaded = _upload_csv(client)
    assert uploaded.status_code == 201

    def fail_analysis(*args, **kwargs):
        raise CSVAnalysisError("The CSV could not be analyzed.")

    monkeypatch.setattr(
        "backend.services.analysis_service.analyze_csv",
        fail_analysis,
    )
    response = client.post(
        f"/api/analyzer/analysis/{uploaded.json()['id']}"
    )

    assert response.status_code == 400
    with session_factory() as session:
        job = session.scalar(select(AnalysisJob))
        assert job is not None
        assert job.status == "failed"
        assert job.error_message == "The CSV could not be analyzed."


def test_organization_failure_state_survives_request_rollback(
    transactional_client,
    temporary_data_root,
    monkeypatch,
):
    client, session_factory, _ = transactional_client

    def fail_move(*args, **kwargs):
        raise OSError("Storage move unavailable")

    monkeypatch.setattr(
        "backend.services.automation_service.storage_service.move_file",
        fail_move,
    )
    response = _upload_csv(client)

    assert response.status_code == 500
    with session_factory() as session:
        file_record = session.scalar(select(FileRecord))
        automation_log = session.scalar(select(AutomationLog))
        assert file_record is not None
        assert file_record.status == "failed"
        assert automation_log is not None
        assert automation_log.status == "failed"


def test_partial_report_failure_state_survives_request_rollback(
    transactional_client,
    temporary_data_root,
    monkeypatch,
):
    client, session_factory, _ = transactional_client
    uploaded = _upload_csv(client)
    assert uploaded.status_code == 201

    def fail_pdf(*args, **kwargs):
        raise OSError("PDF renderer unavailable")

    monkeypatch.setattr(
        "backend.services.report_service._build_pdf_report",
        fail_pdf,
    )
    response = client.post(
        f"/api/reports/{uploaded.json()['id']}",
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

    assert response.status_code == 400
    with session_factory() as session:
        reports = list(session.scalars(select(Report).order_by(Report.id)))
        assert [report.report_type for report in reports] == ["html", "pdf"]
        assert [report.status for report in reports] == ["completed", "failed"]
