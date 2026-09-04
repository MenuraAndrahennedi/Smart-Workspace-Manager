from pathlib import Path

from fastapi import APIRouter, Depends

from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database.models import User
from backend.dependencies.auth_dependency import require_authenticated_user
from backend.dependencies.database_dependency import get_db
from backend.schemas.report_schema import CreateReportRequest, ReportResponse, SavedReportResponse
from backend.services.file_service import get_download_path
from backend.services.report_service import create_report, get_saved_report, list_reports_for_file
from backend.services.visualization_service import ChartConfiguration


router = APIRouter(
    tags=["Report"],
    prefix="/api/reports",
)

@router.post("/{file_id}", response_model=SavedReportResponse, status_code=201)
def create_report_for_file(
    file_id: int,
    request: CreateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    result = create_report(
        session=db,
        file_id=file_id,
        user_id=current_user.id,
        chart_configurations=[
            ChartConfiguration(**chart.model_dump())
            for chart in request.chart_configurations
        ],
    )

    return result


@router.get("/files/{file_id}", response_model=list[ReportResponse])
def get_reports_for_a_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return list_reports_for_file(db, file_id, current_user.id)

@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    report = get_saved_report(db, report_id, current_user.id)
    report_path = get_download_path(report.storage_path)

    return FileResponse(
        path=report_path,
        filename=report_path.name,
        media_type="application/pdf" if report.report_type == "pdf" else "text/html",
    )

@router.get("/{report_id}", response_model=ReportResponse)
def get_report_by_id(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return get_saved_report(db, report_id, current_user.id)
