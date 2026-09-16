from fastapi import APIRouter

from backend.config import settings
from backend.schemas.settings_schema import PublicSettingsResponse
from backend.utils.constants import (
    DEFAULT_ORGANIZER_CATEGORY,
    FILE_TYPE_GROUPS,
    MAX_FILENAME_LENGTH,
    ORGANIZER_CATEGORY_RULES,
    SUPPORTED_FILE_TYPES,
    VALID_AGGREGATIONS,
)


router = APIRouter(
    tags=["Settings"],
    prefix="/api/settings",
)


@router.get("/public", response_model=PublicSettingsResponse)
def get_public_settings():
    return {
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "max_upload_size_bytes": settings.MAX_UPLOAD_SIZE_BYTES,
        "max_filename_length": MAX_FILENAME_LENGTH,
        "supported_file_types": SUPPORTED_FILE_TYPES,
        "file_type_groups": FILE_TYPE_GROUPS,
        "organizer_categories": list(ORGANIZER_CATEGORY_RULES.keys()),
        "default_organizer_category": DEFAULT_ORGANIZER_CATEGORY,
        "max_csv_analysis_size_mb": settings.MAX_CSV_ANALYSIS_SIZE_MB,
        "max_csv_rows": settings.MAX_CSV_ROWS,
        "max_csv_columns": settings.MAX_CSV_COLUMNS,
        "max_chart_rows": settings.MAX_CHART_ROWS,
        "max_bar_categories": settings.MAX_BAR_CATEGORIES,
        "max_report_charts": settings.MAX_REPORT_CHARTS,
        "valid_aggregations": list(VALID_AGGREGATIONS.keys()),
    }
