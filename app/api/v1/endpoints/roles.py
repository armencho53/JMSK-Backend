from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.data.database import get_db
from app.presentation.api.dependencies import get_current_active_user
from app.data.models.user import User
from app.data.models.role import Role, Permission
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PermissionResponse
)

router = APIRouter()

@router.get("/permissions", response_model=List[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all available permissions"""
    permissions = db.query(Permission).all()
    return permissions

@router.get("/", response_model=List[RoleResponse])
def list_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all roles for current tenant"""
    roles = db.query(Role).filter(
        Role.tenant_id == current_user.tenant_id
    ).offset(skip).limit(limit).all()
    return roles

@router.post("/", response_model=RoleResponse)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new role"""
    # Check if role name already exists for this tenant
    existing = db.query(Role).filter(
        Role.tenant_id == current_user.tenant_id,
        Role.name == role.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Role name already exists")
    
    # Create role
    db_role = Role(
        tenant_id=current_user.tenant_id,
        name=role.name,
        description=role.description,
        is_system_role=False
    )
    
    # Add permissions
    if role.permission_ids:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role.permission_ids)
        ).all()
        db_role.permissions = permissions
    
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get role by ID"""
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.tenant_id == current_user.tenant_id
    ).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return role

@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update role"""
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.tenant_id == current_user.tenant_id
    ).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.is_system_role:
        raise HTTPException(status_code=400, detail="Cannot modify system roles")
    
    # Update basic fields
    if role_update.name is not None:
        role.name = role_update.name
    if role_update.description is not None:
        role.description = role_update.description
    
    # Update permissions
    if role_update.permission_ids is not None:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_update.permission_ids)
        ).all()
        role.permissions = permissions
    
    db.commit()
    db.refresh(role)
    return role

@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete role"""
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.tenant_id == current_user.tenant_id
    ).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.is_system_role:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    
    # Check if any users have this role
    users_count = db.query(User).filter(User.role_id == role_id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete role. {users_count} user(s) are assigned to this role"
        )
    
    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"}
