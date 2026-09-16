from pydantic import BaseModel


class PublicSettingsResponse(BaseModel):
    max_upload_size_mb: int
    max_upload_size_bytes: int
    max_filename_length: int
    supported_file_types: list[str]
    file_type_groups: dict[str, list[str]]
    organizer_categories: list[str]
    default_organizer_category: str
    max_csv_analysis_size_mb: int
    max_csv_rows: int
    max_csv_columns: int
    max_chart_rows: int
    max_bar_categories: int
    max_report_charts: int
    valid_aggregations: list[str]
