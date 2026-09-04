from datetime import datetime

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






