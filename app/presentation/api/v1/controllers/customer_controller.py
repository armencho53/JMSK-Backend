"""Customer API controller"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    BalanceBreakdown,
    OrderSummary,
    ShipmentSummary
)
from app.domain.services.customer_service import CustomerService
from app.domain.exceptions import DomainException

router = APIRouter()


def handle_domain_exception(e: DomainException):
    """Convert domain exceptions to HTTP exceptions"""
    raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/", response_model=List[CustomerResponse])
def list_customers(
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None, description="Search by name, email, or company"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all customers for the current tenant"""
    try:
        service = CustomerService(db)
        return service.get_all_customers(
            tenant_id=current_user.tenant_id,
            skip=skip,
            limit=limit,
            search=search
        )
    except DomainException as e:
        handle_domain_exception(e)


@router.post("/", response_model=CustomerResponse)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new customer"""
    try:
        service = CustomerService(db)
        return service.create_customer(customer, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single customer by ID"""
    try:
        service = CustomerService(db)
        return service.get_customer_by_id(customer_id, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing customer"""
    try:
        service = CustomerService(db)
        return service.update_customer(customer_id, customer_update, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a customer"""
    try:
        service = CustomerService(db)
        service.delete_customer(customer_id, current_user.tenant_id)
        return {"message": "Customer deleted successfully"}
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{customer_id}/balance", response_model=BalanceBreakdown)
def get_customer_balance(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed balance breakdown for a customer"""
    try:
        service = CustomerService(db)
        return service.get_customer_balance(customer_id, current_user.tenant_id)
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{customer_id}/orders", response_model=List[OrderSummary])
def get_customer_orders(
    customer_id: int,
    status: str = Query(None, description="Filter by order status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all orders for a customer"""
    try:
        # Import here to avoid circular dependency
        from app.data.models.customer import Customer
        from app.data.models.order import Order
        from app.domain.exceptions import ResourceNotFoundError
        
        # Verify customer exists and belongs to tenant
        customer = db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.tenant_id == current_user.tenant_id
        ).first()
        
        if not customer:
            raise ResourceNotFoundError("Customer", customer_id)
        
        query = db.query(Order).filter(Order.customer_id == customer_id)
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            OrderSummary(
                id=order.id,
                order_number=order.order_number,
                product_description=order.product_description,
                quantity=order.quantity,
                price=order.price,
                status=order.status.value,
                due_date=order.due_date,
                created_at=order.created_at
            )
            for order in orders
        ]
    except DomainException as e:
        handle_domain_exception(e)


@router.get("/{customer_id}/shipments", response_model=List[ShipmentSummary])
def get_customer_shipments(
    customer_id: int,
    status: str = Query(None, description="Filter by shipment status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all shipments for a customer"""
    try:
        from app.data.models.customer import Customer
        from app.data.models.order import Order
        from app.data.models.shipment import Shipment
        from app.domain.exceptions import ResourceNotFoundError
        
        # Verify customer exists and belongs to tenant
        customer = db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.tenant_id == current_user.tenant_id
        ).first()
        
        if not customer:
            raise ResourceNotFoundError("Customer", customer_id)
        
        # Join shipments through orders
        query = db.query(Shipment).join(Order).filter(Order.customer_id == customer_id)
        
        if status:
            query = query.filter(Shipment.status == status)
        
        shipments = query.order_by(Shipment.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            ShipmentSummary(
                id=shipment.id,
                order_id=shipment.order_id,
                tracking_number=shipment.tracking_number,
                carrier=shipment.carrier,
                shipping_address=shipment.shipping_address,
                status=shipment.status.value,
                shipped_at=shipment.shipped_at,
                delivered_at=shipment.delivered_at
            )
            for shipment in shipments
        ]
    except DomainException as e:
        handle_domain_exception(e)
