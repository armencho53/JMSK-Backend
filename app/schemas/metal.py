"""Metal schemas for API request/response validation"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class MetalCreate(BaseModel):
    code: str = Field(..., description="UPPER_CASE metal code identifier")
    name: str = Field(..., description="Human-readable metal name")
    fine_percentage: float = Field(..., description="Purity as decimal 0.0-1.0")
    average_cost_per_gram: Optional[float] = Field(None, description="Average cost per gram")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('code must not be empty or whitespace-only')
        return v.strip().upper()

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('name must not be empty or whitespace-only')
        return v.strip()

    @field_validator('fine_percentage')
    @classmethod
    def validate_fine_percentage(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError('fine_percentage must be between 0.0 and 1.0')
        return v


class MetalUpdate(BaseModel):
    name: Optional[str] = None
    fine_percentage: Optional[float] = None
    average_cost_per_gram: Optional[float] = None
    is_active: Optional[bool] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('name must not be empty or whitespace-only')
            return v.strip()
        return v

    @field_validator('fine_percentage')
    @classmethod
    def validate_fine_percentage(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError('fine_percentage must be between 0.0 and 1.0')
        return v


class MetalResponse(BaseModel):
    id: int
    tenant_id: int
    code: str
    name: str
    fine_percentage: float
    average_cost_per_gram: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
