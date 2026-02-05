"""Unit tests for Contact model and repository"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.data.database import Base
from app.data.models.tenant import Tenant
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.repositories.contact_repository import ContactRepository


# Create in-memory SQLite database for testing
@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def test_tenant(db_session):
    """Create a test tenant"""
    tenant = Tenant(
        name="Test Tenant",
        subdomain="test",
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_company(db_session, test_tenant):
    """Create a test company"""
    company = Company(
        tenant_id=test_tenant.id,
        name="Test Company",
        email="company@test.com",
        phone="1234567890"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def contact_repository(db_session):
    """Create a contact repository instance"""
    return ContactRepository(db_session)


class TestContactModel:
    """Test Contact model functionality"""
    
    def test_create_contact(self, db_session, test_tenant, test_company):
        """Test creating a contact with required fields"""
        contact = Contact(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            name="John Doe",
            email="john@test.com",
            phone="1234567890"
        )
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        
        assert contact.id is not None
        assert contact.name == "John Doe"
        assert contact.email == "john@test.com"
        assert contact.company_id == test_company.id
        assert contact.tenant_id == test_tenant.id
    
    def test_contact_company_relationship(self, db_session, test_tenant, test_company):
        """Test that contact has proper relationship with company"""
        contact = Contact(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            name="Jane Smith",
            email="jane@test.com"
        )
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        
        # Test relationship
        assert contact.company is not None
        assert contact.company.id == test_company.id
        assert contact.company.name == "Test Company"
    
    def test_contact_requires_company(self, db_session, test_tenant):
        """Test that contact requires a company_id"""
        contact = Contact(
            tenant_id=test_tenant.id,
            name="Invalid Contact",
            email="invalid@test.com"
        )
        db_session.add(contact)
        
        # Should raise an error due to NOT NULL constraint
        with pytest.raises(Exception):
            db_session.commit()


class TestContactRepository:
    """Test ContactRepository functionality"""
    
    def test_create_contact_via_repository(
        self,
        contact_repository,
        test_tenant,
        test_company
    ):
        """Test creating a contact through repository"""
        contact = Contact(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            name="Repository Test",
            email="repo@test.com"
        )
        
        created = contact_repository.create(contact)
        
        assert created.id is not None
        assert created.name == "Repository Test"
    
    def test_get_by_id(self, contact_repository, test_tenant, test_company):
        """Test retrieving contact by ID"""
        contact = Contact(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            name="Get By ID Test",
            email="getbyid@test.com"
        )
        created = contact_repository.create(contact)
        
        retrieved = contact_repository.get_by_id(created.id, test_tenant.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Get By ID Test"
    
    def test_get_by_email(self, contact_repository, test_tenant, test_company):
        """Test retrieving contact by email within a company"""
        contact = Contact(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            name="Email Test",
            email="email@test.com"
        )
        contact_repository.create(contact)
        
        retrieved = contact_repository.get_by_email(
            "email@test.com",
            test_company.id,
            test_tenant.id
        )
        
        assert retrieved is not None
        assert retrieved.email == "email@test.com"
        assert retrieved.company_id == test_company.id
    
    def test_get_by_company(
        self,
        contact_repository,
        test_tenant,
        test_company
    ):
        """Test retrieving all contacts for a company"""
        # Create multiple contacts
        for i in range(3):
            contact = Contact(
                tenant_id=test_tenant.id,
                company_id=test_company.id,
                name=f"Contact {i}",
                email=f"contact{i}@test.com"
            )
            contact_repository.create(contact)
        
        contacts = contact_repository.get_by_company(
            test_company.id,
            test_tenant.id
        )
        
        assert len(contacts) == 3
        assert all(c.company_id == test_company.id for c in contacts)
    
    def test_search_contacts(
        self,
        contact_repository,
        test_tenant,
        test_company
    ):
        """Test searching contacts by name or email"""
        contact1 = Contact(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            name="Alice Johnson",
            email="alice@test.com"
        )
        contact2 = Contact(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            name="Bob Smith",
            email="bob@test.com"
        )
        contact_repository.create(contact1)
        contact_repository.create(contact2)
        
        # Search by name
        results = contact_repository.search(test_tenant.id, "Alice")
        assert len(results) == 1
        assert results[0].name == "Alice Johnson"
        
        # Search by email
        results = contact_repository.search(test_tenant.id, "bob@")
        assert len(results) == 1
        assert results[0].email == "bob@test.com"
    
    def test_count_by_company(
        self,
        contact_repository,
        test_tenant,
        test_company
    ):
        """Test counting contacts for a company"""
        # Create contacts
        for i in range(5):
            contact = Contact(
                tenant_id=test_tenant.id,
                company_id=test_company.id,
                name=f"Contact {i}",
                email=f"contact{i}@test.com"
            )
            contact_repository.create(contact)
        
        count = contact_repository.count_by_company(
            test_company.id,
            test_tenant.id
        )
        
        assert count == 5
    
    def test_multi_tenant_isolation(
        self,
        db_session,
        contact_repository,
        test_company
    ):
        """Test that contacts are isolated by tenant"""
        # Create two tenants
        tenant1 = Tenant(name="Tenant 1", subdomain="tenant1")
        tenant2 = Tenant(name="Tenant 2", subdomain="tenant2")
        db_session.add_all([tenant1, tenant2])
        db_session.commit()
        
        # Create companies for each tenant
        company1 = Company(tenant_id=tenant1.id, name="Company 1")
        company2 = Company(tenant_id=tenant2.id, name="Company 2")
        db_session.add_all([company1, company2])
        db_session.commit()
        
        # Create contacts for each tenant
        contact1 = Contact(
            tenant_id=tenant1.id,
            company_id=company1.id,
            name="Tenant 1 Contact",
            email="t1@test.com"
        )
        contact2 = Contact(
            tenant_id=tenant2.id,
            company_id=company2.id,
            name="Tenant 2 Contact",
            email="t2@test.com"
        )
        contact_repository.create(contact1)
        contact_repository.create(contact2)
        
        # Verify tenant isolation
        tenant1_contacts = contact_repository.get_all(tenant_id=tenant1.id)
        tenant2_contacts = contact_repository.get_all(tenant_id=tenant2.id)
        
        assert len(tenant1_contacts) == 1
        assert len(tenant2_contacts) == 1
        assert tenant1_contacts[0].tenant_id == tenant1.id
        assert tenant2_contacts[0].tenant_id == tenant2.id
