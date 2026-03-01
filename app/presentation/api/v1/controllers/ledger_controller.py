"""Department Ledger API controller"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.schemas.ledger import (
    LedgerEntryCreate,
    LedgerEntryUpdate,
    LedgerEntryResponse,
    LedgerSummaryResponse,
    ArchiveRequest,
)
from app.domain.services.ledger_service import LedgerService
from app.domain.exceptions import DomainException

router = APIRouter()


def handle_domain_exception(e: DomainException):
    raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/", response_model=List[LedgerEntryResponse])
def list_entries(
    department_id: Optional[int] = Query(None, description="Filter by department"),
    order_id: Optional[int] = Query(None, description="Filter by order"),
    date_from: Optional[date] = Query(None, description="Filter from date (inclusive)"),
    date_to: Optional[date] = Query(None, description="Filter to date (inclusive)"),
    include_archived: bool = Query(False, description="Include archived entries"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = LedgerService(db)
        return service.list_entries(
            tenant_id=current_user.tenant_id,
            department_id=department_id,
            order_id=order_id,
            date_from=date_from,
            date_to=date_to,
            include_archived=include_archived,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/", response_model=LedgerEntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    data: LedgerEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = LedgerService(db)
        return service.create_entry(
            data=data,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/summary", response_model=LedgerSummaryResponse)
def get_summary(
    department_id: Optional[int] = Query(None, description="Filter by department"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = LedgerService(db)
        return service.get_summary(
            tenant_id=current_user.tenant_id,
            department_id=department_id,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/archive")
def archive_entries(
    data: ArchiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = LedgerService(db)
        count = service.archive_entries(
            tenant_id=current_user.tenant_id,
            date_from=data.date_from,
            date_to=data.date_to,
        )
        return {"message": f"{count} entries archived successfully", "count": count}
    except DomainException as e:
        handle_domain_exception(e)


@router.put("/{entry_id}", response_model=LedgerEntryResponse)
def update_entry(
    entry_id: int,
    data: LedgerEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = LedgerService(db)
        return service.update_entry(
            entry_id=entry_id,
            data=data,
            tenant_id=current_user.tenant_id,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = LedgerService(db)
        service.delete_entry(
            entry_id=entry_id,
            tenant_id=current_user.tenant_id,
        )
        return {"message": "Ledger entry deleted successfully"}
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/{entry_id}/unarchive", response_model=LedgerEntryResponse)
def unarchive_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        service = LedgerService(db)
        return service.unarchive_entry(
            entry_id=entry_id,
            tenant_id=current_user.tenant_id,
        )
    except DomainException as e:
        handle_domain_exception(e)
