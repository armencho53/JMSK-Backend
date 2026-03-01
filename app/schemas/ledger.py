"""Ledger schemas for API request/response validation"""
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import date, datetime


class LedgerEntryCreate(BaseModel):
    date: date
    department_id: int
    order_id: int
    metal_type: str
    direction: Literal["IN", "OUT"]
    quantity: float
    weight: float
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Weight must be positive")
        return v


class LedgerEntryUpdate(BaseModel):
    date: Optional[date] = None
    department_id: Optional[int] = None
    order_id: Optional[int] = None
    metal_type: Optional[str] = None
    direction: Optional[Literal["IN", "OUT"]] = None
    quantity: Optional[float] = None
    weight: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Weight must be positive")
        return v


class LedgerEntryResponse(BaseModel):
    id: int
    tenant_id: int
    date: date
    department_id: int
    order_id: int
    order_number: str
    metal_type: str
    direction: str
    qty_in: Optional[float] = None
    qty_out: Optional[float] = None
    weight_in: Optional[float] = None
    weight_out: Optional[float] = None
    fine_weight: float
    notes: Optional[str] = None
    is_archived: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def map_direction_fields(cls, data):
        """Map direction + quantity/weight into qty_in/qty_out/weight_in/weight_out."""
        # Handle both dict and ORM object attribute access
        if hasattr(data, "__dict__"):
            direction = getattr(data, "direction", None)
            quantity = getattr(data, "quantity", None)
            weight = getattr(data, "weight", None)
            order = getattr(data, "order", None)
            order_number = getattr(order, "order_number", "") if order else ""
            # Convert ORM object to dict for mutation
            obj = {}
            for field in [
                "id", "tenant_id", "date", "department_id", "order_id",
                "metal_type", "direction", "fine_weight", "notes",
                "is_archived", "created_by", "created_at", "updated_at",
            ]:
                obj[field] = getattr(data, field, None)
            obj["order_number"] = order_number
        else:
            direction = data.get("direction")
            quantity = data.get("quantity")
            weight = data.get("weight")
            obj = dict(data)
            if "order_number" not in obj:
                obj["order_number"] = ""

        if direction == "IN":
            obj["qty_in"] = quantity
            obj["qty_out"] = None
            obj["weight_in"] = weight
            obj["weight_out"] = None
        elif direction == "OUT":
            obj["qty_in"] = None
            obj["qty_out"] = quantity
            obj["weight_in"] = None
            obj["weight_out"] = weight

        return obj


class ArchiveRequest(BaseModel):
    date_from: date
    date_to: date


class MetalBalanceItem(BaseModel):
    metal_type: str
    fine_weight_balance: float


class LedgerSummaryResponse(BaseModel):
    total_qty_held: float
    total_qty_out: float
    balances: List[MetalBalanceItem]
