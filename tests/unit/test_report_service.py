from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.database.models import Report
from backend.database.repositories import create_file
from backend.services import analysis_service, report_service
from backend.services.report_service import ReportGenerationError, create_report
from backend.services.visualization_service import ChartConfiguration


@pytest.fixture
def report_source(test_session, tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    csv_path = data_root / "sales.csv"
    csv_path.write_text(
        "region,sales\nNorth,10\nSouth,20\nNorth,30\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(report_service, "DATA_ROOT", data_root)
    monkeypatch.setattr(analysis_service, "DATA_ROOT", data_root)

    file_record = create_file(
        session=test_session,
        original_name="sales.csv",
        stored_name="sales.csv",
        extension="csv",
        category="spreadsheets",
        size_bytes=csv_path.stat().st_size,
        storage_path=str(csv_path),
        status="organized",
    )
    return file_record, data_root


def report_charts() -> list[ChartConfiguration]:
    return [
        ChartConfiguration(
            chart_type="bar",
            title="Sales by region",
            x_column="region",
            y_column="sales",
            aggregation="Sum",
        ),
        ChartConfiguration(
            chart_type="histogram",
            title="Sales distribution",
            x_column="sales",
            histogram_bins=5,
        ),
    ]


def test_create_report_saves_html_pdf_and_database_records(
    test_session,
    report_source,
):
    file_record, data_root = report_source

    result = create_report(
        session=test_session,
        file_id=file_record.id,
        chart_configurations=report_charts(),
        date_value=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    html_record = test_session.get(Report, result.html_report_id)
    pdf_record = test_session.get(Report, result.pdf_report_id)
    report_html = result.html_report_path.read_text(encoding="utf-8")

    assert result.source_file_id == file_record.id
    assert result.html_status == "completed"
    assert result.pdf_status == "completed"
    assert result.chart_count == 2
    assert result.html_report_path.parent == data_root / "reports" / "html" / "2026" / "08"
    assert result.pdf_report_path.parent == data_root / "reports" / "pdf" / "2026" / "08"
    assert result.html_report_filename.endswith(".html")
    assert result.pdf_report_filename.endswith(".pdf")
    assert result.pdf_report_path.read_bytes().startswith(b"%PDF")
    assert "sales.csv report" in report_html
    assert "plotly" in report_html.lower()

    assert html_record is not None
    assert html_record.file_id == file_record.id
    assert html_record.report_type == "html"
    assert html_record.storage_path == str(result.html_report_path)
    assert html_record.status == "completed"
    assert pdf_record is not None
    assert pdf_record.file_id == file_record.id
    assert pdf_record.report_type == "pdf"
    assert pdf_record.storage_path == str(result.pdf_report_path)
    assert pdf_record.status == "completed"


def test_create_report_validates_chart_list(
    test_session,
    report_source,
    monkeypatch,
):
    file_record, _ = report_source

    with pytest.raises(ReportGenerationError, match="at least one chart"):
        create_report(
            session=test_session,
            file_id=file_record.id,
            chart_configurations=[],
        )

    monkeypatch.setattr(report_service, "MAX_REPORT_CHARTS", 1)
    with pytest.raises(ReportGenerationError, match="no more than 1 charts"):
        create_report(
            session=test_session,
            file_id=file_record.id,
            chart_configurations=report_charts(),
        )


def test_create_report_wraps_chart_errors_without_creating_record(
    test_session,
    report_source,
):
    file_record, _ = report_source
    invalid_chart = ChartConfiguration(
        chart_type="histogram",
        title="Invalid",
        x_column="region",
    )

    with pytest.raises(ReportGenerationError, match="Chart 1 could not be generated"):
        create_report(
            session=test_session,
            file_id=file_record.id,
            chart_configurations=[invalid_chart],
        )

    assert test_session.scalars(select(Report)).all() == []


def test_create_report_marks_both_records_failed_when_html_write_fails(
    test_session,
    report_source,
    monkeypatch,
):
    file_record, _ = report_source

    def fail_write_text(self, *args, **kwargs):
        raise OSError("Disk unavailable")

    monkeypatch.setattr(Path, "write_text", fail_write_text)

    with pytest.raises(ReportGenerationError, match="could not be saved"):
        create_report(
            session=test_session,
            file_id=file_record.id,
            chart_configurations=report_charts(),
        )

    report_records = test_session.scalars(select(Report)).all()
    assert len(report_records) == 2
    assert all(record.status == "failed" for record in report_records)
    assert all(not Path(record.storage_path).exists() for record in report_records)


def test_create_report_keeps_html_when_pdf_write_fails(
    test_session,
    report_source,
    monkeypatch,
):
    file_record, _ = report_source

    def fail_pdf(*args, **kwargs):
        raise OSError("PDF unavailable")

    monkeypatch.setattr(report_service, "_build_pdf_report", fail_pdf)

    with pytest.raises(ReportGenerationError, match="PDF report could not be saved"):
        create_report(
            session=test_session,
            file_id=file_record.id,
            chart_configurations=report_charts(),
        )

    report_records = test_session.scalars(
        select(Report).order_by(Report.id)
    ).all()
    assert report_records[0].status == "completed"
    assert Path(report_records[0].storage_path).is_file()
    assert report_records[1].status == "failed"
    assert not Path(report_records[1].storage_path).exists()
