from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from jose import jwt
from datetime import timedelta

from backend.database.models import User
from backend.database.repositories import create_user, get_user_by_email
from backend.config.settings import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from backend.utils.time_utils import time_now


password_hash = PasswordHash.recommended()


class UserAlreadyExistsError(ValueError):
    pass

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def normalize_email(email: str) -> str:
    return email.strip().lower()

def register_user(
    session: Session,
    email: str,
    password: str,
) -> User:
    normalized_email = normalize_email(email)

    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    if len(password) > 128:
        raise ValueError("Password cannot contain more than 128 characters.")

    existing_user = get_user_by_email(session, normalized_email)
    if existing_user is not None:
        raise UserAlreadyExistsError("User with this email already exists.")

    return create_user(
        session=session,
        email=normalized_email,
        password_hash=hash_password(password),
    )

def authenticate_user(
    session: Session,
    email: str,
    password: str,
) -> User | None:
    normalized_email = normalize_email(email)

    user = get_user_by_email(session, normalized_email)
    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user

def create_access_token(user: User) -> str:
    expire = time_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": expire,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
