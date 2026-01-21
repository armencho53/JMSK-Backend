from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.data.models.order import MetalType

class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentResponse(DepartmentBase):
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DepartmentBalanceResponse(BaseModel):
    id: int
    metal_type: MetalType
    balance_grams: float

    class Config:
        from_attributes = True

class DepartmentWithBalancesResponse(DepartmentResponse):
    balances: List[DepartmentBalanceResponse] = []

    class Config:
        from_attributes = True
