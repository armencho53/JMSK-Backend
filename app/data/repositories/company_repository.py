"""Company repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from decimal import Decimal
from app.data.repositories.base import BaseRepository
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.models.order import Order


class CompanyRepository(BaseRepository[Company]):
    """
    Repository for company data access operations.
    
    Provides CRUD operations and specialized queries for companies in the
    hierarchical contact system. All operations enforce multi-tenant isolation
    through tenant_id filtering.
    
    Methods:
        get_by_name: Find company by name within a tenant
        get_with_contacts: Get company with contacts relationship loaded
        get_contacts: Get all contacts for a specific company
        get_balance: Calculate total order value for a company (aggregated from all contacts)
        get_order_count: Count total orders for a company (across all contacts)
        get_contact_count: Count total contacts for a company
        has_contacts: Check if company has any contacts
        search: Search companies by name
    
    Requirements: 1.3, 2.1, 2.2, 4.1, 4.3
    """
    
    def __init__(self, db: Session):
        super().__init__(Company, db)
    
    def get_by_name(
        self,
        name: str,
        tenant_id: int
    ) -> Optional[Company]:
        """
        Get company by name within a tenant.
        
        Company names are unique per tenant due to database constraint.
        
        Args:
            name: Company name
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Company if found, None otherwise
        
        Requirements: 1.3
        """
        return self.db.query(Company).filter(
            Company.name == name,
            Company.tenant_id == tenant_id
        ).first()
    
    def get_with_contacts(
        self,
        company_id: int,
        tenant_id: int
    ) -> Optional[Company]:
        """
        Get company with contacts relationship eagerly loaded.
        
        Uses joinedload to avoid N+1 query problems when accessing
        the company's contacts.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Company with contacts loaded, or None if not found
        
        Requirements: 1.3, 4.1, 7.2
        """
        return self.db.query(Company).options(
            joinedload(Company.contacts)
        ).filter(
            Company.id == company_id,
            Company.tenant_id == tenant_id
        ).first()
    
    def get_contacts(
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
    
    def get_balance(self, company_id: int, tenant_id: int) -> Decimal:
        """
        Calculate total balance (sum of order values) for a company.
        
        Aggregates the price from all orders placed by all contacts
        associated with this company. This is the primary balance calculation
        method that reflects the total business value of the company.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Total balance as a Decimal, or 0.00 if no orders exist
        
        Requirements: 2.1, 2.2, 4.3
        """
        balance = self.db.query(func.sum(Order.price)).filter(
            Order.company_id == company_id,
            Order.tenant_id == tenant_id
        ).scalar()
        return Decimal(str(balance)) if balance is not None else Decimal('0.00')
    
    def get_order_count(self, company_id: int, tenant_id: int) -> int:
        """
        Count total number of orders for a company across all contacts.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Number of orders placed by all contacts of the company
        
        Requirements: 4.1, 4.3
        """
        return self.db.query(Order).filter(
            Order.company_id == company_id,
            Order.tenant_id == tenant_id
        ).count()
    
    def get_contact_count(self, company_id: int, tenant_id: int) -> int:
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
    
    def has_contacts(self, company_id: int, tenant_id: int) -> bool:
        """
        Check if company has any contacts.
        
        Useful for validation before deleting a company or for
        displaying company status in the UI.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            True if company has contacts, False otherwise
        
        Requirements: 1.6
        """
        count = self.db.query(Contact).filter(
            Contact.company_id == company_id,
            Contact.tenant_id == tenant_id
        ).count()
        return count > 0
    
    def search(
        self,
        tenant_id: int,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Company]:
        """
        Search companies by name.
        
        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            search_term: Search term to match against company name
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of companies matching the search criteria
        
        Requirements: 1.3
        """
        return self.db.query(Company).filter(
            Company.tenant_id == tenant_id,
            Company.name.ilike(f"%{search_term}%")
        ).offset(skip).limit(limit).all()
