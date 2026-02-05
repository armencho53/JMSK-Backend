"""
Unit tests for Address Pydantic schemas.

Tests validation logic for address creation, updates, and responses.
Validates requirement 5.5: Address completeness validation.
"""
import pytest
from pydantic import ValidationError
from datetime import datetime
from app.schemas.address import (
    AddressBase,
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    AddressListResponse,
    CompanySummary
)


class TestAddressBase:
    """Test AddressBase schema validation."""
    
    def test_valid_address_base(self):
        """Test creating a valid AddressBase with all required fields."""
        address = AddressBase(
            street_address="123 Main St",
            city="New York",
            state="NY",
            zip_code="10001",
            country="USA",
            is_default=True
        )
        assert address.street_address == "123 Main St"
        assert address.city == "New York"
        assert address.state == "NY"
        assert address.zip_code == "10001"
        assert address.country == "USA"
        assert address.is_default is True
    
    def test_address_base_with_defaults(self):
        """Test AddressBase with default values for optional fields."""
        address = AddressBase(
            street_address="456 Oak Ave",
            city="Los Angeles",
            state="CA",
            zip_code="90001"
        )
        assert address.country == "USA"  # Default value
        assert address.is_default is False  # Default value
    
    def test_address_base_strips_whitespace(self):
        """Test that address fields strip leading/trailing whitespace."""
        address = AddressBase(
            street_address="  789 Pine Rd  ",
            city="  Chicago  ",
            state="  IL  ",
            zip_code="  60601  ",
            country="  USA  "
        )
        assert address.street_address == "789 Pine Rd"
        assert address.city == "Chicago"
        assert address.state == "IL"
        assert address.zip_code == "60601"
        assert address.country == "USA"
    
    def test_address_base_missing_street_address(self):
        """Test that street_address is required."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                city="Boston",
                state="MA",
                zip_code="02101"
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('street_address',) for e in errors)
    
    def test_address_base_missing_city(self):
        """Test that city is required."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="123 Main St",
                state="MA",
                zip_code="02101"
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('city',) for e in errors)
    
    def test_address_base_missing_state(self):
        """Test that state is required."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="123 Main St",
                city="Boston",
                zip_code="02101"
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('state',) for e in errors)
    
    def test_address_base_missing_zip_code(self):
        """Test that zip_code is required."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="123 Main St",
                city="Boston",
                state="MA"
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('zip_code',) for e in errors)
    
    def test_address_base_empty_street_address(self):
        """Test that street_address cannot be empty or whitespace."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="   ",
                city="Boston",
                state="MA",
                zip_code="02101"
            )
        errors = exc_info.value.errors()
        assert any('empty' in str(e['msg']).lower() for e in errors)
    
    def test_address_base_empty_city(self):
        """Test that city cannot be empty or whitespace."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="123 Main St",
                city="   ",
                state="MA",
                zip_code="02101"
            )
        errors = exc_info.value.errors()
        assert any('empty' in str(e['msg']).lower() for e in errors)
    
    def test_address_base_empty_state(self):
        """Test that state cannot be empty or whitespace."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="123 Main St",
                city="Boston",
                state="   ",
                zip_code="02101"
            )
        errors = exc_info.value.errors()
        assert any('empty' in str(e['msg']).lower() for e in errors)
    
    def test_address_base_empty_zip_code(self):
        """Test that zip_code cannot be empty or whitespace."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="123 Main St",
                city="Boston",
                state="MA",
                zip_code="   "
            )
        errors = exc_info.value.errors()
        # Whitespace-only zip code will fail either min_length or custom validation
        assert any('empty' in str(e['msg']).lower() or 'at least 5' in str(e['msg']).lower() for e in errors)
    
    def test_address_base_zip_code_too_short(self):
        """Test that zip_code must be at least 5 characters."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="123 Main St",
                city="Boston",
                state="MA",
                zip_code="123"
            )
        errors = exc_info.value.errors()
        assert any('at least 5' in str(e['msg']).lower() for e in errors)
    
    def test_address_base_zip_code_minimum_length(self):
        """Test that zip_code with exactly 5 characters is valid."""
        address = AddressBase(
            street_address="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101"
        )
        assert address.zip_code == "02101"
    
    def test_address_base_zip_code_with_extension(self):
        """Test that zip_code can include extension (ZIP+4 format)."""
        address = AddressBase(
            street_address="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101-1234"
        )
        assert address.zip_code == "02101-1234"
    
    def test_address_base_empty_country(self):
        """Test that country cannot be empty or whitespace if provided."""
        with pytest.raises(ValidationError) as exc_info:
            AddressBase(
                street_address="123 Main St",
                city="Boston",
                state="MA",
                zip_code="02101",
                country="   "
            )
        errors = exc_info.value.errors()
        assert any('empty' in str(e['msg']).lower() for e in errors)
    
    def test_address_base_max_length_validation(self):
        """Test that fields respect maximum length constraints."""
        # Test street_address max length (255)
        long_street = "A" * 256
        with pytest.raises(ValidationError):
            AddressBase(
                street_address=long_street,
                city="Boston",
                state="MA",
                zip_code="02101"
            )
        
        # Test city max length (100)
        long_city = "B" * 101
        with pytest.raises(ValidationError):
            AddressBase(
                street_address="123 Main St",
                city=long_city,
                state="MA",
                zip_code="02101"
            )
        
        # Test state max length (50)
        long_state = "C" * 51
        with pytest.raises(ValidationError):
            AddressBase(
                street_address="123 Main St",
                city="Boston",
                state=long_state,
                zip_code="02101"
            )
        
        # Test zip_code max length (20)
        long_zip = "D" * 21
        with pytest.raises(ValidationError):
            AddressBase(
                street_address="123 Main St",
                city="Boston",
                state="MA",
                zip_code=long_zip
            )


class TestAddressCreate:
    """Test AddressCreate schema validation."""
    
    def test_valid_address_create(self):
        """Test creating a valid AddressCreate with all required fields."""
        address = AddressCreate(
            street_address="123 Main St",
            city="New York",
            state="NY",
            zip_code="10001",
            country="USA",
            is_default=True,
            company_id=1
        )
        assert address.street_address == "123 Main St"
        assert address.city == "New York"
        assert address.state == "NY"
        assert address.zip_code == "10001"
        assert address.country == "USA"
        assert address.is_default is True
        assert address.company_id == 1
    
    def test_address_create_missing_company_id(self):
        """Test that company_id is required for AddressCreate."""
        with pytest.raises(ValidationError) as exc_info:
            AddressCreate(
                street_address="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001"
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('company_id',) for e in errors)
    
    def test_address_create_invalid_company_id(self):
        """Test that company_id must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            AddressCreate(
                street_address="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
                company_id=0
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('company_id',) for e in errors)
        
        with pytest.raises(ValidationError) as exc_info:
            AddressCreate(
                street_address="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
                company_id=-1
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('company_id',) for e in errors)
    
    def test_address_create_inherits_base_validation(self):
        """Test that AddressCreate inherits all validation from AddressBase."""
        # Test missing required field
        with pytest.raises(ValidationError):
            AddressCreate(
                city="New York",
                state="NY",
                zip_code="10001",
                company_id=1
            )
        
        # Test empty field
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="   ",
                city="New York",
                state="NY",
                zip_code="10001",
                company_id=1
            )
        
        # Test short zip code
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="123 Main St",
                city="New York",
                state="NY",
                zip_code="123",
                company_id=1
            )


