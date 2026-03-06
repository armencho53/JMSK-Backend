"""Order API controller with clean architecture"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

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
    import logging
    logger = logging.getLogger(__name__)
    try:
        service = OrderService(db)
        result = service.create_order_with_deposit(
            order_data=order_data.model_dump(),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        return result
    except DomainException as e:
        handle_domain_exception(e)
    except Exception as e:
        logger.error(f"Unexpected error creating order: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
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
            order_data=order_data.model_dump(exclude_unset=True),
            tenant_id=current_user.tenant_id,
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{order_id}/timeline", response_model=Dict[str, Any])
def get_order_timeline(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get manufacturing timeline for an order using department ledger entries.
    
    Returns department-level progress showing which departments have
    received (IN) and returned (OUT) items for this order.
    """
    from sqlalchemy.orm import joinedload
    from app.data.models.order import Order
    from app.data.models.contact import Contact
    from app.data.models.department_ledger_entry import DepartmentLedgerEntry

    order = db.query(Order).options(
        joinedload(Order.contact),
        joinedload(Order.line_items),
    ).filter(
        Order.id == order_id,
        Order.tenant_id == current_user.tenant_id,
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    entries = db.query(DepartmentLedgerEntry).options(
        joinedload(DepartmentLedgerEntry.department),
        joinedload(DepartmentLedgerEntry.metal),
    ).filter(
        DepartmentLedgerEntry.order_id == order_id,
        DepartmentLedgerEntry.tenant_id == current_user.tenant_id,
        DepartmentLedgerEntry.is_archived == False,
    ).order_by(DepartmentLedgerEntry.date, DepartmentLedgerEntry.created_at).all()

    # Group entries by department to determine status
    dept_map: Dict[int, Dict[str, Any]] = {}
    for entry in entries:
        dept_id = entry.department_id
        if dept_id not in dept_map:
            dept_map[dept_id] = {
                "department_name": entry.department.name if entry.department else f"Dept {dept_id}",
                "has_in": False,
                "has_out": False,
                "latest_date": None,
                "entries": [],
            }
        info = dept_map[dept_id]
        if entry.direction == "IN":
            info["has_in"] = True
        elif entry.direction == "OUT":
            info["has_out"] = True
        entry_date = entry.date
        if info["latest_date"] is None or entry_date > info["latest_date"]:
            info["latest_date"] = entry_date
        info["entries"].append(entry)

    # Build timeline steps from department groups
    steps = []
    for dept_id, info in dept_map.items():
        if info["has_in"] and info["has_out"]:
            step_status = "completed"
        elif info["has_in"]:
            step_status = "in_progress"
        else:
            step_status = "pending"

        steps.append({
            "id": dept_id,
            "step_type": info["department_name"],
            "status": step_status,
            "department": info["department_name"],
            "duration_hours": None,
            "sequence_order": dept_id,
        })

    # Determine product description from line items
    product_desc = ""
    if order.line_items and len(order.line_items) > 0:
        product_desc = order.line_items[0].product_description or ""
        if len(order.line_items) > 1:
            product_desc += f" (+{len(order.line_items) - 1} more)"
    elif order.product_description:
        product_desc = order.product_description

    contact_name = order.contact.name if order.contact else "Unknown Contact"

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "contact_name": contact_name,
        "product_description": product_desc,
        "steps": steps,
        "total_steps": len(steps),
    }
