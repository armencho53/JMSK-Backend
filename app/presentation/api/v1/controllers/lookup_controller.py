"""Lookup value API controller"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Union
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.schemas.lookup_value import (
    LookupValueCreate,
    LookupValueUpdate,
    LookupValueResponse,
)
from app.domain.services.lookup_service import LookupService
from app.domain.exceptions import DomainException, DuplicateResourceError

router = APIRouter()


def handle_domain_exception(e: DomainException):
    """Convert domain exceptions to HTTP exceptions"""
    status_code = e.status_code
    if isinstance(e, DuplicateResourceError):
        status_code = 409
    raise HTTPException(status_code=status_code, detail=e.message)


@router.get("/", response_model=Union[List[LookupValueResponse], Dict[str, List[LookupValueResponse]]])
def list_lookup_values(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_inactive: bool = Query(False, description="Include inactive values"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List lookup values for the current tenant.

    If category is provided, returns active values filtered by that category,
    ordered by sort_order. If category is omitted, returns all active values
    grouped by category. Use include_inactive=true to include deactivated values.

    Requirements: 5.1, 5.2, 5.8
    """
    try:
        service = LookupService(db)
        if category:
            return service.get_by_category(
                tenant_id=current_user.tenant_id,
                category=category,
                include_inactive=include_inactive,
            )
        else:
            return service.get_all_grouped(
                tenant_id=current_user.tenant_id,
                include_inactive=include_inactive,
            )
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/seed")
def seed_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Seed default lookup values for the current tenant.

    Idempotent — safe to call multiple times without creating duplicates.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    try:
        service = LookupService(db)
        service.seed_defaults(tenant_id=current_user.tenant_id)
        return {"message": "Default lookup values seeded successfully"}
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/", response_model=LookupValueResponse, status_code=status.HTTP_201_CREATED)
def create_lookup_value(
    data: LookupValueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new lookup value for the current tenant.

    The code is auto-uppercased. Returns 409 if a duplicate
    category+code combination already exists for this tenant.

    Requirements: 5.3, 5.4
    """
    try:
        service = LookupService(db)
        return service.create_lookup_value(data, tenant_id=current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.put("/{lookup_id}", response_model=LookupValueResponse)
def update_lookup_value(
    lookup_id: int,
    data: LookupValueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update an existing lookup value.

    Only display_label, sort_order, and is_active can be modified.
    Category and code are immutable after creation.

    Requirements: 5.5, 5.6
    """
    try:
        service = LookupService(db)
        return service.update_lookup_value(
            lookup_id=lookup_id,
            data=data,
            tenant_id=current_user.tenant_id,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.delete("/{lookup_id}")
def delete_lookup_value(
    lookup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Soft delete a lookup value (sets is_active to false).

    The record is preserved for referential integrity with existing
    orders, supplies, and manufacturing steps that reference this value.

    Requirements: 5.7
    """
    try:
        service = LookupService(db)
        service.deactivate_lookup_value(
            lookup_id=lookup_id,
            tenant_id=current_user.tenant_id,
        )
        return {"message": "Lookup value deactivated successfully"}
    except DomainException as e:
        handle_domain_exception(e)
