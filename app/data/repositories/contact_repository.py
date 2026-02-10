"""Contact repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from app.data.repositories.base import BaseRepository
from app.data.models.contact import Contact
from app.data.models.order import Order


class ContactRepository(BaseRepository[Contact]):
    """
    Repository for contact data access operations.
    
    Provides CRUD operations and specialized queries for contacts in the
    hierarchical contact system. All operations enforce multi-tenant isolation
    through tenant_id filtering.
    
    Methods:
        get_by_email: Find contact by email within a company
        get_by_company: Get all contacts for a specific company
        search: Search contacts by name or email
        get_with_company: Get contact with company relationship loaded
        get_balance: Calculate total order value for a contact
        has_orders: Check if contact has any orders
        count_by_company: Count contacts for a specific company
    
    Requirements: 1.1, 1.3, 1.4
    """
    
    def __init__(self, db: Session):
        super().__init__(Contact, db)
    
    def get_by_email(
        self,
        email: str,
        company_id: int,
        tenant_id: int
    ) -> Optional[Contact]:
        """
        Get contact by email within a specific company.
        
        Since the same email can exist across different companies, we need
        to filter by both company_id and tenant_id to find the correct contact.
        
        Args:
            email: Contact's email address
            company_id: ID of the company the contact belongs to
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Contact if found, None otherwise
        
        Requirements: 1.4
        """
        return self.db.query(Contact).filter(
            Contact.email == email,
            Contact.company_id == company_id,
            Contact.tenant_id == tenant_id
        ).first()
    
    def get_by_company(
        self,
        company_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """
        Get all contacts for a specific company.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of contacts belonging to the company
        
        Requirements: 1.3, 4.1
        """
        return self.db.query(Contact).filter(
            Contact.company_id == company_id,
            Contact.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()
    
    def search(
        self,
        tenant_id: int,
        search_term: str,
        company_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Contact]:
        """
        Search contacts by name or email.
        
        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            search_term: Search term to match against name or email
            company_id: Optional company ID to filter by specific company
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of contacts matching the search criteria
        
        Requirements: 1.1
        """
        query = self.db.query(Contact).filter(
            Contact.tenant_id == tenant_id,
            or_(
                Contact.name.ilike(f"%{search_term}%"),
                Contact.email.ilike(f"%{search_term}%")
            )
        )
        
        if company_id is not None:
            query = query.filter(Contact.company_id == company_id)
        
        return query.offset(skip).limit(limit).all()
    
    def get_with_company(
        self,
        contact_id: int,
        tenant_id: int
    ) -> Optional[Contact]:
        """
        Get contact with company relationship eagerly loaded.
        
        Uses joinedload to avoid N+1 query problems when accessing
        the contact's company information.
        
        Args:
            contact_id: ID of the contact
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Contact with company loaded, or None if not found
        
        Requirements: 1.3, 7.2
        """
        return self.db.query(Contact).options(
            joinedload(Contact.company)
        ).filter(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id
        ).first()
    
    def get_balance(self, contact_id: int, tenant_id: int) -> float:
        """
        Calculate total balance (sum of order values) for a contact.
        
        Sums the total_amount from all orders placed by this contact.
        Returns 0.0 if the contact has no orders.
        
        Args:
            contact_id: ID of the contact
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Total balance as a float
        
        Requirements: 2.1, 3.2
        """
        balance = self.db.query(func.sum(Order.price)).filter(
            Order.contact_id == contact_id,
            Order.tenant_id == tenant_id
        ).scalar()
        return balance or 0.0
    
    def has_orders(self, contact_id: int, tenant_id: int) -> bool:
        """
        Check if contact has any orders.
        
        Useful for validation before deleting a contact or for
        displaying contact status in the UI.
        
        Args:
            contact_id: ID of the contact
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            True if contact has orders, False otherwise
        
        Requirements: 1.6, 3.2
        """
        count = self.db.query(Order).filter(
            Order.contact_id == contact_id,
            Order.tenant_id == tenant_id
        ).count()
        return count > 0
    
    def count_by_company(self, company_id: int, tenant_id: int) -> int:
        """
        Count total number of contacts for a specific company.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Number of contacts belonging to the company
        
        Requirements: 4.3
        """
        return self.db.query(Contact).filter(
            Contact.company_id == company_id,
            Contact.tenant_id == tenant_id
        ).count()
