"""
Unit tests for Company Pydantic schemas.

Tests validation rules, field requirements, and schema behavior for
Company-related schemas including CompanyCreate, CompanyUpdate, CompanyResponse,
and related summary schemas.

Requirements: 2.1, 4.3
"""
import pytest
from pydantic import ValidationError
from datetime import datetime
from decimal import Decimal
from app.schemas.company import (
    CompanyBase,
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    ContactSummary,
    AddressSummary,
    CustomerSummary,
    CompanyDetailResponse
)


class TestCompanyBase:
    """Test CompanyBase schema validation."""
    
    def test_valid_company_base(self):
        """Test creating CompanyBase with valid data."""
        company = CompanyBase(
            name="Acme Corp",
            address="123 Main St",
            phone="555-1234",
            email="info@acme.com"
        )
        assert company.name == "Acme Corp"
        assert company.address == "123 Main St"
        assert company.phone == "555-1234"
        assert company.email == "info@acme.com"
    
    def test_company_base_minimal_fields(self):
        """Test CompanyBase with only required fields."""
        company = CompanyBase(name="Minimal Corp")
        assert company.name == "Minimal Corp"
        assert company.address is None
        assert company.phone is None
        assert company.email is None
    
    def test_company_base_missing_name(self):
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyBase()
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('name',) for e in errors)
    
    def test_company_base_empty_name(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyBase(name="")
        errors = exc_info.value.errors()
        assert any('name' in str(e) for e in errors)
    
    def test_company_base_invalid_email(self):
        """Test that invalid email format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyBase(
                name="Test Corp",
                email="invalid-email"
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('email',) for e in errors)
    
    def test_company_base_valid_email_formats(self):
        """Test various valid email formats."""
        valid_emails = [
            "test@example.com",
            "user.name@example.co.uk",
            "user+tag@example.com"
        ]
        for email in valid_emails:
            company = CompanyBase(name="Test Corp", email=email)
            assert company.email == email


class TestCompanyCreate:
    """Test CompanyCreate schema."""
    
    def test_company_create_inherits_from_base(self):
        """Test that CompanyCreate inherits all fields from CompanyBase."""
        company = CompanyCreate(
            name="New Corp",
            address="456 Oak Ave",
            phone="555-5678",
            email="contact@newcorp.com"
        )
        assert company.name == "New Corp"
        assert company.address == "456 Oak Ave"
        assert company.phone == "555-5678"
        assert company.email == "contact@newcorp.com"
    
    def test_company_create_minimal(self):
        """Test creating company with minimal data."""
        company = CompanyCreate(name="Simple Corp")
        assert company.name == "Simple Corp"


class TestCompanyUpdate:
    """Test CompanyUpdate schema."""
    
    def test_company_update_all_fields_optional(self):
        """Test that all fields are optional in CompanyUpdate."""
        company = CompanyUpdate()
        assert company.name is None
        assert company.address is None
        assert company.phone is None
        assert company.email is None
    
    def test_company_update_partial_update(self):
        """Test updating only specific fields."""
        company = CompanyUpdate(name="Updated Corp")
        assert company.name == "Updated Corp"
        assert company.address is None
        assert company.phone is None
        assert company.email is None
    
    def test_company_update_all_fields(self):
        """Test updating all fields."""
        company = CompanyUpdate(
            name="Fully Updated Corp",
            address="789 Pine St",
            phone="555-9999",
            email="new@updated.com"
        )
        assert company.name == "Fully Updated Corp"
        assert company.address == "789 Pine St"
        assert company.phone == "555-9999"
        assert company.email == "new@updated.com"
    
    def test_company_update_invalid_email(self):
        """Test that invalid email is rejected in update."""
        with pytest.raises(ValidationError) as exc_info:
            CompanyUpdate(email="not-an-email")
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('email',) for e in errors)


class TestContactSummary:
    """Test ContactSummary schema."""
    
    def test_contact_summary_from_dict(self):
        """Test creating ContactSummary from dictionary."""
        data = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234"
        }
        contact = ContactSummary(**data)
        assert contact.id == 1
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"
        assert contact.phone == "555-1234"
    
    def test_contact_summary_minimal(self):
        """Test ContactSummary with minimal fields."""
        contact = ContactSummary(id=1, name="Jane Smith")
        assert contact.id == 1
        assert contact.name == "Jane Smith"
        assert contact.email is None
        assert contact.phone is None


class TestAddressSummary:
    """Test AddressSummary schema."""
    
    def test_address_summary_complete(self):
        """Test creating AddressSummary with all fields."""
        address = AddressSummary(
            id=1,
            street_address="123 Main St",
            city="New York",
            state="NY",
            zip_code="10001",
            country="USA",
            is_default=True
        )
        assert address.id == 1
        assert address.street_address == "123 Main St"
        assert address.city == "New York"
        assert address.state == "NY"
        assert address.zip_code == "10001"
        assert address.country == "USA"
        assert address.is_default is True
    
    def test_address_summary_not_default(self):
        """Test AddressSummary with is_default=False."""
        address = AddressSummary(
            id=2,
            street_address="456 Oak Ave",
            city="Los Angeles",
            state="CA",
            zip_code="90001",
            country="USA",
            is_default=False
        )
        assert address.is_default is False


class TestCompanyResponse:
    """Test CompanyResponse schema."""
    
    def test_company_response_basic(self):
        """Test CompanyResponse with basic fields."""
        now = datetime.utcnow()
        company = CompanyResponse(
            id=1,
            tenant_id=1,
            name="Response Corp",
            address="123 Test St",
            phone="555-0000",
            email="test@response.com",
            created_at=now,
            updated_at=now
        )
        assert company.id == 1
        assert company.tenant_id == 1
        assert company.name == "Response Corp"
        assert company.contacts is None
        assert company.addresses is None
        assert company.total_balance is None
    
    def test_company_response_with_contacts(self):
        """Test CompanyResponse with contacts list."""
        now = datetime.utcnow()
        contacts = [
            ContactSummary(id=1, name="Contact 1", email="c1@test.com"),
            ContactSummary(id=2, name="Contact 2", email="c2@test.com")
        ]
        company = CompanyResponse(
            id=1,
            tenant_id=1,
            name="Company with Contacts",
            created_at=now,
            updated_at=now,
            contacts=contacts
        )
        assert len(company.contacts) == 2
        assert company.contacts[0].name == "Contact 1"
        assert company.contacts[1].name == "Contact 2"
    
    def test_company_response_with_addresses(self):
        """Test CompanyResponse with addresses list."""
        now = datetime.utcnow()
        addresses = [
            AddressSummary(
                id=1,
                street_address="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
                country="USA",
                is_default=True
            ),
            AddressSummary(
                id=2,
                street_address="456 Oak Ave",
                city="Los Angeles",
                state="CA",
                zip_code="90001",
                country="USA",
                is_default=False
            )
        ]
        company = CompanyResponse(
            id=1,
            tenant_id=1,
            name="Company with Addresses",
            created_at=now,
            updated_at=now,
            addresses=addresses
        )
        assert len(company.addresses) == 2
        assert company.addresses[0].is_default is True
        assert company.addresses[1].is_default is False
    
    def test_company_response_with_total_balance(self):
        """Test CompanyResponse with total_balance calculated field."""
        now = datetime.utcnow()
        company = CompanyResponse(
            id=1,
            tenant_id=1,
            name="Company with Balance",
            created_at=now,
            updated_at=now,
            total_balance=Decimal("15000.50")
        )
        assert company.total_balance == Decimal("15000.50")
    
    def test_company_response_with_zero_balance(self):
        """Test CompanyResponse with zero balance."""
        now = datetime.utcnow()
        company = CompanyResponse(
            id=1,
            tenant_id=1,
            name="Company with Zero Balance",
            created_at=now,
            updated_at=now,
            total_balance=Decimal("0.00")
        )
        assert company.total_balance == Decimal("0.00")
    
    def test_company_response_complete(self):
        """Test CompanyResponse with all optional fields populated."""
        now = datetime.utcnow()
        contacts = [ContactSummary(id=1, name="Contact 1")]
        addresses = [
            AddressSummary(
                id=1,
                street_address="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
                country="USA",
                is_default=True
            )
        ]
        company = CompanyResponse(
            id=1,
            tenant_id=1,
            name="Complete Company",
            address="Legacy Address",
            phone="555-1234",
            email="info@complete.com",
            created_at=now,
            updated_at=now,
            contacts=contacts,
            addresses=addresses,
            total_balance=Decimal("25000.00")
        )
        assert company.id == 1
        assert company.name == "Complete Company"
        assert len(company.contacts) == 1
        assert len(company.addresses) == 1
        assert company.total_balance == Decimal("25000.00")


class TestCustomerSummary:
    """Test CustomerSummary schema (legacy)."""
    
    def test_customer_summary_complete(self):
        """Test CustomerSummary with all fields."""
        customer = CustomerSummary(
            id=1,
            name="Legacy Customer",
            email="legacy@customer.com",
            phone="555-9999"
        )
        assert customer.id == 1
        assert customer.name == "Legacy Customer"
        assert customer.email == "legacy@customer.com"
        assert customer.phone == "555-9999"
    
    def test_customer_summary_without_phone(self):
        """Test CustomerSummary without phone."""
        customer = CustomerSummary(
            id=2,
            name="No Phone Customer",
            email="nophone@customer.com",
            phone=None
        )
        assert customer.phone is None


class TestCompanyDetailResponse:
    """Test CompanyDetailResponse schema."""
    
    def test_company_detail_response_inherits_from_company_response(self):
        """Test that CompanyDetailResponse includes all CompanyResponse fields."""
        now = datetime.utcnow()
        company = CompanyDetailResponse(
            id=1,
            tenant_id=1,
            name="Detail Company",
            created_at=now,
            updated_at=now,
            customers=[]
        )
        assert company.id == 1
        assert company.name == "Detail Company"
        assert company.customers == []
    
    def test_company_detail_response_with_customers(self):
        """Test CompanyDetailResponse with legacy customers list."""
        now = datetime.utcnow()
        customers = [
            CustomerSummary(id=1, name="Customer 1", email="c1@test.com", phone="555-0001"),
            CustomerSummary(id=2, name="Customer 2", email="c2@test.com", phone="555-0002")
        ]
        company = CompanyDetailResponse(
            id=1,
            tenant_id=1,
            name="Company with Customers",
            created_at=now,
            updated_at=now,
            customers=customers
        )
        assert len(company.customers) == 2
        assert company.customers[0].name == "Customer 1"
    
    def test_company_detail_response_with_contacts_and_customers(self):
        """Test CompanyDetailResponse with both contacts and legacy customers."""
        now = datetime.utcnow()
        contacts = [ContactSummary(id=1, name="Contact 1")]
        customers = [CustomerSummary(id=1, name="Customer 1", email="c1@test.com", phone="555-0001")]
        company = CompanyDetailResponse(
            id=1,
            tenant_id=1,
            name="Hybrid Company",
            created_at=now,
            updated_at=now,
            contacts=contacts,
            customers=customers,
            total_balance=Decimal("10000.00")
        )
        assert len(company.contacts) == 1
        assert len(company.customers) == 1
        assert company.total_balance == Decimal("10000.00")


class TestCompanySchemaIntegration:
    """Integration tests for Company schemas."""
    
    def test_company_response_serialization(self):
        """Test that CompanyResponse can be serialized to dict."""
        now = datetime.utcnow()
        company = CompanyResponse(
            id=1,
            tenant_id=1,
            name="Serialization Test",
            created_at=now,
            updated_at=now,
            total_balance=Decimal("5000.00")
        )
        data = company.model_dump()
        assert data['id'] == 1
        assert data['name'] == "Serialization Test"
        assert data['total_balance'] == Decimal("5000.00")
    
    def test_nested_schema_serialization(self):
        """Test serialization with nested schemas."""
        now = datetime.utcnow()
        contacts = [
            ContactSummary(id=1, name="Contact 1", email="c1@test.com")
        ]
        addresses = [
            AddressSummary(
                id=1,
                street_address="123 Main St",
                city="New York",
                state="NY",
                zip_code="10001",
                country="USA",
                is_default=True
            )
        ]
        company = CompanyResponse(
            id=1,
            tenant_id=1,
            name="Nested Test",
            created_at=now,
            updated_at=now,
            contacts=contacts,
            addresses=addresses,
            total_balance=Decimal("7500.00")
        )
        data = company.model_dump()
        assert len(data['contacts']) == 1
        assert len(data['addresses']) == 1
        assert data['contacts'][0]['name'] == "Contact 1"
        assert data['addresses'][0]['is_default'] is True
