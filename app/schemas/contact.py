"""
Contact schemas for API request/response validation.

This module defines Pydantic schemas for the Contact entity in the hierarchical
contact system. Contacts represent individual people who work for companies and
can place orders on behalf of their companies.

Requirements: 1.1, 1.4, 6.5
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class ContactBase(BaseModel):
    """
    Base schema for Contact with common fields.
    
    This schema contains fields that are shared across create, update,
    and response operations.
    
    Attributes:
        name: Contact's full name (required)
        email: Contact's email address (optional, validated format)
        phone: Contact's phone number (optional)
        company_id: Foreign key to the company this contact belongs to (required)
    """
    name: str = Field(..., min_length=1, max_length=255, description="Contact's full name")
    email: Optional[EmailStr] = Field(None, description="Contact's email address")
    phone: Optional[str] = Field(None, max_length=50, description="Contact's phone number")
    company_id: int = Field(..., gt=0, description="ID of the company this contact belongs to")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError('Name cannot be empty or just whitespace')
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean phone number if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class ContactCreate(ContactBase):
    """
    Schema for creating a new contact.
    
    Inherits all fields from ContactBase. All validations from ContactBase
    apply, including:
    - name is required and cannot be empty
    - company_id is required and must be positive
    - email must be valid format if provided
    
    Requirements: 1.4, 6.5
    """
    pass


class ContactUpdate(BaseModel):
    """
    Schema for updating an existing contact.
    
    All fields are optional to allow partial updates. If a field is not
    provided, it will not be updated.
    
    Attributes:
        name: Updated contact name (optional)
        email: Updated email address (optional)
        phone: Updated phone number (optional)
        company_id: Updated company association (optional)
    
    Requirements: 6.5
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Contact's full name")
    email: Optional[EmailStr] = Field(None, description="Contact's email address")
    phone: Optional[str] = Field(None, max_length=50, description="Contact's phone number")
    company_id: Optional[int] = Field(None, gt=0, description="ID of the company this contact belongs to")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate that name is not empty or just whitespace if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Name cannot be empty or just whitespace')
            return v.strip()
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean phone number if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class CompanySummary(BaseModel):
    """
    Summary schema for Company information in Contact responses.
    
    Provides basic company information without full details to avoid
    circular references and reduce response payload size.
    
    Attributes:
        id: Company ID
        name: Company name
        email: Company email
        phone: Company phone
    """
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    
    class Config:
        from_attributes = True


class ContactResponse(ContactBase):
    """
    Schema for Contact API responses.
    
    Includes all fields from ContactBase plus system-generated fields
    and optional company relationship data.
    
    Attributes:
        id: Contact's unique identifier
        tenant_id: Tenant ID for multi-tenant isolation
        created_at: Timestamp when contact was created
        updated_at: Timestamp when contact was last updated
        company: Optional company information (populated when requested)
    
    Requirements: 1.1, 1.4
    """
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    company: Optional[CompanySummary] = None
    
    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """
    Schema for paginated list of contacts.
    
    Used for list endpoints that return multiple contacts with pagination
    metadata.
    
    Attributes:
        contacts: List of contact responses
        total: Total number of contacts matching the query
        page: Current page number
        page_size: Number of items per page
    """
    contacts: list[ContactResponse]
    total: int
    page: int = 1
    page_size: int = 50
