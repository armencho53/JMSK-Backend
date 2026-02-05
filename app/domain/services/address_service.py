"""Address business logic service"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.data.repositories.address_repository import AddressRepository
from app.data.repositories.company_repository import CompanyRepository
from app.data.models.address import Address
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse
from app.domain.exceptions import ResourceNotFoundError, ValidationError


class AddressService:
    """
    Service for address business logic.
    
    Implements business logic for address CRUD operations, default address
    management, address validation, and shipment address population. All
    operations enforce multi-tenant isolation and maintain data integrity.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = AddressRepository(db)
        self.company_repository = CompanyRepository(db)
    
    def get_company_addresses(
        self,
        company_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[AddressResponse]:
        """
        Get all addresses for a specific company.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
        
        Returns:
            List of address responses
        
        Raises:
            ResourceNotFoundError: If company is not found
        
        Requirements: 5.1
        """
        # Validate company exists
        company = self.company_repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        addresses = self.repository.get_by_company(company_id, tenant_id, skip, limit)
        
        return [self._to_response(address) for address in addresses]
    
    def get_address_by_id(self, address_id: int, tenant_id: int) -> AddressResponse:
        """
        Get a single address by ID.
        
        Args:
            address_id: ID of the address
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Address response
        
        Raises:
            ResourceNotFoundError: If address is not found
        
        Requirements: 5.1
        """
        address = self.repository.get_by_id(address_id, tenant_id)
        if not address:
            raise ResourceNotFoundError("Address", address_id)
        
        return self._to_response(address)
    
    def get_default_address(self, company_id: int, tenant_id: int) -> Optional[AddressResponse]:
        """
        Get the default address for a company.
        
        This address is automatically populated during shipment creation.
        Returns None if no default address is set.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Default address response if found, None otherwise
        
        Raises:
            ResourceNotFoundError: If company is not found
        
        Requirements: 5.1, 5.2
        """
        # Validate company exists
        company = self.company_repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        address = self.repository.get_default_address(company_id, tenant_id)
        
        return self._to_response(address) if address else None
    
    def create_address(
        self,
        company_id: int,
        address_data: AddressCreate,
        tenant_id: int,
        set_as_default: bool = False
    ) -> AddressResponse:
        """
        Create a new address for a company with validation.
        
        Validates that:
        - Company exists and belongs to the tenant
        - All required address fields are provided
        - Address data is complete and valid
        
        Args:
            company_id: ID of the company
            address_data: Address creation data
            tenant_id: Tenant ID for multi-tenant isolation
            set_as_default: Whether to set this address as the company's default
        
        Returns:
            Created address response
        
        Raises:
            ResourceNotFoundError: If company is not found
            ValidationError: If address data is incomplete or invalid
        
        Requirements: 5.1, 5.2, 5.5
        """
        # Validate company exists
        company = self.company_repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        # Validate address completeness
        self._validate_address_completeness(address_data)
        
        # Create address
        address = Address(
            company_id=company_id,
            tenant_id=tenant_id,
            street_address=address_data.street_address,
            city=address_data.city,
            state=address_data.state,
            zip_code=address_data.zip_code,
            country=address_data.country or "USA",
            is_default=set_as_default
        )
        
        # If setting as default, unset other defaults first
        if set_as_default:
            self.repository.unset_default_addresses(company_id, tenant_id)
        
        address = self.repository.create(address)
        
        return self._to_response(address)
    
    def update_address(
        self,
        address_id: int,
        address_data: AddressUpdate,
        tenant_id: int
    ) -> AddressResponse:
        """
        Update an existing address with validation.
        
        Validates that:
        - Address exists and belongs to the tenant
        - Updated address data is complete and valid
        
        Args:
            address_id: ID of the address to update
            address_data: Address update data
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Updated address response
        
        Raises:
            ResourceNotFoundError: If address is not found
            ValidationError: If updated address data is incomplete or invalid
        
        Requirements: 5.1, 5.4, 5.5
        """
        address = self.repository.get_by_id(address_id, tenant_id)
        if not address:
            raise ResourceNotFoundError("Address", address_id)
        
        # Validate address completeness if any address fields are being updated
        if any([
            address_data.street_address,
            address_data.city,
            address_data.state,
            address_data.zip_code
        ]):
            # Create a merged version for validation
            merged_data = AddressCreate(
                street_address=address_data.street_address or address.street_address,
                city=address_data.city or address.city,
                state=address_data.state or address.state,
                zip_code=address_data.zip_code or address.zip_code,
                country=address_data.country or address.country
            )
            self._validate_address_completeness(merged_data)
        
        # Update fields
        for key, value in address_data.dict(exclude_unset=True).items():
            if key == "is_default" and value is True:
                # If setting as default, unset other defaults first
                self.repository.unset_default_addresses(address.company_id, tenant_id)
            setattr(address, key, value)
        
        address = self.repository.update(address)
        
        return self._to_response(address)
    
    def delete_address(self, address_id: int, tenant_id: int) -> None:
        """
        Delete an address with validation.
        
        Business rule: Cannot delete address that is currently set as a
        company's default address. User must set a different default first.
        
        Args:
            address_id: ID of the address to delete
            tenant_id: Tenant ID for multi-tenant isolation
        
        Raises:
            ResourceNotFoundError: If address is not found
            ValidationError: If address is currently set as default
        
        Requirements: 5.1, 5.4
        """
        address = self.repository.get_by_id(address_id, tenant_id)
        if not address:
            raise ResourceNotFoundError("Address", address_id)
        
        # Business rule: Cannot delete default address
        if address.is_default:
            raise ValidationError(
                "Cannot delete default address. Please set a different address as default first."
            )
        
        self.repository.delete(address)
    
    def set_default_address(
        self,
        address_id: int,
        company_id: int,
        tenant_id: int
    ) -> AddressResponse:
        """
        Set an address as the default for its company.
        
        This address will be automatically populated during shipment creation.
        Only one address can be default per company.
        
        Args:
            address_id: ID of the address to set as default
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Updated address response
        
        Raises:
            ResourceNotFoundError: If address or company is not found
            ValidationError: If address doesn't belong to the specified company
        
        Requirements: 5.2, 5.4
        """
        # Validate company exists
        company = self.company_repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        # Validate address exists and belongs to company
        address = self.repository.get_by_id(address_id, tenant_id)
        if not address:
            raise ResourceNotFoundError("Address", address_id)
        
        if address.company_id != company_id:
            raise ValidationError("Address does not belong to the specified company")
        
        # Set as default (this also unsets other defaults)
        address = self.repository.set_default_address(address_id, company_id, tenant_id)
        
        return self._to_response(address)
    
    def populate_shipment_address(
        self,
        company_id: int,
        tenant_id: int
    ) -> Optional[dict]:
        """
        Get default address for automatic shipment population.
        
        Returns the company's default address in a format suitable for
        populating shipment forms. Returns None if no default address exists.
        
        This method supports the requirement that shipment addresses are
        automatically populated but can be modified for individual shipments.
        
        Args:
            company_id: ID of the company
            tenant_id: Tenant ID for multi-tenant isolation
        
        Returns:
            Dictionary with address fields, or None if no default address
        
        Raises:
            ResourceNotFoundError: If company is not found
        
        Requirements: 5.2, 5.3
        """
        # Validate company exists
        company = self.company_repository.get_by_id(company_id, tenant_id)
        if not company:
            raise ResourceNotFoundError("Company", company_id)
        
        address = self.repository.get_default_address(company_id, tenant_id)
        
        if not address:
            return None
        
        return {
            "street_address": address.street_address,
            "city": address.city,
            "state": address.state,
            "zip_code": address.zip_code,
            "country": address.country
        }
    
    def _validate_address_completeness(self, address_data: AddressCreate) -> None:
        """
        Validate that address has all required fields.
        
        Required fields: street_address, city, state, zip_code
        Optional fields: country (defaults to USA)
        
        Args:
            address_data: Address data to validate
        
        Raises:
            ValidationError: If any required field is missing or empty
        
        Requirements: 5.5
        """
        errors = []
        
        if not address_data.street_address or not address_data.street_address.strip():
            errors.append("street_address is required")
        
        if not address_data.city or not address_data.city.strip():
            errors.append("city is required")
        
        if not address_data.state or not address_data.state.strip():
            errors.append("state is required")
        
        if not address_data.zip_code or not address_data.zip_code.strip():
            errors.append("zip_code is required")
        
        if errors:
            raise ValidationError(f"Address validation failed: {', '.join(errors)}")
    
    def _to_response(self, address: Address) -> AddressResponse:
        """
        Convert address model to response schema.
        
        Args:
            address: Address model instance
        
        Returns:
            AddressResponse instance
        """
        return AddressResponse(
            id=address.id,
            tenant_id=address.tenant_id,
            company_id=address.company_id,
            street_address=address.street_address,
            city=address.city,
            state=address.state,
            zip_code=address.zip_code,
            country=address.country,
            is_default=address.is_default,
            created_at=address.created_at
        )
