from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    tenant_id: int
    email: Optional[str] = None
    role_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str]
    role_id: Optional[int]
    role: Optional[str] = None
    tenant_id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
