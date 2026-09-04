from datetime import datetime

from pydantic import BaseModel, ConfigDict

class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_id: int
    report_type: str
    status: str
    created_at : datetime


class ChartConfigurationRequest(BaseModel):
    chart_type: str
    title: str
    x_column: str | None = None
    y_column: str | None = None
    aggregation: str | None = None
    histogram_bins: int | None = None

class CreateReportRequest(BaseModel):
    chart_configurations: list[ChartConfigurationRequest]

class SavedReportResponse(BaseModel):
    source_file_id: int
    html_report_id: int
    pdf_report_id: int
    html_status: str
    pdf_status: str
    html_report_filename: str
    pdf_report_filename: str
    chart_count: int