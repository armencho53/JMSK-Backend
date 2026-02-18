"""Supply tracking schemas for safe purchases, deposits, and transactions"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class SafePurchaseCreate(BaseModel):
    metal_id: Optional[int] = None  # NULL for alloy
    supply_type: str = Field(..., description="FINE_METAL or ALLOY")
    quantity_grams: float = Field(..., gt=0, description="Quantity in grams, must be positive")
    cost_per_gram: float = Field(..., ge=0, description="Cost per gram, must be non-negative")
    notes: Optional[str] = None

    @field_validator('supply_type')
    @classmethod
    def validate_supply_type(cls, v: str) -> str:
        allowed = {"FINE_METAL", "ALLOY"}
        v = v.strip().upper()
        if v not in allowed:
            raise ValueError(f"supply_type must be one of: {', '.join(allowed)}")
        return v


class SafeSupplyResponse(BaseModel):
    id: int
    metal_id: Optional[int]
    supply_type: str
    metal_code: Optional[str] = None
    metal_name: Optional[str] = None
    quantity_grams: float

    class Config:
        from_attributes = True


class MetalTransactionResponse(BaseModel):
    id: int
    transaction_type: str
    metal_id: Optional[int]
    metal_code: Optional[str] = None
    company_id: Optional[int]
    order_id: Optional[int]
    quantity_grams: float
    notes: Optional[str]
    created_at: datetime
    created_by: int

    class Config:
        from_attributes = True


class MetalDepositCreate(BaseModel):
    metal_id: int
    quantity_grams: float = Field(..., gt=0, description="Quantity in grams, must be positive")
    notes: Optional[str] = None


class CompanyMetalBalanceResponse(BaseModel):
    id: int
    metal_id: int
    metal_code: str
    metal_name: str
    balance_grams: float

    class Config:
        from_attributes = True


class CastingConsumptionResult(BaseModel):
    fine_metal_grams: float
    alloy_grams: float
    metal_code: str
    company_id: int
    order_id: int
    company_balance_after: float
    safe_fine_metal_after: float
    safe_alloy_after: float
