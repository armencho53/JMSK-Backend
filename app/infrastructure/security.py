from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import secrets
from app.infrastructure.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def create_refresh_token() -> str:
    """Generate a secure random refresh token"""
    return secrets.token_urlsafe(32)

def get_refresh_token_expires(remember_me: bool = False) -> datetime:
    """Calculate refresh token expiration datetime"""
    days = settings.REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER_ME if remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
    return datetime.utcnow() + timedelta(days=days)

def normalize_email(email: str) -> str:
    """
    Normalize email address by converting to lowercase and stripping whitespace.
    Email addresses are case-insensitive per RFC 5321, so we store them lowercase for consistency.
    """
    return email.strip().lower()
