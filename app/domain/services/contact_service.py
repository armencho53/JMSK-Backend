"""Contact business logic service"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.data.repositories.contact_repository import ContactRepository
from app.data.repositories.company_repository import CompanyRepository
from app.data.models.contact import Contact
from app.data.models.order import Order
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse, CompanySummary
from app.schemas.order import OrderResponse
from app.domain.exceptions import ResourceNotFoundError, DuplicateResourceError, ValidationError


class ContactService:
    """
    Service for contact business logic.
    
    Implements business logic for contact CRUD operations, company-contact
    relationship validation, and contact order history retrieval. All operations
    enforce multi-tenant isolation and maintain data integrity.
    
    Requirements: 1.4, 3.2, 6.4
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = ContactRepository(db)
        self.company_repository = CompanyRepository(db)
    
    def get_all_contacts(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        company_id: Optional[int] = None
    ) -> List[ContactResponse]:
        """
        Get all contacts for a tenant with optional search and company filter.
        
        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            search: Optional search term to filter by name or email
            company_id: Optional company ID to filter contacts by company
        
        Returns:
            List of contact responses with company information
        
        Requirements: 1.4, 6.4
        """
        if search:
            contacts = self.repository.search(tenant_id, search, company_id, skip, limit)
        elif company_id:
            contacts = self.repository.get_by_company(company_id, tenant_id, skip, limit)
        else:
            contacts = self.repository.get_all(tenant_id, skip, limit)
        
        # Enrich with company information
        result = []
        for contact in contacts:
            contact_dict = self._to_response_dict(contact)
            result.append(ContactResponse(**contact_dict))
        
        return result
    
    def get_contact_by_id(self, contact_id: int, tenant_id: int) -> ContactResponse:
        """
        Get a single contact by ID with company information.
        
        Args:
            contact_id: ID of the contact
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Contact response with company information
        
        Raises:
            ResourceNotFoundError: If contact is not found
        
        Requirements: 1.4, 6.4
        """
        contact = self.repository.get_with_company(contact_id, tenant_id)
        if not contact:
            raise ResourceNotFoundError("Contact", contact_id)
        
        contact_dict = self._to_response_dict(contact)
        return ContactResponse(**contact_dict)
    
    def create_contact(self, contact_data: ContactCreate, tenant_id: int) -> ContactResponse:
        """
        Create a new contact with company-contact relationship validation.
        
        Validates that:
        - The specified company exists and belongs to the same tenant
        - No duplicate email exists within the same company
        
        Args:
            contact_data: Contact creation data
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Created contact response with company information
        
        Raises:
            ResourceNotFoundError: If company is not found
            DuplicateResourceError: If email already exists within the company
        
        Requirements: 1.4, 6.4
        """
        # Validate company exists and belongs to tenant
        company = self.company_repository.get_by_id(contact_data.company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", contact_data.company_id)
        
        # Check for duplicate email within the same company
        if contact_data.email:
            existing = self.repository.get_by_email(
                contact_data.email,
                contact_data.company_id,
                tenant_id
            )
            if existing:
                raise DuplicateResourceError(
                    "Contact",
                    "email",
                    f"{contact_data.email} (within company {company.name})"
                )
        
        # Create contact
        contact = Contact(
            **contact_data.dict(),
            tenant_id=tenant_id
        )
        contact = self.repository.create(contact)
        
        # Reload with company relationship
        contact = self.repository.get_with_company(contact.id, tenant_id)
        contact_dict = self._to_response_dict(contact)
        return ContactResponse(**contact_dict)
    
    def update_contact(
        self,
        contact_id: int,
        contact_data: ContactUpdate,
        tenant_id: int
    ) -> ContactResponse:
        """
        Update an existing contact with validation.
        
        Validates that:
        - Contact exists and belongs to the tenant
        - If company_id is being changed, the new company exists
        - If email is being changed, no duplicate exists within the target company
        
        Args:
            contact_id: ID of the contact to update
            contact_data: Contact update data
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Updated contact response with company information
        
        Raises:
            ResourceNotFoundError: If contact or new company is not found
            DuplicateResourceError: If new email already exists within the company
        
        Requirements: 1.4, 6.4
        """
        contact = self.repository.get_by_id(contact_id, tenant_id)
        if not contact:
            raise ResourceNotFoundError("Contact", contact_id)
        
        # Determine target company_id (new or existing)
        target_company_id = contact_data.company_id if contact_data.company_id else contact.company_id
        
        # Validate new company if changing
        if contact_data.company_id and contact_data.company_id != contact.company_id:
            company = self.company_repository.get_by_id(contact_data.company_id, tenant_id)
            if not company:
                raise ResourceNotFoundError("Company", contact_data.company_id)
        
        # Check for duplicate email within target company if changing email
        if contact_data.email and contact_data.email != contact.email:
            existing = self.repository.get_by_email(
                contact_data.email,
                target_company_id,
                tenant_id
            )
            if existing and existing.id != contact_id:
                raise DuplicateResourceError(
                    "Contact",
                    "email",
                    f"{contact_data.email} (within target company)"
                )
        
        # Update fields
        for key, value in contact_data.dict(exclude_unset=True).items():
            setattr(contact, key, value)
        
        contact = self.repository.update(contact)
        
        # Reload with company relationship
        contact = self.repository.get_with_company(contact.id, tenant_id)
        contact_dict = self._to_response_dict(contact)
        return ContactResponse(**contact_dict)
    
    def delete_contact(self, contact_id: int, tenant_id: int) -> None:
        """
        Delete a contact with validation.
        
        Business rule: Cannot delete contact with existing orders to maintain
        referential integrity and historical data.
        
        Args:
            contact_id: ID of the contact to delete
            tenant_id: Tenant ID for multi-tenant isolation
        
        Raises:
            ResourceNotFoundError: If contact is not found
            ValidationError: If contact has existing orders
        
        Requirements: 1.4, 6.4
        """
        contact = self.repository.get_by_id(contact_id, tenant_id)
        if not contact:
            raise ResourceNotFoundError("Contact", contact_id)
        
        # Business rule: Cannot delete contact with orders
        if self.repository.has_orders(contact_id, tenant_id):
            raise ValidationError("Cannot delete contact with existing orders")
        
        self.repository.delete(contact)
    
    def get_contact_order_history(
        self,
        contact_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[OrderResponse]:
        """
        Get complete order history for a specific contact.
        
        Returns all orders placed by the contact in chronological order
        (most recent first). This enables tracking individual contact activity
        and viewing their complete transaction history.
        
        Args:
            contact_id: ID of the contact
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of order responses in chronological order
        
        Raises:
            ResourceNotFoundError: If contact is not found
        
        Requirements: 3.2, 6.4
        """
        # Validate contact exists
        contact = self.repository.get_by_id(contact_id, tenant_id)
        if not contact:
            raise ResourceNotFoundError("Contact", contact_id)
        
        # Query orders for this contact, ordered by created_at descending
        orders = self.db.query(Order).filter(
            Order.contact_id == contact_id,
            Order.tenant_id == tenant_id
        ).order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
        
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
                "metal_id": order.metal_id,
                "metal_name": order.metal.name if order.metal else None,
                "target_weight_per_piece": order.target_weight_per_piece,
                "initial_total_weight": order.initial_total_weight,
                "created_at": order.created_at,
                "updated_at": order.updated_at
            }
            result.append(OrderResponse(**order_dict))
        
        return result
    
    def _to_response_dict(self, contact: Contact) -> dict:
        """
        Convert contact model to response dictionary with company information.
        
        Args:
            contact: Contact model instance
        
        Returns:
            Dictionary suitable for ContactResponse schema
        """
        response_dict = {
            "id": contact.id,
            "tenant_id": contact.tenant_id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "company_id": contact.company_id,
            "created_at": contact.created_at,
            "updated_at": contact.updated_at
        }
        
        # Add company information if loaded
        if contact.company:
            response_dict["company"] = CompanySummary(
                id=contact.company.id,
                name=contact.company.name,
                email=contact.company.email,
                phone=contact.company.phone
            )
        
        return response_dict
