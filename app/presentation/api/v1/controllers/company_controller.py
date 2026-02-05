"""Company API controller"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, ContactSummary
from app.schemas.order import OrderResponse
from app.domain.services.company_service import CompanyService
from app.domain.exceptions import DomainException

router = APIRouter()


def handle_domain_exception(e: DomainException):
    """Convert domain exceptions to HTTP exceptions"""
    raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/", response_model=List[CompanyResponse])
def list_companies(
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None, description="Search by company name"),
    include_balance: bool = Query(False, description="Include aggregated balance"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all companies for the current tenant.
    
    Supports optional search by name and can include aggregated balance
    calculated from all orders across all contacts.
    
    Requirements: 6.1, 6.4
    """
    try:
        service = CompanyService(db)
        return service.get_all_companies(
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit,
            search=search,
            include_balance=include_balance
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/", response_model=CompanyResponse)
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new company.
    
    Validates that no duplicate company name exists within the tenant.
    
    Requirements: 6.1, 6.4
    """
    try:
        service = CompanyService(db)
        return service.create_company(company, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    include_contacts: bool = Query(False, description="Include list of contacts"),
    include_balance: bool = Query(True, description="Include aggregated balance"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a single company by ID.
    
    Can optionally include the list of associated contacts and/or
    the aggregated balance from all orders.
    
    Requirements: 6.1, 6.4
    """
    try:
        service = CompanyService(db)
        return service.get_company_by_id(
            company_id=company_id,
            tenant_id=current_user.tenant_id,
            include_contacts=include_contacts,
            include_balance=include_balance
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing company.
    
    Validates that if name is being changed, no duplicate exists.
    
    Requirements: 6.1, 6.4
    """
    try:
        service = CompanyService(db)
        return service.update_company(company_id, company_update, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a company.
    
    Business rule: Cannot delete company with existing contacts due to
    cascade constraints and data integrity requirements.
    
    Requirements: 6.1, 6.4
    """
    try:
        service = CompanyService(db)
        service.delete_company(company_id, current_user.tenant_id)
        return {"message": "Company deleted successfully"}
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{company_id}/contacts", response_model=List[ContactSummary])
def get_company_contacts(
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all contacts for a specific company.
    
    Returns a list of all individuals associated with the company.
    
    Requirements: 2.1, 4.1, 4.2, 4.3
    """
    try:
        service = CompanyService(db)
        return service.get_company_contacts(
            company_id=company_id,
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{company_id}/orders", response_model=List[OrderResponse])
def get_company_orders(
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    group_by_contact: bool = Query(False, description="Group orders by contact"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all orders for a company across all contacts.
    
    Returns orders in chronological order (most recent first). Can optionally
    group by contact for display purposes.
    
    Requirements: 2.1, 4.1, 4.2, 4.3
    """
    try:
        service = CompanyService(db)
        return service.get_company_orders(
            company_id=company_id,
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit,
            group_by_contact=group_by_contact
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{company_id}/balance")
def get_company_balance(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get aggregated balance for a company.
    
    Calculates the sum of all order values from all contacts associated
    with the company. This is the primary balance calculation that reflects
    total business value per company.
    
    Requirements: 2.1, 4.1, 4.2, 4.3
    """
    try:
        service = CompanyService(db)
        balance = service.get_company_balance(company_id, current_user.tenant_id)
        return {
            "company_id": company_id,
            "total_balance": float(balance)
        }
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{company_id}/statistics")
def get_company_statistics(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive statistics for a company.
    
    Returns aggregated metrics including total balance, contact count,
    order count, and average order value.
    
    Requirements: 4.3
    """
    try:
        service = CompanyService(db)
        return service.get_company_statistics(company_id, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)
