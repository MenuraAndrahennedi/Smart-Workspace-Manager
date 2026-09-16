from pydantic import BaseModel

from backend.schemas.file_schema import FileResponse


class CategorySummaryResponse(BaseModel):
    category: str
    file_count: int
    total_size_bytes: int

class DashboardResponse(BaseModel):
    total_files: int
    total_size_bytes: int
    organized_files: int
    failed_files: int
    category_summary: list[CategorySummaryResponse]
    recent_files: list[FileResponse]