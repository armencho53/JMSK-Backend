from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    resource: str
    action: str

class PermissionCreate(PermissionBase):
    pass

class PermissionResponse(PermissionBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permission_ids: List[int] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None

class RoleResponse(RoleBase):
    id: int
    tenant_id: int
    is_system_role: bool
    permissions: List[PermissionResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RoleListResponse(RoleBase):
    id: int
    tenant_id: int
    is_system_role: bool
    permission_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True
