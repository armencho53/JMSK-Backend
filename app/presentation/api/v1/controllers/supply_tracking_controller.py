"""Supply tracking API controller for safe purchases and transactions"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user, require_manager_role
from app.data.models.user import User
from app.schemas.supply_tracking import (
    SafePurchaseCreate,
    SafeSupplyResponse,
    MetalTransactionResponse,
    MetalDepositCreate,
    CompanyMetalBalanceResponse,
)
from app.domain.services.supply_tracking_service import SupplyTrackingService
from app.domain.exceptions import DomainException, DuplicateResourceError

router = APIRouter()


def handle_domain_exception(e: DomainException):
    status_code = e.status_code
    if isinstance(e, DuplicateResourceError):
        status_code = 409
    raise HTTPException(status_code=status_code, detail=e.message)


@router.post("/safe/purchases", response_model=MetalTransactionResponse, status_code=201)
def record_safe_purchase(
    data: SafePurchaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_role),
):
    try:
        service = SupplyTrackingService(db)
        return service.record_safe_purchase(
            tenant_id=current_user.tenant_id,
            metal_id=data.metal_id,
            supply_type=data.supply_type,
            quantity_grams=data.quantity_grams,
            cost_per_gram=data.cost_per_gram,
            user_id=current_user.id,
            notes=data.notes,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/safe/supplies", response_model=List[SafeSupplyResponse])
def get_safe_supplies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = SupplyTrackingService(db)
        return service.get_safe_supplies(tenant_id=current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/metal-transactions", response_model=List[MetalTransactionResponse])
def list_transactions(
    company_id: Optional[int] = Query(None),
    metal_id: Optional[int] = Query(None),
    transaction_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = SupplyTrackingService(db)
        return service.get_transactions(
            tenant_id=current_user.tenant_id,
            company_id=company_id,
            metal_id=metal_id,
            transaction_type=transaction_type,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.post(
    "/companies/{company_id}/metal-deposits",
    response_model=MetalTransactionResponse,
    status_code=201,
)
def record_company_deposit(
    company_id: int,
    data: MetalDepositCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_role),
):
    try:
        service = SupplyTrackingService(db)
        return service.record_company_deposit(
            tenant_id=current_user.tenant_id,
            company_id=company_id,
            metal_id=data.metal_id,
            quantity_grams=data.quantity_grams,
            user_id=current_user.id,
            notes=data.notes,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get(
    "/companies/{company_id}/metal-balances",
    response_model=List[CompanyMetalBalanceResponse],
)
def get_company_balances(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = SupplyTrackingService(db)
        return service.get_company_balances(
            tenant_id=current_user.tenant_id,
            company_id=company_id,
        )
    except DomainException as e:
        handle_domain_exception(e)
