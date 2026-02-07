from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.data.models.order import Order
from app.data.models.contact import Contact
from app.data.models.manufacturing_step import ManufacturingStep
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse

router = APIRouter()

def generate_order_number(tenant_id: int, db: Session) -> str:
    count = db.query(Order).filter(Order.tenant_id == tenant_id).count()
    return f"ORD-{tenant_id}-{count + 1:05d}"

@router.get("/", response_model=List[OrderResponse])
def list_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from sqlalchemy.orm import joinedload
    
    # Eagerly load contact and company relationships (Requirements 3.1, 7.3)
    orders = db.query(Order).options(
        joinedload(Order.contact).joinedload(Contact.company),
        joinedload(Order.company)
    ).filter(
        Order.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).all()
    return orders

@router.post("/", response_model=OrderResponse)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    order_number = generate_order_number(current_user.tenant_id, db)
    order_data = order.dict()
    
    # Validate contact_id and auto-populate company_id
    contact_id = order_data.get('contact_id')
    
    if contact_id:
        contact = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id
        ).first()
        
        if not contact:
            raise HTTPException(
                status_code=404, 
                detail=f"Contact with id {contact_id} not found"
            )
        
        # Auto-populate company_id from contact's company (Requirement 3.1)
        order_data['contact_id'] = contact.id
        order_data['company_id'] = contact.company_id
    
    db_order = Order(
        **order_data,
        order_number=order_number,
        tenant_id=current_user.tenant_id
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from sqlalchemy.orm import joinedload
    
    # Eagerly load contact and company relationships (Requirements 3.1, 7.3)
    order = db.query(Order).options(
        joinedload(Order.contact).joinedload(Contact.company),
        joinedload(Order.company)
    ).filter(
        Order.id == order_id,
        Order.tenant_id == current_user.tenant_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.tenant_id == current_user.tenant_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = order_update.dict(exclude_unset=True)
    
    # Handle contact_id update
    contact_id = update_data.get('contact_id')
    
    if contact_id:
        contact = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.tenant_id == current_user.tenant_id
        ).first()
        
        if not contact:
            raise HTTPException(
                status_code=404, 
                detail=f"Contact with id {contact_id} not found"
            )
        
        # Auto-populate company_id from contact's company (Requirement 3.1)
        update_data['contact_id'] = contact.id
        update_data['company_id'] = contact.company_id
    
    for key, value in update_data.items():
        setattr(order, key, value)
    
    db.commit()
    db.refresh(order)
    return order

@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.tenant_id == current_user.tenant_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()
    return {"message": "Order deleted successfully"}

@router.get("/{order_id}/timeline", response_model=Dict[str, Any])
def get_order_timeline(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get timeline of manufacturing steps for an order
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.tenant_id == current_user.tenant_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Get all manufacturing steps for this order, ordered by sequence
    steps = db.query(ManufacturingStep).filter(
        ManufacturingStep.order_id == order_id,
        ManufacturingStep.tenant_id == current_user.tenant_id
    ).order_by(ManufacturingStep.sequence_order, ManufacturingStep.created_at).all()

    timeline_steps = []
    for step in steps:
        # Calculate duration if step has timestamps
        duration_hours = None
        if step.started_at and step.completed_at:
            duration_seconds = (step.completed_at - step.started_at).total_seconds()
            duration_hours = round(duration_seconds / 3600, 2)

        timeline_steps.append({
            "id": step.id,
            "step_name": step.step_name,
            "step_type": step.step_type.value,
            "status": step.status.value,
            "department": step.department,
            "worker_name": step.worker_name or step.assigned_to,
            "started_at": step.started_at,
            "completed_at": step.completed_at,
            "received_at": step.received_at,
            "duration_hours": duration_hours,
            "sequence_order": step.sequence_order,
            "weight_loss_percentage": step.weight_loss_percentage,
            "expected_loss_percentage": step.expected_loss_percentage
        })

    # Get contact name from relationship
    contact_name = order.contact.name if order.contact else "Unknown Contact"
    
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "contact_name": contact_name,
        "product_description": order.product_description,
        "steps": timeline_steps,
        "total_steps": len(timeline_steps)
    }
