from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.schemas.file_schema import FileResponse

class AnalysisResult(BaseModel):
    preview: list[dict]
    row_count: int
    column_count: int
    columns: list[str]
    data_types: dict[str, str]
    missing_values: dict[str, int]
    duplicate_count: int
    descriptive_statistics: list[dict]

class AnalysisResponse(BaseModel):
    job_id: int
    result: AnalysisResult


class ChartConfigurationRequest(BaseModel):
    chart_type: str
    title: str
    x_column: str | None = None
    y_column: str | None = None
    aggregation: str | None = None
    histogram_bins: int | None = None


class ChartPreviewResponse(BaseModel):
    configuration: ChartConfigurationRequest
    figure: dict[str, Any]
    plotted_row_count: int


from pydantic import BaseModel, ConfigDict

class AnalysisJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int
    status: str
    requested_options: str | None
    summary: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    file: FileResponse






