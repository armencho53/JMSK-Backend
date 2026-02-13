"""
Lookup value schemas for API request/response validation.

This module defines Pydantic schemas for the LookupValue entity,
which represents tenant-scoped configurable enum values stored in the database.

Requirements: 5.9, 5.10
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class LookupValueCreate(BaseModel):
    """
    Schema for creating a new lookup value.

    Attributes:
        category: Category grouping (e.g., "metal_type", "step_type")
        code: UPPER_CASE identifier, auto-uppercased on validation
        display_label: Human-readable label for display
        sort_order: Ordering within category (default 0)
    """
    category: str = Field(..., description="Category grouping for the lookup value")
    code: str = Field(..., description="UPPER_CASE code identifier")
    display_label: str = Field(..., description="Human-readable display label")
    sort_order: int = Field(default=0, description="Sort order within category")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate that code is not empty/whitespace and auto-uppercase."""
        if not v or not v.strip():
            raise ValueError('code must not be empty or whitespace-only')
        return v.strip().upper()

    @field_validator('display_label')
    @classmethod
    def validate_display_label(cls, v: str) -> str:
        """Validate that display_label is not empty/whitespace."""
        if not v or not v.strip():
            raise ValueError('display_label must not be empty or whitespace-only')
        return v.strip()

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate that category is not empty/whitespace."""
        if not v or not v.strip():
            raise ValueError('category must not be empty or whitespace-only')
        return v.strip()


class LookupValueUpdate(BaseModel):
    """
    Schema for updating an existing lookup value.

    All fields are optional. Only display_label, sort_order, and is_active
    can be modified. Code and category are immutable after creation.

    Attributes:
        display_label: Updated display label (optional)
        sort_order: Updated sort order (optional)
        is_active: Updated active status (optional)
    """
    display_label: Optional[str] = Field(None, description="Human-readable display label")
    sort_order: Optional[int] = Field(None, description="Sort order within category")
    is_active: Optional[bool] = Field(None, description="Whether the lookup value is active")

    @field_validator('display_label')
    @classmethod
    def validate_display_label(cls, v: Optional[str]) -> Optional[str]:
        """Validate that display_label is not empty/whitespace if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('display_label must not be empty or whitespace-only')
            return v.strip()
        return v


class LookupValueResponse(BaseModel):
    """
    Schema for lookup value API responses.

    Includes all fields from the LookupValue model.

    Attributes:
        id: Unique identifier
        tenant_id: Tenant ID for multi-tenant isolation
        category: Category grouping
        code: UPPER_CASE code identifier
        display_label: Human-readable display label
        sort_order: Sort order within category
        is_active: Whether the lookup value is active
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    id: int
    tenant_id: int
    category: str
    code: str
    display_label: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
