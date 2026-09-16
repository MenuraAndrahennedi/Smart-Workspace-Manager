from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse as FastAPIFileResponse

from sqlalchemy.orm import Session

from backend.database.models import User
from backend.database.repositories import get_file_by_id
from backend.dependencies.auth_dependency import require_authenticated_user
from backend.dependencies.database_dependency import get_db
from backend.schemas.file_schema import FileDeleteResponse, FileResponse
from backend.services.automation_service import organize_uploaded_file
from backend.services.file_service import delete_actual_file, get_download_path, get_library_files, upload_file


router = APIRouter(
    tags=["Files"],
    prefix="/api/files",
)


@router.get("/", response_model=list[FileResponse])
async def read_all_files(
    search_term: str | None=None,
    category: str | list[str] = Query(default=None),
    status: str | list[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return get_library_files(db, current_user.id, search_term, category, status)


@router.get("/{file_id}", response_model=FileResponse)
async def read_file_by_id(
    file_id:int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    return get_file_by_id(db, file_id, current_user.id)


@router.post("/upload", response_model=FileResponse, status_code=201)
async def create_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    file_bytes = await file.read()
    upload_result = upload_file(
        filename=file.filename,
        file_bytes=file_bytes,
        session=db,
        user_id=current_user.id,
    )

    organize_uploaded_file(
        session=db,
        file_id=upload_result.file_id,
        user_id=current_user.id,
        source_path=Path(upload_result.saved_path),
    )

    return get_file_by_id(db, upload_result.file_id, current_user.id)


@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
    file_id:int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    delete_result = delete_actual_file(db, file_id, current_user.id)

    return {
        "id": delete_result["file_id"],
        "message": "File deleted successfully",
    }


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    file_record = get_file_by_id(db, file_id, current_user.id)
    file_path = get_download_path(file_record.storage_path)

    return FastAPIFileResponse(
        path=file_path,
        filename=file_record.original_name,
    )
