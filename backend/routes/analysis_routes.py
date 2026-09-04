
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database.models import User
from backend.database.repositories import get_analysis_job_by_id
from backend.dependencies.auth_dependency import require_authenticated_user
from backend.dependencies.database_dependency import get_db
from backend.schemas.analysis_schema import AnalysisJobResponse, AnalysisResponse
from backend.schemas.file_schema import FileResponse
from backend.services.analysis_service import analyze_file_and_record_job, filter_csv_data, get_analyzable_csv_files


router = APIRouter(
    tags=["Analyzer"],
    prefix="/api/analyzer",
)

@router.get("/analyzable_files", response_model=list[FileResponse])
def get_analyzable_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return get_analyzable_csv_files(db, current_user.id)

@router.post("/analysis/{file_id}", response_model=AnalysisResponse, status_code=201)
def get_analysis_result(
    file_id:int,
    preview_rows: int = Query(default=10, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    recorded_analysis = analyze_file_and_record_job(
        session=db,
        file_id=file_id,
        user_id=current_user.id,
        preview_rows=preview_rows,
    )

    return recorded_analysis.to_api_response()


@router.get("/analysis_job/{job_id}", response_model=AnalysisJobResponse)
def get_analysis_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return get_analysis_job_by_id(db, job_id, current_user.id)


@router.get("/files/{file_id}/filter", response_model=list[dict])
def get_filtered_data(
    file_id: int,
    selected_columns: list[str] = Query(...),
    filter_column: str | None = None,
    operator: str | None = None,
    filter_value: Any | None = None,
    maximum_result_rows: int = Query(default=10, gt=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    filtered_data = filter_csv_data(
        session=db,
        file_id=file_id,
        user_id=current_user.id,
        selected_columns=selected_columns,
        filter_column=filter_column,
        operator=operator,
        filter_value=filter_value,
        maximum_result_rows=maximum_result_rows,
    )

    return filtered_data.to_dict(orient="records")

