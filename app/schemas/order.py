from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.data.models.order import OrderStatus, MetalType

class OrderBase(BaseModel):
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    product_description: str
    specifications: Optional[str] = None
    quantity: int = 1
    price: Optional[float] = None
    due_date: Optional[datetime] = None
    metal_type: Optional[MetalType] = None
    target_weight_per_piece: Optional[float] = None
    initial_total_weight: Optional[float] = None

class OrderCreate(OrderBase):
    customer_id: Optional[int] = None

class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    product_description: Optional[str] = None
    specifications: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    status: Optional[OrderStatus] = None
    due_date: Optional[datetime] = None
    metal_type: Optional[MetalType] = None
    target_weight_per_piece: Optional[float] = None
    initial_total_weight: Optional[float] = None

class OrderResponse(OrderBase):
    id: int
    order_number: str
    tenant_id: int
    customer_id: Optional[int] = None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
