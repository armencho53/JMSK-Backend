from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.data.models.order import OrderStatus, MetalType

# Import summary schemas for nested relationships
# Note: ContactSummary is in company.py, CompanySummary is in contact.py
# to avoid circular imports
from app.schemas.company import ContactSummary
from app.schemas.contact import CompanySummary

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
    contact_id: Optional[int] = None  # New field for hierarchical contact system
    customer_id: Optional[int] = None  # Deprecated: maintained for backward compatibility

class OrderUpdate(BaseModel):
    contact_id: Optional[int] = None  # New field for hierarchical contact system
    customer_id: Optional[int] = None  # Deprecated: maintained for backward compatibility
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
    contact_id: Optional[int] = None  # New field for hierarchical contact system
    company_id: Optional[int] = None  # New field for hierarchical contact system
    customer_id: Optional[int] = None  # Deprecated: maintained for backward compatibility
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    
    # Nested relationship data (Requirements 3.1, 7.3)
    contact: Optional[ContactSummary] = None
    company: Optional[CompanySummary] = None
    
    class Config:
        from_attributes = True
