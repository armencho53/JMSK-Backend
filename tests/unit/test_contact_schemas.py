"""
Unit tests for Contact Pydantic schemas.

Tests validation rules, field requirements, and schema behavior for
Contact-related schemas including ContactCreate, ContactUpdate, and ContactResponse.

Requirements: 1.1, 1.4, 6.5
"""
import pytest
from pydantic import ValidationError
from datetime import datetime
from app.schemas.contact import (
    ContactBase,
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    CompanySummary,
    ContactListResponse
)


class TestContactBase:
    """Test ContactBase schema validation."""
    
    def test_valid_contact_base(self):
        """Test creating ContactBase with valid data."""
        contact = ContactBase(
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            company_id=1
        )
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"
        assert contact.phone == "555-1234"
        assert contact.company_id == 1
    
    def test_contact_base_minimal_fields(self):
        """Test ContactBase with only required fields."""
        contact = ContactBase(
            name="Jane Smith",
            company_id=2
        )
        assert contact.name == "Jane Smith"
        assert contact.email is None
        assert contact.phone is None
        assert contact.company_id == 2
    
    def test_contact_base_missing_name(self):
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ContactBase(
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('name',) for e in errors)
    
    def test_contact_base_missing_company_id(self):
        """Test that company_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ContactBase(
                name="John Doe"
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('company_id',) for e in errors)
    
    def test_contact_base_empty_name(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ContactBase(
                name="",
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any('name' in str(e) for e in errors)
    
    def test_contact_base_whitespace_name(self):
        """Test that whitespace-only name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ContactBase(
                name="   ",
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any('whitespace' in str(e).lower() for e in errors)
    
    def test_contact_base_name_trimmed(self):
        """Test that name is trimmed of leading/trailing whitespace."""
        contact = ContactBase(
            name="  John Doe  ",
            company_id=1
        )
        assert contact.name == "John Doe"
    
    def test_contact_base_invalid_email(self):
        """Test that invalid email format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ContactBase(
                name="John Doe",
                email="invalid-email",
                company_id=1
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('email',) for e in errors)
    
    def test_contact_base_zero_company_id(self):
        """Test that company_id must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ContactBase(
                name="John Doe",
                company_id=0
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('company_id',) for e in errors)
    
    def test_contact_base_negative_company_id(self):
        """Test that negative company_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ContactBase(
                name="John Doe",
                company_id=-1
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('company_id',) for e in errors)
    
    def test_contact_base_phone_trimmed(self):
        """Test that phone is trimmed of whitespace."""
        contact = ContactBase(
            name="John Doe",
            phone="  555-1234  ",
            company_id=1
        )
        assert contact.phone == "555-1234"
    
    def test_contact_base_empty_phone_becomes_none(self):
        """Test that empty phone string becomes None."""
        contact = ContactBase(
            name="John Doe",
            phone="   ",
            company_id=1
        )
        assert contact.phone is None


class TestContactCreate:
    """Test ContactCreate schema."""
    
    def test_valid_contact_create(self):
        """Test creating ContactCreate with valid data."""
        contact = ContactCreate(
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            company_id=1
        )
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"
        assert contact.phone == "555-1234"
        assert contact.company_id == 1
    
    def test_contact_create_inherits_validation(self):
        """Test that ContactCreate inherits validation from ContactBase."""
        with pytest.raises(ValidationError):
            ContactCreate(
                name="",
                company_id=1
            )


class TestContactUpdate:
    """Test ContactUpdate schema."""
    
    def test_contact_update_all_fields(self):
        """Test ContactUpdate with all fields."""
        contact = ContactUpdate(
            name="Updated Name",
            email="updated@example.com",
            phone="555-9999",
            company_id=2
        )
        assert contact.name == "Updated Name"
        assert contact.email == "updated@example.com"
        assert contact.phone == "555-9999"
        assert contact.company_id == 2
    
    def test_contact_update_partial_fields(self):
        """Test ContactUpdate with only some fields."""
        contact = ContactUpdate(
            name="Updated Name"
        )
        assert contact.name == "Updated Name"
        assert contact.email is None
        assert contact.phone is None
        assert contact.company_id is None
    
    def test_contact_update_no_fields(self):
        """Test ContactUpdate with no fields (all optional)."""
        contact = ContactUpdate()
        assert contact.name is None
        assert contact.email is None
        assert contact.phone is None
        assert contact.company_id is None
    
    def test_contact_update_empty_name_rejected(self):
        """Test that empty name is rejected in update."""
        with pytest.raises(ValidationError) as exc_info:
            ContactUpdate(
                name=""
            )
        errors = exc_info.value.errors()
        assert any('name' in str(e) for e in errors)
    
    def test_contact_update_whitespace_name_rejected(self):
        """Test that whitespace-only name is rejected in update."""
        with pytest.raises(ValidationError) as exc_info:
            ContactUpdate(
                name="   "
            )
        errors = exc_info.value.errors()
        assert any('whitespace' in str(e).lower() for e in errors)
    
    def test_contact_update_name_trimmed(self):
        """Test that name is trimmed in update."""
        contact = ContactUpdate(
            name="  Updated Name  "
        )
        assert contact.name == "Updated Name"
    
    def test_contact_update_invalid_email(self):
        """Test that invalid email is rejected in update."""
        with pytest.raises(ValidationError) as exc_info:
            ContactUpdate(
                email="invalid-email"
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('email',) for e in errors)
    
    def test_contact_update_zero_company_id_rejected(self):
        """Test that zero company_id is rejected in update."""
        with pytest.raises(ValidationError) as exc_info:
            ContactUpdate(
                company_id=0
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('company_id',) for e in errors)


class TestCompanySummary:
    """Test CompanySummary schema."""
    
    def test_company_summary_from_dict(self):
        """Test creating CompanySummary from dictionary."""
        data = {
            "id": 1,
            "name": "Acme Corp",
            "email": "info@acme.com",
            "phone": "555-0000"
        }
        company = CompanySummary(**data)
        assert company.id == 1
        assert company.name == "Acme Corp"
        assert company.email == "info@acme.com"
        assert company.phone == "555-0000"
    
    def test_company_summary_minimal(self):
        """Test CompanySummary with minimal fields."""
        company = CompanySummary(
            id=1,
            name="Acme Corp"
        )
        assert company.id == 1
        assert company.name == "Acme Corp"
        assert company.email is None
        assert company.phone is None


class TestContactResponse:
    """Test ContactResponse schema."""
    
    def test_contact_response_full(self):
        """Test ContactResponse with all fields."""
        now = datetime.utcnow()
        contact = ContactResponse(
            id=1,
            tenant_id=1,
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            company_id=1,
            created_at=now,
            updated_at=now,
            company=CompanySummary(
                id=1,
                name="Acme Corp",
                email="info@acme.com",
                phone="555-0000"
            )
        )
        assert contact.id == 1
        assert contact.tenant_id == 1
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"
        assert contact.phone == "555-1234"
        assert contact.company_id == 1
        assert contact.created_at == now
        assert contact.updated_at == now
        assert contact.company is not None
        assert contact.company.name == "Acme Corp"
    
    def test_contact_response_without_company(self):
        """Test ContactResponse without company relationship."""
        now = datetime.utcnow()
        contact = ContactResponse(
            id=1,
            tenant_id=1,
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            company_id=1,
            created_at=now,
            updated_at=now
        )
        assert contact.company is None


class TestContactListResponse:
    """Test ContactListResponse schema."""
    
    def test_contact_list_response(self):
        """Test ContactListResponse with multiple contacts."""
        now = datetime.utcnow()
        contacts = [
            ContactResponse(
                id=1,
                tenant_id=1,
                name="John Doe",
                email="john@example.com",
                phone="555-1234",
                company_id=1,
                created_at=now,
                updated_at=now
            ),
            ContactResponse(
                id=2,
                tenant_id=1,
                name="Jane Smith",
                email="jane@example.com",
                phone="555-5678",
                company_id=1,
                created_at=now,
                updated_at=now
            )
        ]
        
        response = ContactListResponse(
            contacts=contacts,
            total=2,
            page=1,
            page_size=50
        )
        
        assert len(response.contacts) == 2
        assert response.total == 2
        assert response.page == 1
        assert response.page_size == 50
    
    def test_contact_list_response_empty(self):
        """Test ContactListResponse with no contacts."""
        response = ContactListResponse(
            contacts=[],
            total=0
        )
        
        assert len(response.contacts) == 0
        assert response.total == 0
        assert response.page == 1  # Default value
        assert response.page_size == 50  # Default value
    
    def test_contact_list_response_custom_pagination(self):
        """Test ContactListResponse with custom pagination."""
        response = ContactListResponse(
            contacts=[],
            total=100,
            page=3,
            page_size=25
        )
        
        assert response.total == 100
        assert response.page == 3
        assert response.page_size == 25
