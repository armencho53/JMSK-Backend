from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.data.models.supply import Supply
from app.schemas.supply import SupplyCreate, SupplyUpdate, SupplyResponse
from app.domain.services.lookup_service import LookupService
from app.domain.exceptions import ValidationError

router = APIRouter()

@router.get("/", response_model=List[SupplyResponse])
def list_supplies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    supplies = db.query(Supply).filter(
        Supply.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).all()
    return supplies

@router.post("/", response_model=SupplyResponse)
def create_supply(
    supply: SupplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Validate type against lookup values (Requirement 6.3)
    lookup_service = LookupService(db)
    try:
        lookup_service.validate_lookup_code(current_user.tenant_id, "supply_type", supply.type)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    db_supply = Supply(**supply.dict(), tenant_id=current_user.tenant_id)
    db.add(db_supply)
    db.commit()
    db.refresh(db_supply)
    return db_supply

@router.get("/{supply_id}", response_model=SupplyResponse)
def get_supply(
    supply_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    supply = db.query(Supply).filter(
        Supply.id == supply_id,
        Supply.tenant_id == current_user.tenant_id
    ).first()
    
    if not supply:
        raise HTTPException(status_code=404, detail="Supply not found")
    
    return supply

@router.put("/{supply_id}", response_model=SupplyResponse)
def update_supply(
    supply_id: int,
    supply_update: SupplyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    supply = db.query(Supply).filter(
        Supply.id == supply_id,
        Supply.tenant_id == current_user.tenant_id
    ).first()
    
    if not supply:
        raise HTTPException(status_code=404, detail="Supply not found")
    
    update_data = supply_update.dict(exclude_unset=True)

    # Validate type against lookup values if provided (Requirement 6.3)
    supply_type = update_data.get('type')
    if supply_type:
        lookup_service = LookupService(db)
        try:
            lookup_service.validate_lookup_code(current_user.tenant_id, "supply_type", supply_type)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=e.message)

    for key, value in update_data.items():
        setattr(supply, key, value)
    
    db.commit()
    db.refresh(supply)
    return supply

@router.delete("/{supply_id}")
def delete_supply(
    supply_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    supply = db.query(Supply).filter(
        Supply.id == supply_id,
        Supply.tenant_id == current_user.tenant_id
    ).first()
    
    if not supply:
        raise HTTPException(status_code=404, detail="Supply not found")
    
    db.delete(supply)
    db.commit()
    return {"message": "Supply deleted successfully"}
