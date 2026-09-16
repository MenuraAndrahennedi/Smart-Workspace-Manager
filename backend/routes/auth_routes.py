from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.dependencies.database_dependency import get_db
from backend.schemas.auth_schema import RegistrationRequest, TokenResponse
from backend.services.auth_service import (
    UserAlreadyExistsError,
    authenticate_user,
    create_access_token,
    register_user,
)

router = APIRouter(
    tags=["Authentication"],
    prefix="/api/auth"
)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    request: RegistrationRequest,
    db: Session = Depends(get_db),
):
    try:
        user = register_user(
            session=db,
            email=request.email,
            password=request.password,
        )
    except UserAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        session=db,
        email=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
    }

