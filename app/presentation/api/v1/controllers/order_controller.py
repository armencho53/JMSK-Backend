"""Order API controller with clean architecture"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.schemas.order import (
    OrderCreateWithDeposit,
    OrderUpdate,
    OrderResponse,
)
from app.domain.services.order_service import OrderService
from app.domain.exceptions import DomainException

router = APIRouter()


def handle_domain_exception(e: DomainException):
    """Convert domain exceptions to HTTP exceptions"""
    raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order_with_deposit(
    order_data: OrderCreateWithDeposit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new order with line items and optional metal deposit.
    
    This endpoint supports:
    - Multiple line items per order (minimum 1 required)
    - Optional metal deposit during order creation
    - Atomic transaction (both order and deposit succeed or both fail)
    
    Requirements: 3.9, 3.10, 5.8
    """
    try:
        service = OrderService(db)
        return service.create_order_with_deposit(
            order_data=order_data,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
    except DomainException as e:
        handle_domain_exception(e)
@router.get("/", response_model=List[OrderResponse])
def list_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all orders with pagination.

    Returns a list of orders with:
    - All associated line items
    - Contact and company information
    - Metal names for each line item

    Query Parameters:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: 100)

    Requirements: 3.9, 3.10
    """
    try:
        service = OrderService(db)
        return service.get_all_orders(
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit,
        )
    except DomainException as e:
        handle_domain_exception(e)



@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a single order by ID with all line items.
    
    Returns the order with:
    - All associated line items
    - Contact and company information
    - Metal names for each line item
    
    Requirements: 3.9, 3.10
    """
    try:
        service = OrderService(db)
        return service.get_order_with_line_items(
            order_id=order_id,
            tenant_id=current_user.tenant_id,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update an existing order.
    
    Supports updating:
    - Order header fields (contact, due date, status)
    - Line items (replaces all existing line items if provided)
    
    Requirements: 3.9
    """
    try:
        service = OrderService(db)
        return service.update_order(
            order_id=order_id,
            order_data=order_data,
            tenant_id=current_user.tenant_id,
        )
    except DomainException as e:
        handle_domain_exception(e)
