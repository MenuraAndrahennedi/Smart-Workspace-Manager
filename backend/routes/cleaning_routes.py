from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.models import User
from backend.dependencies.auth_dependency import require_authenticated_user
from backend.dependencies.database_dependency import get_db
from backend.schemas.cleaning_schema import CleaningRequest, CleaningResultResponse, CleaningSaveResponse
from backend.services.cleaning_service import preview_cleaning, save_cleaning_result

router = APIRouter(
    tags=["Cleaning"],
    prefix="/api/cleaning",
)

@router.post("/{file_id}", response_model=CleaningResultResponse)
def clean_and_get_results(
    file_id: int,
    request: CleaningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    result = preview_cleaning(
        session=db,
        file_id=file_id,
        user_id=current_user.id,
        cleaning_options=request,
    )
    return result.to_api_response()

@router.post("/save_cleaning_results/{file_id}", response_model=CleaningSaveResponse)
def save_results(
    file_id: int,
    request: CleaningRequest,
    date_value: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    preview_result = preview_cleaning(
        session=db,
        file_id=file_id,
        user_id=current_user.id,
        cleaning_options=request,
    )
    return save_cleaning_result(
        session=db,
        file_id=file_id,
        user_id=current_user.id,
        cleaned_dataframe=preview_result.cleaned_dataframe,
        date_value=date_value,
    )

