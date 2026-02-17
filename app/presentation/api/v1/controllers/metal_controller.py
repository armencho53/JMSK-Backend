"""Metal API controller"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user, require_manager_role
from app.data.models.user import User
from app.schemas.metal import MetalCreate, MetalUpdate, MetalResponse
from app.domain.services.metal_service import MetalService
from app.domain.exceptions import DomainException, DuplicateResourceError

router = APIRouter()


def handle_domain_exception(e: DomainException):
    status_code = e.status_code
    if isinstance(e, DuplicateResourceError):
        status_code = 409
    raise HTTPException(status_code=status_code, detail=e.message)


@router.get("/", response_model=List[MetalResponse])
def list_metals(
    include_inactive: bool = Query(False, description="Include inactive metals"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = MetalService(db)
        return service.get_all(
            tenant_id=current_user.tenant_id,
            include_inactive=include_inactive,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/", response_model=MetalResponse, status_code=status.HTTP_201_CREATED)
def create_metal(
    data: MetalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_role),
):
    try:
        service = MetalService(db)
        return service.create(data, tenant_id=current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{metal_id}", response_model=MetalResponse)
def get_metal(
    metal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = MetalService(db)
        return service.get_by_id(metal_id, tenant_id=current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.put("/{metal_id}", response_model=MetalResponse)
def update_metal(
    metal_id: int,
    data: MetalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_role),
):
    try:
        service = MetalService(db)
        return service.update(metal_id, data, tenant_id=current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.delete("/{metal_id}")
def deactivate_metal(
    metal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_role),
):
    try:
        service = MetalService(db)
        service.deactivate(metal_id, tenant_id=current_user.tenant_id)
        return {"message": "Metal deactivated successfully"}
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/seed")
def seed_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_role),
):
    try:
        service = MetalService(db)
        service.seed_defaults(tenant_id=current_user.tenant_id)
        return {"message": "Default metals seeded successfully"}
    except DomainException as e:
        handle_domain_exception(e)
