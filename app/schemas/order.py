from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
from app.domain.enums import OrderStatus

# Import summary schemas for nested relationships
from app.schemas.company import ContactSummary
from app.schemas.contact import CompanySummary

class OrderBase(BaseModel):
    product_description: str
    specifications: Optional[str] = None
    quantity: int = 1
    price: Optional[float] = None
    due_date: Optional[datetime] = None
    metal_id: Optional[int] = None
    target_weight_per_piece: Optional[float] = None
    initial_total_weight: Optional[float] = None
    labor_cost: Optional[float] = None

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
    metal_id: Optional[int] = None
    target_weight_per_piece: Optional[float] = None
    initial_total_weight: Optional[float] = None
    labor_cost: Optional[float] = None

class OrderResponse(OrderBase):
    id: int
    order_number: str
    tenant_id: int
    contact_id: int
    company_id: int
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    metal_name: Optional[str] = None
    
    # Nested relationship data (Requirements 3.1, 7.3)
    contact: Optional[ContactSummary] = None
    company: Optional[CompanySummary] = None
    
    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def resolve_metal_name(cls, data):
        """Resolve metal_name from the metal relationship."""
        if hasattr(data, "__dict__"):
            metal = getattr(data, "metal", None)
            if metal and not getattr(data, "metal_name", None):
                # For ORM objects, we need to build a dict-like wrapper
                # that Pydantic can use, but since from_attributes=True
                # handles most fields, we just need to set metal_name
                data.metal_name = getattr(metal, "name", None)
        elif isinstance(data, dict):
            if "metal_name" not in data or data["metal_name"] is None:
                metal = data.get("metal")
                if metal:
                    data["metal_name"] = getattr(metal, "name", None) if hasattr(metal, "name") else None
        return data
