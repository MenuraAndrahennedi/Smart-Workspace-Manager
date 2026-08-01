from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

from sqlalchemy.orm import Session

from backend.config.settings import DATA_ROOT, MAX_REPORT_CHARTS, time_now
from backend.database.models import FileRecord
from backend.database.repositories import (
    create_report as create_report_record,
    read_file_by_id,
    update_report,
)
from backend.services.analysis_service import load_csv_with_limits
from backend.services.visualization_service import (
    ChartConfiguration,
    GeneratedChart,
    VisualizationError,
    generate_chart,
)
from backend.utils.file_utils import (
    ensure_directory,
    file_exists,
    generate_safe_filename,
)

class ReportGenerationError(Exception):
    pass

@dataclass(frozen=True)
class SavedReportResult:
    source_file_id: int
    html_report_id: int
    pdf_report_id: int
    html_status: str
    pdf_status: str
    html_report_path: Path
    pdf_report_path: Path
    html_report_filename: str
    pdf_report_filename: str
    chart_count: int

def _validate_source_file(file_record: FileRecord | None) -> FileRecord:
    if file_record is None:
        raise ReportGenerationError("The selected file does not exist.")

    if file_record.extension.lstrip(".").lower() != "csv":
        raise ReportGenerationError("The selected file must be a CSV file.")

    if file_record.status.lower() != "organized":
        raise ReportGenerationError("The selected CSV file must be organized.")

    if not file_exists(file_record.storage_path):
        raise ReportGenerationError("The source CSV file does not exist.")

    return file_record


def _generate_report_charts(
    dataframe,
    chart_configurations: list[ChartConfiguration],
) -> list[GeneratedChart]:
    charts: list[GeneratedChart] = []

    for index, configuration in enumerate(chart_configurations, start=1):
        try:
            charts.append(generate_chart(dataframe, configuration))
        except VisualizationError as error:
            raise ReportGenerationError(
                f"Chart {index} could not be generated: {error}"
            ) from error

    return charts


def _build_html_report(
    file_record: FileRecord,
    charts: list[GeneratedChart],
) -> str:
    chart_sections = []
    for index, chart in enumerate(charts):
        chart_sections.append(
            chart.figure.to_html(
                full_html=False,
                include_plotlyjs="cdn" if index == 0 else False,
            )
        )

    return f"""<!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{escape(Path(file_record.original_name).stem)} report</title>
        </head>
        <body>
            <h1>{escape(file_record.original_name)} report</h1>
            {''.join(chart_sections)}
        </body>
        </html>
        """


def _build_pdf_report(
    report_path: Path,
    file_record: FileRecord,
    charts: list[GeneratedChart],
) -> None:
    with PdfPages(
        report_path,
        metadata={"Title": f"{file_record.original_name} report"},
    ) as pdf:
        for chart in charts:
            figure = Figure(figsize=(11, 8.5))
            axis = figure.subplots()

            for trace in chart.figure.data:
                if trace.type == "bar":
                    axis.bar(trace.x, trace.y)
                elif trace.type == "histogram":
                    axis.hist(
                        trace.x,
                        bins=chart.configuration.histogram_bins or 20,
                    )
                elif trace.type == "scatter" and "lines" in (trace.mode or ""):
                    axis.plot(
                        trace.x,
                        trace.y,
                        marker="o" if "markers" in trace.mode else None,
                    )
                elif trace.type == "scatter":
                    axis.scatter(trace.x, trace.y)
                else:
                    raise ReportGenerationError(
                        f"Chart type '{trace.type}' cannot be added to a PDF report."
                    )

            axis.set_title(chart.configuration.title)
            axis.set_xlabel(chart.configuration.x_column or "")
            axis.set_ylabel(chart.configuration.y_column or "Count")
            axis.grid(alpha=0.2)
            figure.text(
                0.5,
                0.02,
                f"Source: {file_record.original_name}",
                ha="center",
                fontsize=9,
            )
            figure.tight_layout(rect=(0.04, 0.05, 0.96, 0.96))
            pdf.savefig(figure)


def create_report(
    session: Session,
    file_id: int,
    chart_configurations: list[ChartConfiguration],
    date_value: datetime | None = None,
) -> SavedReportResult:
    if not chart_configurations:
        raise ReportGenerationError("Add at least one chart before saving the report.")

    if len(chart_configurations) > MAX_REPORT_CHARTS:
        raise ReportGenerationError(f"A report can contain no more than {MAX_REPORT_CHARTS} charts.")

    file_record = read_file_by_id(session, file_id)
    file_record = _validate_source_file(file_record)

    try:
        dataframe = load_csv_with_limits(Path(file_record.storage_path))
    except Exception as error:
        raise ReportGenerationError(
            f"The source CSV could not be loaded: {error}"
        ) from error

    charts = _generate_report_charts(dataframe, chart_configurations)
    report_html = _build_html_report(file_record, charts)

    if date_value is None:
        date_value = time_now()

    html_report_directory = ensure_directory(DATA_ROOT / "reports" / "html" / date_value.strftime("%Y") / date_value.strftime("%m"))
    html_report_filename = generate_safe_filename(f"{Path(file_record.original_name).stem}_report.html")
    html_report_path = html_report_directory / html_report_filename

    pdf_report_directory = ensure_directory(DATA_ROOT / "reports" / "pdf" / date_value.strftime("%Y") / date_value.strftime("%m"))
    pdf_report_filename = generate_safe_filename(f"{Path(file_record.original_name).stem}_report.pdf")
    pdf_report_path = pdf_report_directory / pdf_report_filename

    html_report_record = create_report_record(
        session=session,
        file_id=file_id,
        report_type="html",
        status="pending",
        report_path=str(html_report_path),
    )

    pdf_report_record = create_report_record(
        session=session,
        file_id=file_id,
        report_type="pdf",
        status="pending",
        report_path=str(pdf_report_path),
    )

    try:
        html_report_path.write_text(report_html, encoding="utf-8")
        html_report_record = update_report(
            session=session,
            report_id=html_report_record.id,
            status="completed",
            report_path=str(html_report_path),
        )

    except Exception as error:
        html_report_path.unlink(missing_ok=True)
        update_report(
            session=session,
            report_id=html_report_record.id,
            status="failed",
        )
        update_report(
            session=session,
            report_id=pdf_report_record.id,
            status="failed",
        )
        raise ReportGenerationError("The HTML report could not be saved.") from error

    try:
        _build_pdf_report(pdf_report_path, file_record, charts)
        pdf_report_record = update_report(
            session=session,
            report_id=pdf_report_record.id,
            status="completed",
            report_path=str(pdf_report_path),
        )
    except Exception as error:
        pdf_report_path.unlink(missing_ok=True)
        update_report(
            session=session,
            report_id=pdf_report_record.id,
            status="failed",
        )
        raise ReportGenerationError("The PDF report could not be saved.") from error

    return SavedReportResult(
        source_file_id=file_id,
        html_report_id=html_report_record.id,
        pdf_report_id=pdf_report_record.id,
        html_status=html_report_record.status,
        pdf_status=pdf_report_record.status,
        html_report_path=html_report_path,
        pdf_report_path=pdf_report_path,
        html_report_filename=html_report_filename,
        pdf_report_filename=pdf_report_filename,
        chart_count=len(charts),
    )
