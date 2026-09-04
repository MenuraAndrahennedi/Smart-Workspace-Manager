from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.models import User
from backend.dependencies.auth_dependency import require_authenticated_user
from backend.dependencies.database_dependency import get_db
from backend.schemas.dashboard_schema import DashboardResponse
from backend.services.dashboard_service import get_dashboard_data


router = APIRouter(
    tags=["Dashboard"],
    prefix="/api/dashboard",
)

@router.get("/", response_model=DashboardResponse)
async def read_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    dashboard_result = get_dashboard_data(db, current_user.id)
    return dashboard_result
 
