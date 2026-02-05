"""
Address schemas for API request/response validation.

This module defines Pydantic schemas for the Address entity in the hierarchical
contact system. Addresses represent physical locations associated with companies
for shipping and billing purposes.

Requirements: 5.5
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class AddressBase(BaseModel):
    """
    Base schema for Address with common fields.
    
    This schema contains fields that are shared across create, update,
    and response operations.
    
    Attributes:
        street_address: Street address line (required)
        city: City name (required)
        state: State or province (required)
        zip_code: Postal/ZIP code (required, minimum 5 characters)
        country: Country name (defaults to 'USA')
        is_default: Whether this is the default address for the company
    
    Requirements: 5.5
    """
    street_address: str = Field(..., min_length=1, max_length=255, description="Street address line")
    city: str = Field(..., min_length=1, max_length=100, description="City name")
    state: str = Field(..., min_length=1, max_length=50, description="State or province")
    zip_code: str = Field(..., min_length=5, max_length=20, description="Postal/ZIP code")
    country: str = Field(default="USA", max_length=100, description="Country name")
    is_default: bool = Field(default=False, description="Whether this is the default address")
    
    @field_validator('street_address', 'city', 'state')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate that address fields are not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError('Address field cannot be empty or just whitespace')
        return v.strip()
    
    @field_validator('zip_code')
    @classmethod
    def validate_zip_code(cls, v: str) -> str:
        """Validate and clean zip code."""
        if not v or not v.strip():
            raise ValueError('ZIP code cannot be empty or just whitespace')
        v = v.strip()
        if len(v) < 5:
            raise ValueError('ZIP code must be at least 5 characters')
        return v
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate and clean country name."""
        if not v or not v.strip():
            raise ValueError('Country cannot be empty or just whitespace')
        return v.strip()


class AddressCreate(AddressBase):
    """
    Schema for creating a new address.
    
    Inherits all fields from AddressBase plus company_id which is required
    for creating an address.
    
    Attributes:
        company_id: Foreign key to the company this address belongs to (required)
    
    Validations:
        - All address fields (street_address, city, state, zip_code) are required
        - ZIP code must be at least 5 characters
        - company_id must be positive
        - All text fields cannot be empty or just whitespace
    
    Requirements: 5.5
    """
    company_id: int = Field(..., gt=0, description="ID of the company this address belongs to")


class AddressUpdate(BaseModel):
    """
    Schema for updating an existing address.
    
    All fields are optional to allow partial updates. If a field is not
    provided, it will not be updated.
    
    Attributes:
        street_address: Updated street address (optional)
        city: Updated city name (optional)
        state: Updated state or province (optional)
        zip_code: Updated postal/ZIP code (optional)
        country: Updated country name (optional)
        is_default: Updated default status (optional)
    
    Requirements: 5.5
    """
    street_address: Optional[str] = Field(None, min_length=1, max_length=255, description="Street address line")
    city: Optional[str] = Field(None, min_length=1, max_length=100, description="City name")
    state: Optional[str] = Field(None, min_length=1, max_length=50, description="State or province")
    zip_code: Optional[str] = Field(None, min_length=5, max_length=20, description="Postal/ZIP code")
    country: Optional[str] = Field(None, max_length=100, description="Country name")
    is_default: Optional[bool] = Field(None, description="Whether this is the default address")
    
    @field_validator('street_address', 'city', 'state', 'country')
    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validate that address fields are not empty or just whitespace if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Address field cannot be empty or just whitespace')
            return v.strip()
        return v
    
    @field_validator('zip_code')
    @classmethod
    def validate_zip_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean zip code if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('ZIP code cannot be empty or just whitespace')
            if len(v) < 5:
                raise ValueError('ZIP code must be at least 5 characters')
            return v
        return v


class CompanySummary(BaseModel):
    """
    Summary schema for Company information in Address responses.
    
    Provides basic company information without full details to avoid
    circular references and reduce response payload size.
    
    Attributes:
        id: Company ID
        name: Company name
    """
    id: int
    name: str
    
    class Config:
        from_attributes = True


class AddressResponse(AddressBase):
    """
    Schema for Address API responses.
    
    Includes all fields from AddressBase plus system-generated fields
    and optional company relationship data.
    
    Attributes:
        id: Address's unique identifier
        tenant_id: Tenant ID for multi-tenant isolation
        company_id: ID of the company this address belongs to
        created_at: Timestamp when address was created
        company: Optional company information (populated when requested)
    
    Requirements: 5.5
    """
    id: int
    tenant_id: int
    company_id: int
    created_at: datetime
    company: Optional[CompanySummary] = None
    
    class Config:
        from_attributes = True


class AddressListResponse(BaseModel):
    """
    Schema for paginated list of addresses.
    
    Used for list endpoints that return multiple addresses with pagination
    metadata.
    
    Attributes:
        addresses: List of address responses
        total: Total number of addresses matching the query
        page: Current page number
        page_size: Number of items per page
    """
    addresses: list[AddressResponse]
    total: int
    page: int = 1
    page_size: int = 50
