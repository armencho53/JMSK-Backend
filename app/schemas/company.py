from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class CompanyBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class CompanyResponse(CompanyBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CustomerSummary(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    
    class Config:
        from_attributes = True

class CompanyDetailResponse(CompanyResponse):
    customers: List[CustomerSummary] = []
    
    class Config:
        from_attributes = True
