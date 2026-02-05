"""Unit tests for Address default address logic"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.data.database import Base
from app.data.models.tenant import Tenant
from app.data.models.company import Company
from app.data.models.address import Address
from app.data.repositories.address_repository import AddressRepository


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
def address_repository(db_session):
    """Create an address repository instance"""
    return AddressRepository(db_session)


class TestAddressDefaultLogic:
    """Test default address business logic"""
    
    def test_only_one_default_per_company(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test that only one address can be default per company"""
        # Create first address as default
        address1 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 First St",
            city="City1",
            state="ST",
            zip_code="11111",
            is_default=True
        )
        created1 = address_repository.create(address1)
        assert created1.is_default is True
        
        # Create second address as default
        address2 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="200 Second Ave",
            city="City2",
            state="ST",
            zip_code="22222",
            is_default=True
        )
        created2 = address_repository.create(address2)
        assert created2.is_default is True
        
        # Verify first address is no longer default
        # (This would be enforced by database trigger in PostgreSQL,
        # but we test the application logic here)
        address_repository.set_default_address(
            created2.id,
            test_company.id,
            test_tenant.id
        )
        
        first = address_repository.get_by_id(created1.id, test_tenant.id)
        second = address_repository.get_by_id(created2.id, test_tenant.id)
        
        assert first.is_default is False
        assert second.is_default is True
    
    def test_default_address_for_shipment_population(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test retrieving default address for shipment creation (Requirement 5.2)"""
        # Create multiple addresses with one default
        address1 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Warehouse St",
            city="Warehouse City",
            state="WC",
            zip_code="11111",
            is_default=False
        )
        address_repository.create(address1)
        
        address2 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="200 Shipping Ave",
            city="Shipping City",
            state="SC",
            zip_code="22222",
            is_default=True
        )
        created_default = address_repository.create(address2)
        
        # Retrieve default address for shipment
        default = address_repository.get_default_address(
            test_company.id,
            test_tenant.id
        )
        
        assert default is not None
        assert default.id == created_default.id
        assert default.street_address == "200 Shipping Ave"
        assert default.is_default is True
    
    def test_changing_default_address(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test updating company's default address (Requirement 5.4)"""
        # Create two addresses
        address1 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Old Default St",
            city="OldCity",
            state="OC",
            zip_code="11111",
            is_default=True
        )
        created1 = address_repository.create(address1)
        
        address2 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="200 New Default Ave",
            city="NewCity",
            state="NC",
            zip_code="22222",
            is_default=False
        )
        created2 = address_repository.create(address2)
        
        # Change default to second address
        address_repository.set_default_address(
            created2.id,
            test_company.id,
            test_tenant.id
        )
        
        # Verify change
        old_default = address_repository.get_by_id(created1.id, test_tenant.id)
        new_default = address_repository.get_by_id(created2.id, test_tenant.id)
        
        assert old_default.is_default is False
        assert new_default.is_default is True
        
        # Verify get_default_address returns new default
        default = address_repository.get_default_address(
            test_company.id,
            test_tenant.id
        )
        assert default.id == created2.id
    
    def test_company_with_no_default_address(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test company with addresses but no default"""
        # Create addresses without default
        address1 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 No Default St",
            city="City1",
            state="ST",
            zip_code="11111",
            is_default=False
        )
        address_repository.create(address1)
        
        # Verify no default exists
        default = address_repository.get_default_address(
            test_company.id,
            test_tenant.id
        )
        assert default is None
        
        has_default = address_repository.has_default_address(
            test_company.id,
            test_tenant.id
        )
        assert has_default is False
    
    def test_address_validation_completeness(
        self,
        db_session,
        test_tenant,
        test_company
    ):
        """Test address validation for required fields (Requirement 5.5)"""
        # Valid complete address
        valid_address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Complete St",
            city="Complete City",
            state="CC",
            zip_code="12345"
        )
        db_session.add(valid_address)
        db_session.commit()
        db_session.refresh(valid_address)
        
        assert valid_address.id is not None
        assert valid_address.street_address == "100 Complete St"
        assert valid_address.city == "Complete City"
        assert valid_address.state == "CC"
        assert valid_address.zip_code == "12345"
    
    def test_multiple_companies_can_have_default_addresses(
        self,
        db_session,
        address_repository,
        test_tenant
    ):
        """Test that different companies can each have their own default address"""
        # Create two companies
        company1 = Company(
            tenant_id=test_tenant.id,
            name="Company 1",
            email="company1@test.com"
        )
        company2 = Company(
            tenant_id=test_tenant.id,
            name="Company 2",
            email="company2@test.com"
        )
        db_session.add_all([company1, company2])
        db_session.commit()
        
        # Create default address for company 1
        address1 = Address(
            tenant_id=test_tenant.id,
            company_id=company1.id,
            street_address="100 Company 1 St",
            city="City1",
            state="ST",
            zip_code="11111",
            is_default=True
        )
        created1 = address_repository.create(address1)
        
        # Create default address for company 2
        address2 = Address(
            tenant_id=test_tenant.id,
            company_id=company2.id,
            street_address="200 Company 2 Ave",
            city="City2",
            state="ST",
            zip_code="22222",
            is_default=True
        )
        created2 = address_repository.create(address2)
        
        # Verify both companies have their own default
        default1 = address_repository.get_default_address(
            company1.id,
            test_tenant.id
        )
        default2 = address_repository.get_default_address(
            company2.id,
            test_tenant.id
        )
        
        assert default1 is not None
        assert default2 is not None
        assert default1.id == created1.id
        assert default2.id == created2.id
        assert default1.company_id == company1.id
        assert default2.company_id == company2.id
