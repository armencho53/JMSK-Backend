from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.data.models.supply import SupplyType

class SupplyBase(BaseModel):
    name: str
    type: SupplyType
    quantity: float
    unit: str
    cost_per_unit: Optional[float] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None

class SupplyCreate(SupplyBase):
    pass

class SupplyUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[SupplyType] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    cost_per_unit: Optional[float] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None

class SupplyResponse(SupplyBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
