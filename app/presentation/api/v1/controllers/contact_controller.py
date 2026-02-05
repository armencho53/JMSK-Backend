"""Contact API controller"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.schemas.order import OrderResponse
from app.domain.services.contact_service import ContactService
from app.domain.exceptions import DomainException

router = APIRouter()


def handle_domain_exception(e: DomainException):
    """Convert domain exceptions to HTTP exceptions"""
    raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/", response_model=List[ContactResponse])
def list_contacts(
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None, description="Search by name or email"),
    company_id: int = Query(None, description="Filter by company ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all contacts for the current tenant.
    
    Supports optional filtering by company and search by name/email.
    Returns contacts with their associated company information.
    
    Requirements: 1.1, 1.4, 6.1, 6.4
    """
    try:
        service = ContactService(db)
        return service.get_all_contacts(
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit,
            search=search,
            company_id=company_id
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/", response_model=ContactResponse)
def create_contact(
    contact: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new contact.
    
    Requires company_id to establish the company-contact relationship.
    Validates that the company exists and belongs to the same tenant.
    
    Requirements: 1.1, 1.4, 6.1, 6.4
    """
    try:
        service = ContactService(db)
        return service.create_contact(contact, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a single contact by ID.
    
    Returns contact details with associated company information.
    
    Requirements: 1.1, 1.4, 6.1, 6.4
    """
    try:
        service = ContactService(db)
        return service.get_contact_by_id(contact_id, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    contact_update: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing contact.
    
    Validates company-contact relationships if company_id is being changed.
    Checks for duplicate emails within the target company.
    
    Requirements: 1.1, 1.4, 6.1, 6.4
    """
    try:
        service = ContactService(db)
        return service.update_contact(contact_id, contact_update, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.delete("/{contact_id}")
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a contact.
    
    Business rule: Cannot delete contact with existing orders to maintain
    referential integrity and historical data.
    
    Requirements: 1.1, 1.4, 6.1, 6.4
    """
    try:
        service = ContactService(db)
        service.delete_contact(contact_id, current_user.tenant_id)
        return {"message": "Contact deleted successfully"}
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{contact_id}/orders", response_model=List[OrderResponse])
def get_contact_orders(
    contact_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get complete order history for a specific contact.
    
    Returns all orders placed by the contact in chronological order
    (most recent first). This enables tracking individual contact activity
    and viewing their complete transaction history.
    
    Requirements: 3.2, 3.3
    """
    try:
        service = ContactService(db)
        return service.get_contact_order_history(
            contact_id=contact_id,
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit
        )
    except DomainException as e:
        handle_domain_exception(e)
