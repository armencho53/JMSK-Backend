"""Address repository for data access"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.data.repositories.base import BaseRepository
from app.data.models.address import Address


class AddressRepository(BaseRepository[Address]):
    """
    Repository for address data access operations.
    
    Provides CRUD operations and specialized queries for addresses in the
    hierarchical contact system. All operations enforce multi-tenant isolation
    through tenant_id filtering.
    
    Methods:
        get_by_company: Get all addresses for a specific company
        get_default_address: Get the default address for a company
        set_default_address: Set an address as the default for its company
        unset_default_addresses: Remove default status from all addresses for a company
        has_default_address: Check if a company has a default address
        count_by_company: Count addresses for a specific company
        is_referenced_as_default: Check if address is referenced as company default
    
    Requirements: 5.1, 5.2, 5.3, 5.4
    """
    
    def __init__(self, db: Session):
        super().__init__(Address, db)
    
    def get_by_company(
        self,
        company_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Address]:
        """
        Get all addresses for a specific company.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of addresses belonging to the company
        
        Requirements: 5.1
        """
        return self.db.query(Address).filter(
            Address.company_id == company_id,
            Address.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()
    
    def get_default_address(
        self,
        company_id: int,
        tenant_id: int
    ) -> Optional[Address]:
        """
        Get the default address for a company.
        
        Returns the address marked as default for the specified company.
        This address is automatically populated during shipment creation.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Default address if found, None otherwise
        
        Requirements: 5.1, 5.2
        """
        return self.db.query(Address).filter(
            Address.company_id == company_id,
            Address.tenant_id == tenant_id,
            Address.is_default == True
        ).first()
    
    def set_default_address(
        self,
        address_id: int,
        company_id: int,
        tenant_id: int
    ) -> Optional[Address]:
        """
        Set an address as the default for its company.
        
        This method:
        1. Unsets default status from all other addresses for the company
        2. Sets the specified address as default
        3. Returns the updated address
        
        Note: Database triggers also handle this logic, but this method
        provides explicit control for application-level operations.
        
        Args:
            address_id: ID of the address to set as default
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Updated address if found, None otherwise
        
        Requirements: 5.2, 5.4
        """
        # First, unset all default addresses for this company
        self.unset_default_addresses(company_id, tenant_id)
        
        # Then set the specified address as default
        address = self.db.query(Address).filter(
            Address.id == address_id,
            Address.company_id == company_id,
            Address.tenant_id == tenant_id
        ).first()
        
        if address:
            address.is_default = True
            self.db.commit()
            self.db.refresh(address)
        
        return address
    
    def unset_default_addresses(
        self,
        company_id: int,
        tenant_id: int
    ) -> int:
        """
        Remove default status from all addresses for a company.
        
        This is typically called before setting a new default address
        to ensure only one address is marked as default.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Number of addresses updated
        
        Requirements: 5.2
        """
        result = self.db.query(Address).filter(
            Address.company_id == company_id,
            Address.tenant_id == tenant_id,
            Address.is_default == True
        ).update({"is_default": False}, synchronize_session=False)
        
        self.db.commit()
        return result
    
    def has_default_address(
        self,
        company_id: int,
        tenant_id: int
    ) -> bool:
        """
        Check if a company has a default address.
        
        Useful for validation and UI display logic.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            True if company has a default address, False otherwise
        
        Requirements: 5.1
        """
        count = self.db.query(Address).filter(
            Address.company_id == company_id,
            Address.tenant_id == tenant_id,
            Address.is_default == True
        ).count()
        return count > 0
    
    def count_by_company(
        self,
        company_id: int,
        tenant_id: int
    ) -> int:
        """
        Count total number of addresses for a specific company.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Number of addresses belonging to the company
        
        Requirements: 5.1
        """
        return self.db.query(Address).filter(
            Address.company_id == company_id,
            Address.tenant_id == tenant_id
        ).count()
    
    def is_referenced_as_default(
        self,
        address_id: int,
        tenant_id: int
    ) -> bool:
        """
        Check if an address is referenced as a company's default address.
        
        This is used to prevent deletion of addresses that are actively
        referenced by companies. The database trigger also enforces this,
        but this method allows application-level validation.
        
        Args:
            address_id: ID of the address
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            True if address is referenced as default, False otherwise
        
        Requirements: 5.4
        """
        from app.data.models.company import Company
        
        count = self.db.query(Company).filter(
            Company.default_address_id == address_id,
            Company.tenant_id == tenant_id
        ).count()
        return count > 0
