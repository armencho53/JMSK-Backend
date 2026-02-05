"""
Company schemas for API request/response validation.

This module defines Pydantic schemas for the Company entity in the hierarchical
contact system. Companies are the parent entities that have multiple contacts
and aggregate balances from all associated orders.

Requirements: 2.1, 4.3
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class CompanyBase(BaseModel):
    """
    Base schema for Company with common fields.
    
    Attributes:
        name: Company name (required)
        address: Company address (optional, legacy field)
        phone: Company phone number (optional)
        email: Company email address (optional)
    """
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    address: Optional[str] = Field(None, description="Company address (legacy field)")
    phone: Optional[str] = Field(None, max_length=50, description="Company phone number")
    email: Optional[EmailStr] = Field(None, description="Company email address")


class CompanyCreate(CompanyBase):
    """
    Schema for creating a new company.
    
    Inherits all fields from CompanyBase.
    """
    pass


class CompanyUpdate(BaseModel):
    """
    Schema for updating an existing company.
    
    All fields are optional to allow partial updates.
    
    Attributes:
        name: Updated company name (optional)
        address: Updated address (optional)
        phone: Updated phone number (optional)
        email: Updated email address (optional)
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Company name")
    address: Optional[str] = Field(None, description="Company address")
    phone: Optional[str] = Field(None, max_length=50, description="Company phone number")
    email: Optional[EmailStr] = Field(None, description="Company email address")


class ContactSummary(BaseModel):
    """
    Summary schema for Contact information in Company responses.
    
    Provides basic contact information without full details to avoid
    circular references and reduce response payload size.
    
    Attributes:
        id: Contact ID
        name: Contact name
        email: Contact email
        phone: Contact phone
    """
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    
    class Config:
        from_attributes = True


class AddressSummary(BaseModel):
    """
    Summary schema for Address information in Company responses.
    
    Provides basic address information for company responses.
    
    Attributes:
        id: Address ID
        street_address: Street address
        city: City name
        state: State or province
        zip_code: Postal/ZIP code
        country: Country name
        is_default: Whether this is the default address
    
    Requirements: 5.1, 5.2
    """
    id: int
    street_address: str
    city: str
    state: str
    zip_code: str
    country: str
    is_default: bool
    
    class Config:
        from_attributes = True


class CompanyResponse(CompanyBase):
    """
    Schema for Company API responses.
    
    Includes all fields from CompanyBase plus system-generated fields
    and optional calculated fields.
    
    Attributes:
        id: Company's unique identifier
        tenant_id: Tenant ID for multi-tenant isolation
        created_at: Timestamp when company was created
        updated_at: Timestamp when company was last updated
        contacts: List of contacts associated with this company (optional)
        addresses: List of addresses for this company (optional)
        total_balance: Calculated total balance from all orders (optional)
    
    Requirements: 2.1, 4.3
    """
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    contacts: Optional[List[ContactSummary]] = None
    addresses: Optional[List[AddressSummary]] = None
    total_balance: Optional[Decimal] = Field(None, description="Total balance from all orders across all contacts")
    
    class Config:
        from_attributes = True


class CustomerSummary(BaseModel):
    """
    Legacy schema for Customer information (being phased out).
    
    Kept for backward compatibility during migration from customer to contact model.
    
    Attributes:
        id: Customer ID
        name: Customer name
        email: Customer email
        phone: Customer phone
    """
    id: int
    name: str
    email: str
    phone: Optional[str]
    
    class Config:
        from_attributes = True


class CompanyDetailResponse(CompanyResponse):
    """
    Detailed schema for Company with all relationships loaded.
    
    Includes legacy customers relationship for backward compatibility.
    Use CompanyResponse with contacts field for new implementations.
    
    Attributes:
        customers: Legacy customer list (being phased out)
    """
    customers: List[CustomerSummary] = []
    
    class Config:
        from_attributes = True
