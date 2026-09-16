from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.models import User
from backend.database.repositories import get_file_by_id
from backend.dependencies.auth_dependency import require_authenticated_user
from backend.dependencies.database_dependency import get_db
from backend.schemas.file_schema import FileResponse
from backend.schemas.xlsx_schema import XLSXConvertRequest
from backend.services.xlsx_to_csv_service import convert_xlsx_to_csv, get_convertible_xlsx_files, get_xlsx_sheet_names


router = APIRouter(
    tags=["XLSX"],
    prefix="/api/xlsx",
)

@router.get("/files", response_model=list[FileResponse])
def get_convertible_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return get_convertible_xlsx_files(db, current_user.id)

@router.get("/files/{file_id}/sheets", response_model=list[str])
def get_sheet_names(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return get_xlsx_sheet_names(db, file_id, current_user.id)

@router.post("/files/{file_id}/convert", response_model=FileResponse, status_code=201)
def convert_workbook(
    file_id: int,
    request: XLSXConvertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    result = convert_xlsx_to_csv(
        session=db,
        file_id=file_id,
        user_id=current_user.id,
        sheet_name=request.sheet_name,
    )

    return get_file_by_id(db, result.file_id, current_user.id)
