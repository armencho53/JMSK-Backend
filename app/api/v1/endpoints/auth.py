from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from app.data.database import get_db
from app.infrastructure.security import (
    verify_password,
    create_access_token,
    get_password_hash,
    create_refresh_token,
    get_refresh_token_expires,
    normalize_email
)
from app.infrastructure.config import settings
from app.data.models.user import User
from app.data.models.tenant import Tenant
from app.data.models.refresh_token import RefreshToken
from app.data.models.login_history import LoginHistory
from app.schemas.auth import Token, UserCreate, UserResponse
from app.presentation.api.dependencies import get_current_active_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Normalize email to lowercase
    normalized_email = normalize_email(user_data.email)

    # Check if email already exists (globally unique)
    existing_user = db.query(User).filter(User.email == normalized_email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=normalized_email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        tenant_id=user_data.tenant_id,
        role_id=user_data.role_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Get IP address and user agent for logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Normalize email to lowercase for consistent lookup
    normalized_email = normalize_email(form_data.username)

    # Query user by email (globally unique)
    user = db.query(User).filter(User.email == normalized_email).first()

    # Get tenant (if user exists)
    tenant = None
    if user:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()

    # Check if account is locked
    if user and user.locked_until:
        if user.locked_until > datetime.utcnow():
            # Account is still locked
            minutes_remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1

            # Log failed attempt - account locked
            login_history = LoginHistory(
                user_id=user.id,
                tenant_id=user.tenant_id,
                email=normalized_email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="account_locked"
            )
            db.add(login_history)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Too many failed login attempts. Account locked. Try again in {minutes_remaining} minute(s).",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            # Lockout period has expired, reset lockout fields
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_failed_login = None
            db.commit()

    # Check if tenant is active (only if user exists)
    if user and tenant and not tenant.is_active:
        # Log failed attempt - inactive tenant
        login_history = LoginHistory(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=normalized_email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="inactive_tenant"
        )
        db.add(login_history)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",  # Don't reveal tenant status
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify credentials
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Log failed attempt - invalid credentials (only if user exists)
        if user:
            login_history = LoginHistory(
                user_id=user.id,
                tenant_id=user.tenant_id,
                email=normalized_email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="invalid_credentials"
            )
            db.add(login_history)

            # Increment failed login attempts
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.utcnow()

            # Check if we should lock the account
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)

            db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        # Log failed attempt - inactive user
        login_history = LoginHistory(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=normalized_email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="inactive_user"
        )
        db.add(login_history)
        db.commit()

        raise HTTPException(status_code=400, detail="Inactive user")

    # Successful login - reset lockout fields
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_failed_login = None

    # Log successful login
    login_history = LoginHistory(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=normalized_email,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
        failure_reason=None
    )
    db.add(login_history)

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "tenant_id": user.tenant_id, "user_id": user.id},
        expires_delta=access_token_expires
    )

    # Delete any existing refresh tokens for this user (one token per user policy)
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()

    # Create refresh token (default to remember_me=False for OAuth2 flow)
    refresh_token_value = create_refresh_token()
    refresh_token_expires = get_refresh_token_expires(remember_me=False)

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=refresh_token_expires
    )
    db.add(refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer"
    }

@router.post("/refresh")
def refresh_token(refresh_token: str = Form(...), db: Session = Depends(get_db)):
    """Exchange refresh token for new access token"""
    # Look up refresh token in database
    db_refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if not db_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Check if token is expired
    from datetime import datetime
    if db_refresh_token.expires_at < datetime.utcnow():
        # Delete expired token
        db.delete(db_refresh_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    # Get user and check if active
    user = db.query(User).filter(User.id == db_refresh_token.user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "tenant_id": user.tenant_id, "user_id": user.id},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout user by deleting their refresh token"""
    # Delete all refresh tokens for this user
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()
    db.commit()

    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current logged-in user information"""
    # Add role name to response
    user_dict = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role_id": current_user.role_id,
        "role": current_user.role.name if current_user.role else None,
        "tenant_id": current_user.tenant_id,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }
    return user_dict

@router.get("/login-history")
def get_login_history(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's login history"""
    history = db.query(LoginHistory).filter(
        LoginHistory.user_id == current_user.id
    ).order_by(LoginHistory.timestamp.desc()).limit(limit).all()

    return {
        "history": [
            {
                "id": h.id,
                "email": h.email,
                "ip_address": h.ip_address,
                "user_agent": h.user_agent,
                "success": h.success,
                "failure_reason": h.failure_reason,
                "timestamp": h.timestamp
            }
            for h in history
        ]
    }
