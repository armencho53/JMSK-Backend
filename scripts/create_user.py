#!/usr/bin/env python3
"""
Helper script to create users for any tenant
Usage: cd backend
export DATABASE_URL='postgresql://postgres.esdjwyvwhpuknjtqfzzb:fu18Qk1wOuKBdRyB@aws-1-us-east-1.pooler.supabase.com:5432/postgres'
source venv/bin/activate
python create_user.py

"""
import sys
from sqlalchemy.orm import Session
from app.data.database import SessionLocal
from app.data.models.user import User
from app.infrastructure.security import get_password_hash

def create_user():
    db = SessionLocal()
    
    try:
        print("=" * 50)
        print("Create New User")
        print("=" * 50)
        
        # Get user input
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        full_name = input("Full Name: ").strip()
        tenant_id = int(input("Tenant ID: ").strip())
        role_id = int(input("Role ID (1=admin): ").strip() or "1")
        
        # Check if user already exists
        existing = db.query(User).filter(
            User.email == email,
            User.tenant_id == tenant_id
        ).first()
        
        if existing:
            print(f"\n❌ User {email} already exists for tenant {tenant_id}")
            sys.exit(1)
        
        # Create user
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            tenant_id=tenant_id,
            role_id=role_id,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print("\n" + "=" * 50)
        print("✅ User created successfully!")
        print("=" * 50)
        print(f"ID: {user.id}")
        print(f"Email: {user.email}")
        print(f"Full Name: {user.full_name}")
        print(f"Tenant ID: {user.tenant_id}")
        print(f"Role ID: {user.role_id}")
        print(f"Active: {user.is_active}")
        print("\nUser can now login with:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_user()
