"""API dependencies for dependency injection"""
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.data.database import get_db
from app.infrastructure.security import decode_access_token
from app.data.models.user import User

# Determine token URL based on environment
IS_LAMBDA = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
STAGE = os.getenv("STAGE", "prod")
TOKEN_URL = f"/{STAGE}/api/v1/auth/login" if IS_LAMBDA else "/api/v1/auth/login"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=TOKEN_URL, auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check if token is provided
    if token is None:
        raise credentials_exception
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    tenant_id: int = payload.get("tenant_id")
    
    if email is None or tenant_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(
        User.email == email,
        User.tenant_id == tenant_id
    ).first()
    
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is active"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_manager_role(current_user: User = Depends(get_current_active_user)) -> User:
    """Ensure current user has manager or admin role"""
    allowed_roles = {"manager", "admin"}
    if not current_user.role or current_user.role.name.lower() not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or admin role required",
        )
    return current_user
