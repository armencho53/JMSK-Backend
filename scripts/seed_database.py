#!/usr/bin/env python3
"""
Database seeding script - creates initial data for development
Idempotent: safe to run multiple times
"""
import sys
from sqlalchemy.orm import Session
from app.data.database import SessionLocal
from app.data.models.tenant import Tenant
from app.data.models.role import Role, Permission
from app.data.models.user import User
from app.infrastructure.security import get_password_hash

def seed_permissions(db: Session):
    """Create default permissions"""
    permissions_data = [
        # Supply permissions
        {"name": "supplies:create", "description": "Create supplies", "resource": "supplies", "action": "create"},
        {"name": "supplies:read", "description": "View supplies", "resource": "supplies", "action": "read"},
        {"name": "supplies:update", "description": "Update supplies", "resource": "supplies", "action": "update"},
        {"name": "supplies:delete", "description": "Delete supplies", "resource": "supplies", "action": "delete"},
        
        # Order permissions
        {"name": "orders:create", "description": "Create orders", "resource": "orders", "action": "create"},
        {"name": "orders:read", "description": "View orders", "resource": "orders", "action": "read"},
        {"name": "orders:update", "description": "Update orders", "resource": "orders", "action": "update"},
        {"name": "orders:delete", "description": "Delete orders", "resource": "orders", "action": "delete"},
        
        # Manufacturing permissions
        {"name": "manufacturing:create", "description": "Create manufacturing steps", "resource": "manufacturing", "action": "create"},
        {"name": "manufacturing:read", "description": "View manufacturing steps", "resource": "manufacturing", "action": "read"},
        {"name": "manufacturing:update", "description": "Update manufacturing steps", "resource": "manufacturing", "action": "update"},
        {"name": "manufacturing:delete", "description": "Delete manufacturing steps", "resource": "manufacturing", "action": "delete"},
        
        # Shipment permissions
        {"name": "shipments:create", "description": "Create shipments", "resource": "shipments", "action": "create"},
        {"name": "shipments:read", "description": "View shipments", "resource": "shipments", "action": "read"},
        {"name": "shipments:update", "description": "Update shipments", "resource": "shipments", "action": "update"},
        {"name": "shipments:delete", "description": "Delete shipments", "resource": "shipments", "action": "delete"},
        
        # User permissions
        {"name": "users:create", "description": "Create users", "resource": "users", "action": "create"},
        {"name": "users:read", "description": "View users", "resource": "users", "action": "read"},
        {"name": "users:update", "description": "Update users", "resource": "users", "action": "update"},
        {"name": "users:delete", "description": "Delete users", "resource": "users", "action": "delete"},
        
        # Role permissions
        {"name": "roles:create", "description": "Create roles", "resource": "roles", "action": "create"},
        {"name": "roles:read", "description": "View roles", "resource": "roles", "action": "read"},
        {"name": "roles:update", "description": "Update roles", "resource": "roles", "action": "update"},
        {"name": "roles:delete", "description": "Delete roles", "resource": "roles", "action": "delete"},
    ]
    
    created_permissions = []
    for perm_data in permissions_data:
        existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not existing:
            permission = Permission(**perm_data)
            db.add(permission)
            created_permissions.append(perm_data["name"])
    
    db.commit()
    return created_permissions

def seed_tenant(db: Session):
    """Create default tenant"""
    existing = db.query(Tenant).filter(Tenant.name == "Demo Company").first()
    if existing:
        print(f"✓ Tenant 'Demo Company' already exists (ID: {existing.id})")
        return existing
    
    tenant = Tenant(
        name="Demo Company",
        subdomain="demo",
        is_active=True
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    print(f"✓ Created tenant 'Demo Company' (ID: {tenant.id})")
    return tenant

def seed_roles(db: Session, tenant_id: int):
    """Create default roles with permissions"""
    all_permissions = db.query(Permission).all()
    
    # Admin role - all permissions
    admin_role = db.query(Role).filter(
        Role.tenant_id == tenant_id,
        Role.name == "admin"
    ).first()
    
    if not admin_role:
        admin_role = Role(
            tenant_id=tenant_id,
            name="admin",
            description="Administrator with full access",
            is_system_role=True,
            permissions=all_permissions
        )
        db.add(admin_role)
        print(f"✓ Created 'admin' role with {len(all_permissions)} permissions")
    else:
        print(f"✓ Role 'admin' already exists (ID: {admin_role.id})")
    
    # Manager role - most permissions except user/role management
    manager_perms = [p for p in all_permissions if not p.resource in ["users", "roles"]]
    manager_role = db.query(Role).filter(
        Role.tenant_id == tenant_id,
        Role.name == "manager"
    ).first()
    
    if not manager_role:
        manager_role = Role(
            tenant_id=tenant_id,
            name="manager",
            description="Manager with access to operations",
            is_system_role=True,
            permissions=manager_perms
        )
        db.add(manager_role)
        print(f"✓ Created 'manager' role with {len(manager_perms)} permissions")
    else:
        print(f"✓ Role 'manager' already exists (ID: {manager_role.id})")
    
    # Viewer role - read-only access
    viewer_perms = [p for p in all_permissions if p.action == "read"]
    viewer_role = db.query(Role).filter(
        Role.tenant_id == tenant_id,
        Role.name == "viewer"
    ).first()
    
    if not viewer_role:
        viewer_role = Role(
            tenant_id=tenant_id,
            name="viewer",
            description="Read-only access to all resources",
            is_system_role=True,
            permissions=viewer_perms
        )
        db.add(viewer_role)
        print(f"✓ Created 'viewer' role with {len(viewer_perms)} permissions")
    else:
        print(f"✓ Role 'viewer' already exists (ID: {viewer_role.id})")
    
    db.commit()
    return admin_role, manager_role, viewer_role

def seed_admin_user(db: Session, tenant_id: int, admin_role_id: int):
    """Create default admin user"""
    email = "admin@demo.com"
    existing = db.query(User).filter(
        User.email == email,
        User.tenant_id == tenant_id
    ).first()
    
    if existing:
        print(f"✓ Admin user '{email}' already exists (ID: {existing.id})")
        return existing
    
    password = "admin123"
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name="Admin User",
        tenant_id=tenant_id,
        role_id=admin_role_id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    print(f"✓ Created admin user:")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
    print(f"  ID: {user.id}")
    return user

def main():
    """Run all seed functions"""
    print("=" * 60)
    print("DATABASE SEEDING")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 1. Seed permissions
        print("\n1. Seeding permissions...")
        created_perms = seed_permissions(db)
        if created_perms:
            print(f"✓ Created {len(created_perms)} new permissions")
        else:
            print("✓ All permissions already exist")
        
        # 2. Seed tenant
        print("\n2. Seeding tenant...")
        tenant = seed_tenant(db)
        
        # 3. Seed roles
        print("\n3. Seeding roles...")
        admin_role, manager_role, viewer_role = seed_roles(db, tenant.id)
        
        # 4. Seed admin user
        print("\n4. Seeding admin user...")
        admin_user = seed_admin_user(db, tenant.id, admin_role.id)
        
        print("\n" + "=" * 60)
        print("✅ DATABASE SEEDING COMPLETED")
        print("=" * 60)
        print("\nYou can now login with:")
        print("  Email: admin@demo.com")
        print("  Password: admin123")
        print("\nTenant ID:", tenant.id)
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
