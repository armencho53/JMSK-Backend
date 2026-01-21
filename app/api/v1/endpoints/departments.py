from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.data.models.department import Department
from app.data.models.department_balance import DepartmentBalance
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentWithBalancesResponse,
    DepartmentBalanceResponse
)

router = APIRouter()

@router.get("/", response_model=List[DepartmentWithBalancesResponse])
def list_departments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all departments with their balances for current tenant"""
    departments = db.query(Department).filter(
        Department.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).all()
    return departments

@router.post("/", response_model=DepartmentResponse)
def create_department(
    department: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new department (admin only in future)"""
    # Check if department name already exists for this tenant
    existing = db.query(Department).filter(
        Department.tenant_id == current_user.tenant_id,
        Department.name == department.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Department with this name already exists"
        )

    db_department = Department(
        **department.dict(),
        tenant_id=current_user.tenant_id
    )
    db.add(db_department)
    db.commit()
    db.refresh(db_department)

    return db_department

@router.get("/{department_id}", response_model=DepartmentWithBalancesResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single department with its balances"""
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.tenant_id == current_user.tenant_id
    ).first()

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    return department

@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    department_update: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a department (admin only in future)"""
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.tenant_id == current_user.tenant_id
    ).first()

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    # Check if new name already exists (if name is being updated)
    if department_update.name and department_update.name != department.name:
        existing = db.query(Department).filter(
            Department.tenant_id == current_user.tenant_id,
            Department.name == department_update.name
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Department with this name already exists"
            )

    # Update fields
    update_data = department_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)

    db.commit()
    db.refresh(department)

    return department

@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a department (admin only in future)"""
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.tenant_id == current_user.tenant_id
    ).first()

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    # Check if department is "Inventory" (cannot be deleted)
    if department.name.lower() == "inventory":
        raise HTTPException(
            status_code=400,
            detail="Inventory department cannot be deleted"
        )

    db.delete(department)
    db.commit()

    return {"message": "Department deleted successfully"}

@router.get("/{department_id}/balances", response_model=List[DepartmentBalanceResponse])
def get_department_balances(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get balances for a specific department by metal type"""
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.tenant_id == current_user.tenant_id
    ).first()

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    balances = db.query(DepartmentBalance).filter(
        DepartmentBalance.department_id == department_id
    ).all()

    return balances

@router.get("/balances/summary", response_model=List[DepartmentWithBalancesResponse])
def get_balances_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all departments with their balances for dashboard display"""
    departments = db.query(Department).filter(
        Department.tenant_id == current_user.tenant_id,
        Department.is_active == True
    ).all()

    return departments
