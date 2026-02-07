"""Company business logic service"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from decimal import Decimal
from app.data.repositories.company_repository import CompanyRepository
from app.data.repositories.contact_repository import ContactRepository
from app.data.models.company import Company
from app.data.models.order import Order
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, ContactSummary
from app.schemas.order import OrderResponse
from app.domain.exceptions import ResourceNotFoundError, DuplicateResourceError, ValidationError


class CompanyService:
    """
    Service for company business logic.
    
    Implements business logic for company CRUD operations, balance aggregation,
    contact and order aggregation, and company-wide statistics. All operations
    enforce multi-tenant isolation and maintain data integrity.
    
    Requirements: 2.1, 2.2, 4.1, 4.2, 4.3
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = CompanyRepository(db)
        self.contact_repository = ContactRepository(db)
    
    def get_all_companies(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        include_balance: bool = False
    ) -> List[CompanyResponse]:
        """
        Get all companies for a tenant with optional search and balance calculation.
        
        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            search: Optional search term to filter by name
            include_balance: Whether to calculate and include balance for each company
        
        Returns:
            List of company responses with optional balance information
        
        Requirements: 2.1, 4.3
        """
        if search:
            companies = self.repository.search(tenant_id, search, skip, limit)
        else:
            companies = self.repository.get_all(tenant_id, skip, limit)
        
        result = []
        for company in companies:
            company_dict = self._to_response_dict(company, include_balance, tenant_id)
            result.append(CompanyResponse(**company_dict))
        
        return result
    
    def get_company_by_id(
        self,
        company_id: int,
        tenant_id: int,
        include_contacts: bool = False,
        include_balance: bool = True
    ) -> CompanyResponse:
        """
        Get a single company by ID with optional contacts and balance.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
            include_contacts: Whether to include list of contacts
            include_balance: Whether to calculate and include balance
        
        Returns:
            Company response with requested information
        
        Raises:
            ResourceNotFoundError: If company is not found
        
        Requirements: 2.1, 4.1, 4.3
        """
        if include_contacts:
            company = self.repository.get_with_contacts(company_id, tenant_id)
        else:
            company = self.repository.get_by_id(company_id, tenant_id)
        
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        company_dict = self._to_response_dict(
            company,
            include_balance,
            tenant_id,
            include_contacts
        )
        return CompanyResponse(**company_dict)
    
    def create_company(self, company_data: CompanyCreate, tenant_id: int) -> CompanyResponse:
        """
        Create a new company with validation.
        
        Validates that no duplicate company name exists within the tenant.
        
        Args:
            company_data: Company creation data
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Created company response
        
        Raises:
            DuplicateResourceError: If company name already exists
        
        Requirements: 4.3
        """
        # Check for duplicate name
        existing = self.repository.get_by_name(company_data.name, tenant_id)
        if existing:
            raise DuplicateResourceError("Company", "name", company_data.name)
        
        # Create company
        company = Company(
            **company_data.dict(),
            tenant_id=tenant_id
        )
        company = self.repository.create(company)
        
        company_dict = self._to_response_dict(company, False, tenant_id)
        return CompanyResponse(**company_dict)
    
    def update_company(
        self,
        company_id: int,
        company_data: CompanyUpdate,
        tenant_id: int
    ) -> CompanyResponse:
        """
        Update an existing company with validation.
        
        Validates that:
        - Company exists and belongs to the tenant
        - If name is being changed, no duplicate exists
        
        Args:
            company_id: ID of the company to update
            company_data: Company update data
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Updated company response
        
        Raises:
            ResourceNotFoundError: If company is not found
            DuplicateResourceError: If new name already exists
        
        Requirements: 4.3
        """
        company = self.repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        # Check for duplicate name if changing
        if company_data.name and company_data.name != company.name:
            existing = self.repository.get_by_name(company_data.name, tenant_id)
            if existing and existing.id != company_id:
                raise DuplicateResourceError("Company", "name", company_data.name)
        
        # Update fields
        for key, value in company_data.dict(exclude_unset=True).items():
            setattr(company, key, value)
        
        company = self.repository.update(company)
        
        company_dict = self._to_response_dict(company, True, tenant_id)
        return CompanyResponse(**company_dict)
    
    def delete_company(self, company_id: int, tenant_id: int) -> None:
        """
        Delete a company with validation.
        
        Business rule: Cannot delete company with existing contacts due to
        cascade constraints and data integrity requirements.
        
        Args:
            company_id: ID of the company to delete
            tenant_id: Tenant ID for multi-tenant isolation
        
        Raises:
            ResourceNotFoundError: If company is not found
            ValidationError: If company has existing contacts
        
        Requirements: 4.3
        """
        company = self.repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        # Business rule: Cannot delete company with contacts
        if self.repository.has_contacts(company_id, tenant_id):
            raise ValidationError("Cannot delete company with existing contacts")
        
        self.repository.delete(company)
    
    def get_company_balance(self, company_id: int, tenant_id: int) -> Decimal:
        """
        Calculate aggregated balance for a company.
        
        Sums all order values from all contacts associated with the company.
        This is the primary balance calculation that reflects total business
        value per company.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Total balance as Decimal
        
        Raises:
            ResourceNotFoundError: If company is not found
        
        Requirements: 2.1, 2.2, 4.3
        """
        company = self.repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        return self.repository.get_balance(company_id, tenant_id)
    
    def get_company_contacts(
        self,
        company_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ContactSummary]:
        """
        Get all contacts for a specific company.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of contact summaries
        
        Raises:
            ResourceNotFoundError: If company is not found
        
        Requirements: 4.1, 4.3
        """
        company = self.repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        contacts = self.repository.get_contacts(company_id, tenant_id, skip, limit)
        
        result = []
        for contact in contacts:
            result.append(ContactSummary(
                id=contact.id,
                name=contact.name,
                email=contact.email,
                phone=contact.phone
            ))
        
        return result
    
    def get_company_orders(
        self,
        company_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
        group_by_contact: bool = False
    ) -> List[OrderResponse]:
        """
        Get all orders for a company across all contacts.
        
        Returns orders in chronological order (most recent first). Can optionally
        group by contact for display purposes.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            group_by_contact: Whether to group orders by contact
        
        Returns:
            List of order responses in chronological order
        
        Raises:
            ResourceNotFoundError: If company is not found
        
        Requirements: 4.1, 4.2, 4.3
        """
        company = self.repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        # Query orders for this company
        query = self.db.query(Order).filter(
            Order.company_id == company_id,
            Order.tenant_id == tenant_id
        )
        
        if group_by_contact:
            # Order by contact_id first, then by created_at
            query = query.order_by(Order.contact_id, desc(Order.created_at))
        else:
            # Just chronological order
            query = query.order_by(desc(Order.created_at))
        
        orders = query.offset(skip).limit(limit).all()
        
        # Convert to response schema
        result = []
        for order in orders:
            order_dict = {
                "id": order.id,
                "order_number": order.order_number,
                "tenant_id": order.tenant_id,
                "contact_id": order.contact_id,
                "company_id": order.company_id,
                "product_description": order.product_description,
                "specifications": order.specifications,
                "quantity": order.quantity,
                "price": order.price,
                "status": order.status,
                "due_date": order.due_date,
                "metal_type": order.metal_type,
                "target_weight_per_piece": order.target_weight_per_piece,
                "initial_total_weight": order.initial_total_weight,
                "created_at": order.created_at,
                "updated_at": order.updated_at
            }
            result.append(OrderResponse(**order_dict))
        
        return result
    
    def get_company_statistics(self, company_id: int, tenant_id: int) -> dict:
        """
        Get comprehensive statistics for a company.
        
        Returns aggregated metrics including:
        - Total balance (sum of all order values)
        - Total number of contacts
        - Total number of orders
        - Average order value
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Dictionary with company statistics
        
        Raises:
            ResourceNotFoundError: If company is not found
        
        Requirements: 4.3
        """
        company = self.repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        balance = self.repository.get_balance(company_id, tenant_id)
        contact_count = self.repository.get_contact_count(company_id, tenant_id)
        order_count = self.repository.get_order_count(company_id, tenant_id)
        
        average_order_value = Decimal('0.00')
        if order_count > 0:
            average_order_value = balance / order_count
        
        return {
            "company_id": company_id,
            "total_balance": float(balance),
            "contact_count": contact_count,
            "order_count": order_count,
            "average_order_value": float(average_order_value)
        }
    
    def _to_response_dict(
        self,
        company: Company,
        include_balance: bool,
        tenant_id: int,
        include_contacts: bool = False
    ) -> dict:
        """
        Convert company model to response dictionary.
        
        Args:
            company: Company model instance
            include_balance: Whether to calculate and include balance
            tenant_id: Tenant ID for balance calculation
            include_contacts: Whether to include contacts list
        
        Returns:
            Dictionary suitable for CompanyResponse schema
        """
        response_dict = {
            "id": company.id,
            "tenant_id": company.tenant_id,
            "name": company.name,
            "email": company.email,
            "phone": company.phone,
            "address": company.address,
            "created_at": company.created_at,
            "updated_at": company.updated_at
        }
        
        # Add balance if requested
        if include_balance:
            balance = self.repository.get_balance(company.id, tenant_id)
            response_dict["total_balance"] = float(balance)
        
        # Add contacts if requested and loaded
        if include_contacts and hasattr(company, 'contacts') and company.contacts:
            response_dict["contacts"] = [
                ContactSummary(
                    id=contact.id,
                    name=contact.name,
                    email=contact.email,
                    phone=contact.phone
                )
                for contact in company.contacts
            ]
        
        return response_dict
