from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.domain.enums import ShipmentStatus

class ShipmentBase(BaseModel):
    order_id: int
    carrier: Optional[str] = None
    shipping_address: str
    shipping_cost: Optional[float] = None

class ShipmentCreate(ShipmentBase):
    pass

class ShipmentUpdate(BaseModel):
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    shipping_address: Optional[str] = None
    status: Optional[ShipmentStatus] = None
    shipping_cost: Optional[float] = None
    notes: Optional[str] = None

class ShipmentResponse(ShipmentBase):
    id: int
    tenant_id: int
    tracking_number: Optional[str] = None
    status: ShipmentStatus
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
