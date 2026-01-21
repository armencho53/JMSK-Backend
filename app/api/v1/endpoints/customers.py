from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.data.models.customer import Customer
from app.data.models.order import Order
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse, BalanceBreakdown, OrderSummary, ShipmentSummary
from app.data.models.order import OrderStatus
from app.data.models.shipment import Shipment

router = APIRouter()

@router.get("/", response_model=List[CustomerResponse])
def list_customers(
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None, description="Search by name, email, or company"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Customer).filter(Customer.tenant_id == current_user.tenant_id)
    
    if search:
        query = query.filter(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%")
            )
        )
    
    customers = query.offset(skip).limit(limit).all()
    
    # Calculate balance for each customer
    result = []
    for customer in customers:
        balance = db.query(func.sum(Order.price)).filter(
            Order.customer_id == customer.id
        ).scalar() or 0.0
        
        customer_dict = {
            "id": customer.id,
            "tenant_id": customer.tenant_id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "company_id": customer.company_id,
            "created_at": customer.created_at,
            "updated_at": customer.updated_at,
            "balance": balance
        }
        result.append(CustomerResponse(**customer_dict))
    
    return result

@router.post("/", response_model=CustomerResponse)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Check if email already exists for this tenant
    existing = db.query(Customer).filter(
        Customer.tenant_id == current_user.tenant_id,
        Customer.email == customer.email
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Customer with this email already exists"
        )
    
    db_customer = Customer(
        **customer.dict(),
        tenant_id=current_user.tenant_id
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    # Add balance field
    customer_dict = {
        "id": db_customer.id,
        "tenant_id": db_customer.tenant_id,
        "name": db_customer.name,
        "email": db_customer.email,
        "phone": db_customer.phone,
        "company_id": db_customer.company_id,
        "created_at": db_customer.created_at,
        "updated_at": db_customer.updated_at,
        "balance": 0.0
    }
    
    return CustomerResponse(**customer_dict)

@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Calculate balance
    balance = db.query(func.sum(Order.price)).filter(
        Order.customer_id == customer.id
    ).scalar() or 0.0
    
    customer_dict = {
        "id": customer.id,
        "tenant_id": customer.tenant_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "company_id": customer.company_id,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "balance": balance
    }
    
    return CustomerResponse(**customer_dict)

@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check if email is being changed and if it already exists
    if customer_update.email and customer_update.email != customer.email:
        existing = db.query(Customer).filter(
            Customer.tenant_id == current_user.tenant_id,
            Customer.email == customer_update.email
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Customer with this email already exists"
            )
    
    for key, value in customer_update.dict(exclude_unset=True).items():
        setattr(customer, key, value)
    
    db.commit()
    db.refresh(customer)
    
    # Calculate balance
    balance = db.query(func.sum(Order.price)).filter(
        Order.customer_id == customer.id
    ).scalar() or 0.0
    
    customer_dict = {
        "id": customer.id,
        "tenant_id": customer.tenant_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "company_id": customer.company_id,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "balance": balance
    }
    
    return CustomerResponse(**customer_dict)

@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check if customer has orders
    order_count = db.query(Order).filter(Order.customer_id == customer_id).count()
    if order_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete customer with existing orders"
        )
    
    db.delete(customer)
    db.commit()
    
    return {"message": "Customer deleted successfully"}


@router.get("/{customer_id}/balance", response_model=BalanceBreakdown)
def get_customer_balance(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Calculate total balance
    total = db.query(func.sum(Order.price)).filter(
        Order.customer_id == customer_id
    ).scalar() or 0.0
    
    # Calculate pending balance (pending and in_progress orders)
    pending = db.query(func.sum(Order.price)).filter(
        Order.customer_id == customer_id,
        Order.status.in_([OrderStatus.PENDING, OrderStatus.IN_PROGRESS])
    ).scalar() or 0.0
    
    # Calculate completed balance (completed and shipped orders)
    completed = db.query(func.sum(Order.price)).filter(
        Order.customer_id == customer_id,
        Order.status.in_([OrderStatus.COMPLETED, OrderStatus.SHIPPED])
    ).scalar() or 0.0
    
    return BalanceBreakdown(
        total=total,
        pending=pending,
        completed=completed
    )


@router.get("/{customer_id}/orders", response_model=List[OrderSummary])
def get_customer_orders(
    customer_id: int,
    status: str = Query(None, description="Filter by order status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
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


@router.get("/{customer_id}/shipments", response_model=List[ShipmentSummary])
def get_customer_shipments(
    customer_id: int,
    status: str = Query(None, description="Filter by shipment status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.tenant_id == current_user.tenant_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
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
