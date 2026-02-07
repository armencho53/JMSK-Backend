from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.data.models.order import OrderStatus, MetalType

# Import summary schemas for nested relationships
from app.schemas.company import ContactSummary
from app.schemas.contact import CompanySummary

class OrderBase(BaseModel):
    product_description: str
    specifications: Optional[str] = None
    quantity: int = 1
    price: Optional[float] = None
    due_date: Optional[datetime] = None
    metal_type: Optional[MetalType] = None
    target_weight_per_piece: Optional[float] = None
    initial_total_weight: Optional[float] = None

class OrderCreate(OrderBase):
    contact_id: int  # Required for hierarchical contact system

class OrderUpdate(BaseModel):
    contact_id: Optional[int] = None
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
    contact_id: int
    company_id: int
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    
    # Nested relationship data (Requirements 3.1, 7.3)
    contact: Optional[ContactSummary] = None
    company: Optional[CompanySummary] = None
    
    class Config:
        from_attributes = True
