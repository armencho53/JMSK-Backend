"""
DEPRECATED: Legacy customer repository for data access.

This repository is being replaced by ContactRepository as part of the
hierarchical contact system migration. Use app.data.repositories.contact_repository
for all new code.

Migration path: CustomerRepository -> ContactRepository
See: app/data/repositories/contact_repository.py
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.data.repositories.base import BaseRepository
from app.data.models.customer import Customer
from app.data.models.order import Order


class CustomerRepository(BaseRepository[Customer]):
    """
    DEPRECATED: Repository for customer data access.
    Use ContactRepository instead.
    """
    
    def __init__(self, db: Session):
        super().__init__(Customer, db)
    
    def get_by_email(self, email: str, tenant_id: int) -> Optional[Customer]:
        """Get customer by email within a tenant"""
        return self.db.query(Customer).filter(
            Customer.email == email,
            Customer.tenant_id == tenant_id
        ).first()
    
    def search(
        self,
        tenant_id: int,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Customer]:
        """Search customers by name or email"""
        return self.db.query(Customer).filter(
            Customer.tenant_id == tenant_id,
            or_(
                Customer.name.ilike(f"%{search_term}%"),
                Customer.email.ilike(f"%{search_term}%")
            )
        ).offset(skip).limit(limit).all()
    
    def get_balance(self, customer_id: int) -> float:
        """Calculate total balance for a customer"""
        balance = self.db.query(func.sum(Order.price)).filter(
            Order.customer_id == customer_id
        ).scalar()
        return balance or 0.0
    
    def has_orders(self, customer_id: int) -> bool:
        """Check if customer has any orders"""
        count = self.db.query(Order).filter(
            Order.customer_id == customer_id
        ).count()
        return count > 0
