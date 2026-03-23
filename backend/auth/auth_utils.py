import os

from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone


SECRET_KEY = os.getenv("SECRET_KEY", "super-tajny-klucz-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
password_hash = PasswordHash.recommended()

def get_password_hash(password: str) -> str:
    """Zamienia surowe hasło na bezpieczny skrót."""
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Sprawdza, czy podane hasło pasuje do skrótu z bazy."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Tworzy podpisany token JWT dla użytkownika."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_preauth_token(user_id: int):
    """Tworzy token ważny tylko 5 minut, służący wyłącznie do przejścia do etapu 2FA."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode = {"sub": str(user_id), "type": "preauth", "exp": expire}

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    """Tworzy długowieczny token służący tylko do odświeżania sesji."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
