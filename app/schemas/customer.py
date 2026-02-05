"""
DEPRECATED: Legacy customer schemas.

These schemas are being replaced by Contact schemas as part of the
hierarchical contact system migration. Use app.schemas.contact for all new code.

Migration path: customer schemas -> contact schemas
See: app/schemas/contact.py
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class CustomerBase(BaseModel):
    """DEPRECATED: Use ContactBase instead"""
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company_id: Optional[int] = None

class CustomerCreate(CustomerBase):
    """DEPRECATED: Use ContactCreate instead"""
    pass

class CustomerUpdate(BaseModel):
    """DEPRECATED: Use ContactUpdate instead"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company_id: Optional[int] = None

class CustomerResponse(CustomerBase):
    """DEPRECATED: Use ContactResponse instead"""
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    balance: Optional[float] = 0.0
    
    class Config:
        from_attributes = True

class OrderSummary(BaseModel):
    id: int
    order_number: str
    product_description: str
    quantity: int
    price: Optional[float]
    status: str
    due_date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ShipmentSummary(BaseModel):
    id: int
    order_id: int
    tracking_number: Optional[str]
    carrier: Optional[str]
    shipping_address: Optional[str]
    status: str
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class BalanceBreakdown(BaseModel):
    total: float
    pending: float
    completed: float

class CustomerDetailResponse(CustomerResponse):
    """DEPRECATED: Use ContactResponse with order history instead"""
    orders: List[OrderSummary] = []
    shipments: List[ShipmentSummary] = []
    balance_breakdown: Optional[BalanceBreakdown] = None
    
    class Config:
        from_attributes = True
