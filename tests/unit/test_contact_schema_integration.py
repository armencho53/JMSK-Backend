"""
Integration tests for Contact schemas with ORM models.

Tests that Contact schemas correctly serialize/deserialize Contact ORM models
and handle relationships properly.

Requirements: 1.1, 1.4, 6.5
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.data.database import Base
from app.data.models.contact import Contact
from app.data.models.company import Company
from app.data.models.tenant import Tenant
from app.schemas.contact import ContactResponse, CompanySummary


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


def test_contact_response_from_orm_model(db_session):
    """Test that ContactResponse can be created from Contact ORM model."""
    # Create tenant
    tenant = Tenant(id=1, name="Test Tenant", subdomain="test")
    db_session.add(tenant)
    
    # Create company
    company = Company(
        id=1,
        tenant_id=1,
        name="Acme Corp",
        email="info@acme.com",
        phone="555-0000"
    )
    db_session.add(company)
    
    # Create contact
    contact = Contact(
        id=1,
        tenant_id=1,
        company_id=1,
        name="John Doe",
        email="john@example.com",
        phone="555-1234"
    )
    db_session.add(contact)
    db_session.commit()
    
    # Refresh to load relationships
    db_session.refresh(contact)
    
    # Create ContactResponse from ORM model
    response = ContactResponse.model_validate(contact)
    
    assert response.id == 1
    assert response.tenant_id == 1
    assert response.company_id == 1
    assert response.name == "John Doe"
    assert response.email == "john@example.com"
    assert response.phone == "555-1234"
    assert response.created_at is not None
    assert response.updated_at is not None


def test_contact_response_with_company_relationship(db_session):
    """Test that ContactResponse includes company relationship when loaded."""
    # Create tenant
    tenant = Tenant(id=1, name="Test Tenant", subdomain="test")
    db_session.add(tenant)
    
    # Create company
    company = Company(
        id=1,
        tenant_id=1,
        name="Acme Corp",
        email="info@acme.com",
        phone="555-0000"
    )
    db_session.add(company)
    
    # Create contact
    contact = Contact(
        id=1,
        tenant_id=1,
        company_id=1,
        name="John Doe",
        email="john@example.com",
        phone="555-1234"
    )
    db_session.add(contact)
    db_session.commit()
    
    # Refresh and load company relationship
    db_session.refresh(contact)
    
    # Create ContactResponse from ORM model
    response = ContactResponse.model_validate(contact)
    
    # Company relationship should be loaded
    assert response.company is not None
    assert response.company.id == 1
    assert response.company.name == "Acme Corp"
    assert response.company.email == "info@acme.com"
    assert response.company.phone == "555-0000"


def test_contact_response_without_optional_fields(db_session):
    """Test ContactResponse with minimal fields (no email/phone)."""
    # Create tenant
    tenant = Tenant(id=1, name="Test Tenant", subdomain="test")
    db_session.add(tenant)
    
    # Create company
    company = Company(
        id=1,
        tenant_id=1,
        name="Acme Corp"
    )
    db_session.add(company)
    
    # Create contact with minimal fields
    contact = Contact(
        id=1,
        tenant_id=1,
        company_id=1,
        name="Jane Smith"
    )
    db_session.add(contact)
    db_session.commit()
    
    # Refresh to load relationships
    db_session.refresh(contact)
    
    # Create ContactResponse from ORM model
    response = ContactResponse.model_validate(contact)
    
    assert response.id == 1
    assert response.name == "Jane Smith"
    assert response.email is None
    assert response.phone is None
    assert response.company_id == 1


def test_company_summary_from_orm_model(db_session):
    """Test that CompanySummary can be created from Company ORM model."""
    # Create tenant
    tenant = Tenant(id=1, name="Test Tenant", subdomain="test")
    db_session.add(tenant)
    
    # Create company
    company = Company(
        id=1,
        tenant_id=1,
        name="Acme Corp",
        email="info@acme.com",
        phone="555-0000"
    )
    db_session.add(company)
    db_session.commit()
    
    # Create CompanySummary from ORM model
    summary = CompanySummary.model_validate(company)
    
    assert summary.id == 1
    assert summary.name == "Acme Corp"
    assert summary.email == "info@acme.com"
    assert summary.phone == "555-0000"
