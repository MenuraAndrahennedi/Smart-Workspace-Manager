from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config.settings import ALGORITHM, SECRET_KEY
from backend.database.models import User
from backend.database.repositories import get_user_by_id
from backend.dependencies.database_dependency import get_db

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
    token: str = Depends(oauth2_scheme), # read bearer token
    db: Session = Depends(get_db),
) -> User:
    try: 
        # Decodes JWT using SECRET_KEY and ALGORITHM
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user = get_user_by_id(db, int(user_id))
        if user is None:
            raise credentials_exception

        return user

    except (JWTError, ValueError):
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