class TestAddressUpdate:
    """Test AddressUpdate schema validation."""
    
    def test_address_update_all_fields(self):
        """Test updating all fields in AddressUpdate."""
        address = AddressUpdate(
            street_address="456 Oak Ave",
            city="Los Angeles",
            state="CA",
            zip_code="90001",
            country="USA",
            is_default=True
        )
        assert address.street_address == "456 Oak Ave"
        assert address.city == "Los Angeles"
        assert address.state == "CA"
        assert address.zip_code == "90001"
        assert address.country == "USA"
        assert address.is_default is True
    
    def test_address_update_partial_fields(self):
        """Test that AddressUpdate allows partial updates."""
        # Update only street address
        address1 = AddressUpdate(street_address="789 Pine Rd")
        assert address1.street_address == "789 Pine Rd"
        assert address1.city is None
        assert address1.state is None
        
        # Update only city and state
        address2 = AddressUpdate(city="Chicago", state="IL")
        assert address2.street_address is None
        assert address2.city == "Chicago"
        assert address2.state == "IL"
        
        # Update only is_default
        address3 = AddressUpdate(is_default=True)
        assert address3.is_default is True
        assert address3.street_address is None
    
    def test_address_update_no_fields(self):
        """Test that AddressUpdate can be created with no fields (empty update)."""
        address = AddressUpdate()
        assert address.street_address is None
        assert address.city is None
        assert address.state is None
        assert address.zip_code is None
        assert address.country is None
        assert address.is_default is None
    
    def test_address_update_strips_whitespace(self):
        """Test that AddressUpdate strips whitespace from provided fields."""
        address = AddressUpdate(
            street_address="  123 Main St  ",
            city="  Boston  ",
            state="  MA  "
        )
        assert address.street_address == "123 Main St"
        assert address.city == "Boston"
        assert address.state == "MA"
    
    def test_address_update_empty_fields_rejected(self):
        """Test that empty or whitespace-only fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AddressUpdate(street_address="   ")
        errors = exc_info.value.errors()
        assert any('empty' in str(e['msg']).lower() for e in errors)
        
        with pytest.raises(ValidationError):
            AddressUpdate(city="   ")
        
        with pytest.raises(ValidationError):
            AddressUpdate(state="   ")
        
        with pytest.raises(ValidationError):
            AddressUpdate(zip_code="   ")
        
        with pytest.raises(ValidationError):
            AddressUpdate(country="   ")
    
    def test_address_update_zip_code_validation(self):
        """Test that zip_code validation applies to updates."""
        # Too short
        with pytest.raises(ValidationError) as exc_info:
            AddressUpdate(zip_code="123")
        errors = exc_info.value.errors()
        assert any('at least 5' in str(e['msg']).lower() for e in errors)
        
        # Valid
        address = AddressUpdate(zip_code="12345")
        assert address.zip_code == "12345"
        
        # Valid with extension
        address = AddressUpdate(zip_code="12345-6789")
        assert address.zip_code == "12345-6789"


class TestAddressResponse:
    """Test AddressResponse schema."""
    
    def test_address_response_from_dict(self):
        """Test creating AddressResponse from dictionary (simulating ORM model)."""
        data = {
            "id": 1,
            "tenant_id": 100,
            "company_id": 5,
            "street_address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "country": "USA",
            "is_default": True,
            "created_at": datetime(2024, 1, 1, 12, 0, 0)
        }
        address = AddressResponse(**data)
        assert address.id == 1
        assert address.tenant_id == 100
        assert address.company_id == 5
        assert address.street_address == "123 Main St"
        assert address.city == "New York"
        assert address.state == "NY"
        assert address.zip_code == "10001"
        assert address.country == "USA"
        assert address.is_default is True
        assert address.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert address.company is None
    
    def test_address_response_with_company(self):
        """Test AddressResponse with company relationship."""
        company_data = {
            "id": 5,
            "name": "Acme Corp"
        }
        data = {
            "id": 1,
            "tenant_id": 100,
            "company_id": 5,
            "street_address": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "country": "USA",
            "is_default": True,
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "company": company_data
        }
        address = AddressResponse(**data)
        assert address.company is not None
        assert address.company.id == 5
        assert address.company.name == "Acme Corp"


class TestAddressListResponse:
    """Test AddressListResponse schema."""
    
    def test_address_list_response(self):
        """Test creating AddressListResponse with multiple addresses."""
        addresses_data = [
            {
                "id": 1,
                "tenant_id": 100,
                "company_id": 5,
                "street_address": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "country": "USA",
                "is_default": True,
                "created_at": datetime(2024, 1, 1, 12, 0, 0)
            },
            {
                "id": 2,
                "tenant_id": 100,
                "company_id": 5,
                "street_address": "456 Oak Ave",
                "city": "Los Angeles",
                "state": "CA",
                "zip_code": "90001",
                "country": "USA",
                "is_default": False,
                "created_at": datetime(2024, 1, 2, 12, 0, 0)
            }
        ]
        
        response = AddressListResponse(
            addresses=[AddressResponse(**addr) for addr in addresses_data],
            total=2,
            page=1,
            page_size=50
        )
        
        assert len(response.addresses) == 2
        assert response.total == 2
        assert response.page == 1
        assert response.page_size == 50
        assert response.addresses[0].id == 1
        assert response.addresses[1].id == 2
    
    def test_address_list_response_empty(self):
        """Test AddressListResponse with no addresses."""
        response = AddressListResponse(
            addresses=[],
            total=0,
            page=1,
            page_size=50
        )
        assert len(response.addresses) == 0
        assert response.total == 0


class TestCompanySummary:
    """Test CompanySummary schema."""
    
    def test_company_summary(self):
        """Test creating CompanySummary."""
        company = CompanySummary(id=1, name="Acme Corp")
        assert company.id == 1
        assert company.name == "Acme Corp"


class TestAddressValidationRequirement55:
    """
    Test suite specifically for Requirement 5.5: Address Validation Completeness.
    
    Validates: Requirements 5.5
    """
    
    def test_complete_address_accepted(self):
        """Test that complete addresses with all required fields are accepted."""
        # Minimum required fields
        address = AddressCreate(
            street_address="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101",
            company_id=1
        )
        assert address.street_address == "123 Main St"
        assert address.city == "Boston"
        assert address.state == "MA"
        assert address.zip_code == "02101"
        assert address.country == "USA"  # Default
        
        # All fields provided
        address_full = AddressCreate(
            street_address="456 Oak Ave",
            city="Los Angeles",
            state="CA",
            zip_code="90001-1234",
            country="USA",
            is_default=True,
            company_id=2
        )
        assert address_full.street_address == "456 Oak Ave"
        assert address_full.city == "Los Angeles"
        assert address_full.state == "CA"
        assert address_full.zip_code == "90001-1234"
        assert address_full.country == "USA"
        assert address_full.is_default is True
    
    def test_incomplete_address_rejected_missing_street(self):
        """Test that addresses missing street_address are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AddressCreate(
                city="Boston",
                state="MA",
                zip_code="02101",
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('street_address',) for e in errors)
    
    def test_incomplete_address_rejected_missing_city(self):
        """Test that addresses missing city are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AddressCreate(
                street_address="123 Main St",
                state="MA",
                zip_code="02101",
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('city',) for e in errors)
    
    def test_incomplete_address_rejected_missing_state(self):
        """Test that addresses missing state are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AddressCreate(
                street_address="123 Main St",
                city="Boston",
                zip_code="02101",
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('state',) for e in errors)
    
    def test_incomplete_address_rejected_missing_zip(self):
        """Test that addresses missing zip_code are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AddressCreate(
                street_address="123 Main St",
                city="Boston",
                state="MA",
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('zip_code',) for e in errors)
    
    def test_incomplete_address_rejected_empty_fields(self):
        """Test that addresses with empty/whitespace fields are rejected."""
        # Empty street address
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="",
                city="Boston",
                state="MA",
                zip_code="02101",
                company_id=1
            )
        
        # Whitespace-only city
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="123 Main St",
                city="   ",
                state="MA",
                zip_code="02101",
                company_id=1
            )
        
        # Empty state
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="123 Main St",
                city="Boston",
                state="",
                zip_code="02101",
                company_id=1
            )
        
        # Whitespace-only zip code
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="123 Main St",
                city="Boston",
                state="MA",
                zip_code="   ",
                company_id=1
            )
    
    def test_incomplete_address_rejected_invalid_zip_format(self):
        """Test that addresses with invalid zip code format are rejected."""
        # Too short (less than 5 characters)
        with pytest.raises(ValidationError) as exc_info:
            AddressCreate(
                street_address="123 Main St",
                city="Boston",
                state="MA",
                zip_code="1234",
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any('at least 5' in str(e['msg']).lower() for e in errors)
        
        # Empty after stripping
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="123 Main St",
                city="Boston",
                state="MA",
                zip_code="    ",
                company_id=1
            )
    
    def test_address_validation_for_shipment_creation(self):
        """
        Test address validation in the context of shipment creation.
        
        This simulates the requirement that addresses must be validated
        before allowing shipment creation.
        """
        # Valid address should pass validation
        valid_address = AddressCreate(
            street_address="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101",
            company_id=1
        )
        # If we get here without exception, validation passed
        assert valid_address is not None
        
        # Invalid addresses should fail validation
        invalid_addresses = [
            # Missing street
            {"city": "Boston", "state": "MA", "zip_code": "02101", "company_id": 1},
            # Missing city
            {"street_address": "123 Main St", "state": "MA", "zip_code": "02101", "company_id": 1},
            # Missing state
            {"street_address": "123 Main St", "city": "Boston", "zip_code": "02101", "company_id": 1},
            # Missing zip
            {"street_address": "123 Main St", "city": "Boston", "state": "MA", "company_id": 1},
            # Invalid zip (too short)
            {"street_address": "123 Main St", "city": "Boston", "state": "MA", "zip_code": "123", "company_id": 1},
        ]
        
        for invalid_data in invalid_addresses:
            with pytest.raises(ValidationError):
                AddressCreate(**invalid_data)
