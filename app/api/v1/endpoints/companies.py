from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.data.models.company import Company
from app.data.models.customer import Customer
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyDetailResponse, CustomerSummary

router = APIRouter()

@router.get("/", response_model=List[CompanyResponse])
def list_companies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    companies = db.query(Company).filter(
        Company.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).all()
    return companies

@router.post("/", response_model=CompanyResponse)
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Check if company name already exists for this tenant
    existing = db.query(Company).filter(
        Company.tenant_id == current_user.tenant_id,
        Company.name == company.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Company with this name already exists"
        )
    
    db_company = Company(
        **company.dict(),
        tenant_id=current_user.tenant_id
    )
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    
    return db_company

@router.get("/{company_id}", response_model=CompanyDetailResponse)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.tenant_id == current_user.tenant_id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get customers for this company
    customers = db.query(Customer).filter(Customer.company_id == company_id).all()
    
    customer_summaries = [
        CustomerSummary(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone
        )
        for customer in customers
    ]
    
    return CompanyDetailResponse(
        id=company.id,
        tenant_id=company.tenant_id,
        name=company.name,
        address=company.address,
        phone=company.phone,
        email=company.email,
        created_at=company.created_at,
        updated_at=company.updated_at,
        customers=customer_summaries
    )

@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.tenant_id == current_user.tenant_id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if name is being changed and if it already exists
    if company_update.name and company_update.name != company.name:
        existing = db.query(Company).filter(
            Company.tenant_id == current_user.tenant_id,
            Company.name == company_update.name
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Company with this name already exists"
            )
    
    for key, value in company_update.dict(exclude_unset=True).items():
        setattr(company, key, value)
    
    db.commit()
    db.refresh(company)
    
    return company

@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.tenant_id == current_user.tenant_id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if company has customers
    customer_count = db.query(Customer).filter(Customer.company_id == company_id).count()
    if customer_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete company with associated customers"
        )
    
    db.delete(company)
    db.commit()
    
    return {"message": "Company deleted successfully"}
