from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.database.models import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)

credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

forbidden_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this resource",
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    raise credentials_exception

def require_authenticated_user( 
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


# def require_admin_user(
#     current_user = Depends(get_current_user),
# ):
#     if current_user.role != "admin":
#         raise forbidden_exception
#     return current_user
