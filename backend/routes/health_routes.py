# Check whether the backend is alive and responding.
# GET /health → Backend status check

from fastapi import APIRouter # mMdularize, group, and isolate route operations into separate files or components


router = APIRouter(
    tags=["Health"]
)

@router.get("/health")
def health_check():
    return {"status": "ok"}

