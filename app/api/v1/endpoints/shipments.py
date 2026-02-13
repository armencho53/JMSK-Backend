from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.data.models.shipment import Shipment
from app.domain.enums import ShipmentStatus
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate, ShipmentResponse

router = APIRouter()

@router.get("/", response_model=List[ShipmentResponse])
def list_shipments(
    order_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Shipment).filter(
        Shipment.tenant_id == current_user.tenant_id
    )
    
    if order_id:
        query = query.filter(Shipment.order_id == order_id)
    
    shipments = query.offset(skip).limit(limit).all()
    return shipments

@router.post("/", response_model=ShipmentResponse)
def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_shipment = Shipment(**shipment.dict(), tenant_id=current_user.tenant_id)
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    return db_shipment

@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_id,
        Shipment.tenant_id == current_user.tenant_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return shipment

@router.put("/{shipment_id}", response_model=ShipmentResponse)
def update_shipment(
    shipment_id: int,
    shipment_update: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_id,
        Shipment.tenant_id == current_user.tenant_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    for key, value in shipment_update.dict(exclude_unset=True).items():
        setattr(shipment, key, value)

    # Auto-set timestamps
    if shipment_update.status == ShipmentStatus.SHIPPED and not shipment.shipped_at:
        shipment.shipped_at = datetime.utcnow()
    elif shipment_update.status == ShipmentStatus.DELIVERED and not shipment.delivered_at:
        shipment.delivered_at = datetime.utcnow()

    db.commit()
    db.refresh(shipment)
    return shipment

@router.delete("/{shipment_id}")
def delete_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_id,
        Shipment.tenant_id == current_user.tenant_id
    ).first()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    db.delete(shipment)
    db.commit()
    return {"message": "Shipment deleted successfully"}
