"""Address API controller"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse
from app.domain.services.address_service import AddressService
from app.domain.exceptions import DomainException

router = APIRouter()


def handle_domain_exception(e: DomainException):
    """Convert domain exceptions to HTTP exceptions"""
    raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/companies/{company_id}/addresses", response_model=List[AddressResponse])
def get_company_addresses(
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all addresses for a specific company.
    
    Returns all addresses associated with the company, including
    which one is marked as the default.
    
    Requirements: 5.1, 5.2, 5.3, 5.4
    """
    try:
        service = AddressService(db)
        return service.get_company_addresses(
            company_id=company_id,
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/companies/{company_id}/addresses/default", response_model=Optional[AddressResponse])
def get_default_address(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the default address for a company.
    
    This address is automatically populated during shipment creation.
    Returns null if no default address is set.
    
    Requirements: 5.1, 5.2
    """
    try:
        service = AddressService(db)
        return service.get_default_address(company_id, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/companies/{company_id}/addresses", response_model=AddressResponse)
def create_address(
    company_id: int,
    address: AddressCreate,
    set_as_default: bool = Query(False, description="Set this address as the company's default"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add a new address to a company.
    
    Validates that all required address fields are provided and complete.
    Can optionally set the new address as the company's default.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    try:
        service = AddressService(db)
        return service.create_address(
            company_id=company_id,
            address_data=address,
            tenant_id=current_user.tenant_id,
            set_as_default=set_as_default
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/addresses/{address_id}", response_model=AddressResponse)
def get_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific address by ID.
    
    Requirements: 5.1
    """
    try:
        service = AddressService(db)
        return service.get_address_by_id(address_id, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.put("/addresses/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: int,
    address_update: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a specific address.
    
    Validates that the updated address data is complete and valid.
    Can update the is_default flag to set/unset as default address.
    
    Requirements: 5.1, 5.4, 5.5
    """
    try:
        service = AddressService(db)
        return service.update_address(address_id, address_update, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.delete("/addresses/{address_id}")
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an address.
    
    Business rule: Cannot delete address that is currently set as a
    company's default address. User must set a different default first.
    
    Requirements: 5.1, 5.4
    """
    try:
        service = AddressService(db)
        service.delete_address(address_id, current_user.tenant_id)
        return {"message": "Address deleted successfully"}
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/addresses/{address_id}/set-default", response_model=AddressResponse)
def set_default_address(
    address_id: int,
    company_id: int = Query(..., description="Company ID to verify address ownership"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Set an address as the default for its company.
    
    This address will be automatically populated during shipment creation.
    Only one address can be default per company.
    
    Requirements: 5.2, 5.4
    """
    try:
        service = AddressService(db)
        return service.set_default_address(
            address_id=address_id,
            company_id=company_id,
            tenant_id=current_user.tenant_id
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/companies/{company_id}/addresses/shipment-default")
def get_shipment_address(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get default address for automatic shipment population.
    
    Returns the company's default address in a format suitable for
    populating shipment forms. Returns null if no default address exists.
    
    This endpoint supports the requirement that shipment addresses are
    automatically populated but can be modified for individual shipments.
    
    Requirements: 5.2, 5.3
    """
    try:
        service = AddressService(db)
        return service.populate_shipment_address(company_id, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)
