from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime

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
    metal_id: int
    metal_name: str
    balance_grams: float

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def extract_metal_name(cls, data):
        if hasattr(data, "__dict__"):
            metal = getattr(data, "metal", None)
            obj = {
                "id": getattr(data, "id", None),
                "metal_id": getattr(data, "metal_id", None),
                "metal_name": getattr(metal, "name", "") if metal else "",
                "balance_grams": getattr(data, "balance_grams", 0.0),
            }
            return obj
        return data

class DepartmentWithBalancesResponse(DepartmentResponse):
    balances: List[DepartmentBalanceResponse] = []

    class Config:
        from_attributes = True
