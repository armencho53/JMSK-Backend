from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_id: int
    role_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role_id: Optional[int]
    role: Optional[str] = None  # Role name for frontend
    tenant_id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
