"""Unit tests for Address model and repository"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.data.database import Base
from app.data.models.tenant import Tenant
from app.data.models.company import Company
from app.data.models.address import Address
from app.data.repositories.address_repository import AddressRepository


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
def address_repository(db_session):
    """Create an address repository instance"""
    return AddressRepository(db_session)


class TestAddressModel:
    """Test Address model functionality"""
    
    def test_create_address(self, db_session, test_tenant, test_company):
        """Test creating an address with required fields"""
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="123 Main St",
            city="New York",
            state="NY",
            zip_code="10001",
            country="USA"
        )
        db_session.add(address)
        db_session.commit()
        db_session.refresh(address)
        
        assert address.id is not None
        assert address.street_address == "123 Main St"
        assert address.city == "New York"
        assert address.state == "NY"
        assert address.zip_code == "10001"
        assert address.country == "USA"
        assert address.is_default is False
        assert address.company_id == test_company.id
        assert address.tenant_id == test_tenant.id
    
    def test_address_default_country(self, db_session, test_tenant, test_company):
        """Test that country defaults to USA"""
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="456 Oak Ave",
            city="Los Angeles",
            state="CA",
            zip_code="90001"
        )
        db_session.add(address)
        db_session.commit()
        db_session.refresh(address)
        
        assert address.country == "USA"
    
    def test_address_company_relationship(self, db_session, test_tenant, test_company):
        """Test that address has proper relationship with company"""
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="789 Pine Rd",
            city="Chicago",
            state="IL",
            zip_code="60601"
        )
        db_session.add(address)
        db_session.commit()
        db_session.refresh(address)
        
        # Test relationship
        assert address.company is not None
        assert address.company.id == test_company.id
        assert address.company.name == "Test Company"
    
    def test_address_requires_company(self, db_session, test_tenant):
        """Test that address requires a company_id"""
        address = Address(
            tenant_id=test_tenant.id,
            street_address="Invalid Address",
            city="Nowhere",
            state="XX",
            zip_code="00000"
        )
        db_session.add(address)
        
        # Should raise an error due to NOT NULL constraint
        with pytest.raises(Exception):
            db_session.commit()
    
    def test_address_requires_all_fields(self, db_session, test_tenant, test_company):
        """Test that address requires all mandatory fields"""
        # Missing street_address
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            city="Test City",
            state="TS",
            zip_code="12345"
        )
        db_session.add(address)
        
        with pytest.raises(Exception):
            db_session.commit()


class TestAddressRepository:
    """Test AddressRepository functionality"""
    
    def test_create_address_via_repository(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test creating an address through repository"""
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Repository St",
            city="Boston",
            state="MA",
            zip_code="02101"
        )
        
        created = address_repository.create(address)
        
        assert created.id is not None
        assert created.street_address == "100 Repository St"
        assert created.city == "Boston"
    
    def test_get_by_id(self, address_repository, test_tenant, test_company):
        """Test retrieving address by ID"""
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="200 Get By ID Ave",
            city="Seattle",
            state="WA",
            zip_code="98101"
        )
        created = address_repository.create(address)
        
        retrieved = address_repository.get_by_id(created.id, test_tenant.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.street_address == "200 Get By ID Ave"
    
    def test_get_by_company(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test retrieving all addresses for a company"""
        # Create multiple addresses
        addresses_data = [
            ("123 First St", "City1", "ST", "11111"),
            ("456 Second Ave", "City2", "ST", "22222"),
            ("789 Third Blvd", "City3", "ST", "33333")
        ]
        
        for street, city, state, zip_code in addresses_data:
            address = Address(
                tenant_id=test_tenant.id,
                company_id=test_company.id,
                street_address=street,
                city=city,
                state=state,
                zip_code=zip_code
            )
            address_repository.create(address)
        
        addresses = address_repository.get_by_company(
            test_company.id,
            test_tenant.id
        )
        
        assert len(addresses) == 3
        assert all(a.company_id == test_company.id for a in addresses)
    
    def test_get_default_address(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test retrieving the default address for a company"""
        # Create non-default address
        address1 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Non-Default St",
            city="City1",
            state="ST",
            zip_code="11111",
            is_default=False
        )
        address_repository.create(address1)
        
        # Create default address
        address2 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="200 Default Ave",
            city="City2",
            state="ST",
            zip_code="22222",
            is_default=True
        )
        created_default = address_repository.create(address2)
        
        # Retrieve default address
        default = address_repository.get_default_address(
            test_company.id,
            test_tenant.id
        )
        
        assert default is not None
        assert default.id == created_default.id
        assert default.is_default is True
        assert default.street_address == "200 Default Ave"
    
    def test_set_default_address(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test setting an address as default"""
        # Create two addresses
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
        
        address2 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="200 Second Ave",
            city="City2",
            state="ST",
            zip_code="22222",
            is_default=False
        )
        created2 = address_repository.create(address2)
        
        # Set second address as default
        updated = address_repository.set_default_address(
            created2.id,
            test_company.id,
            test_tenant.id
        )
        
        assert updated is not None
        assert updated.is_default is True
        
        # Verify first address is no longer default
        first = address_repository.get_by_id(created1.id, test_tenant.id)
        assert first.is_default is False
    
    def test_unset_default_addresses(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test removing default status from all addresses"""
        # Create addresses with one default
        address1 = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Default St",
            city="City1",
            state="ST",
            zip_code="11111",
            is_default=True
        )
        address_repository.create(address1)
        
        # Unset all defaults
        count = address_repository.unset_default_addresses(
            test_company.id,
            test_tenant.id
        )
        
        assert count == 1
        
        # Verify no default address exists
        default = address_repository.get_default_address(
            test_company.id,
            test_tenant.id
        )
        assert default is None
    
    def test_has_default_address(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test checking if company has a default address"""
        # Initially no default
        assert address_repository.has_default_address(
            test_company.id,
            test_tenant.id
        ) is False
        
        # Create default address
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Default St",
            city="City",
            state="ST",
            zip_code="11111",
            is_default=True
        )
        address_repository.create(address)
        
        # Now has default
        assert address_repository.has_default_address(
            test_company.id,
            test_tenant.id
        ) is True
    
    def test_count_by_company(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test counting addresses for a company"""
        # Create addresses
        for i in range(4):
            address = Address(
                tenant_id=test_tenant.id,
                company_id=test_company.id,
                street_address=f"{i}00 Street {i}",
                city=f"City{i}",
                state="ST",
                zip_code=f"{i}{i}{i}{i}{i}"
            )
            address_repository.create(address)
        
        count = address_repository.count_by_company(
            test_company.id,
            test_tenant.id
        )
        
        assert count == 4
    
    def test_multi_tenant_isolation(
        self,
        db_session,
        address_repository
    ):
        """Test that addresses are isolated by tenant"""
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
        
        # Create addresses for each tenant
        address1 = Address(
            tenant_id=tenant1.id,
            company_id=company1.id,
            street_address="100 Tenant 1 St",
            city="City1",
            state="ST",
            zip_code="11111"
        )
        address2 = Address(
            tenant_id=tenant2.id,
            company_id=company2.id,
            street_address="200 Tenant 2 Ave",
            city="City2",
            state="ST",
            zip_code="22222"
        )
        address_repository.create(address1)
        address_repository.create(address2)
        
        # Verify tenant isolation
        tenant1_addresses = address_repository.get_all(tenant_id=tenant1.id)
        tenant2_addresses = address_repository.get_all(tenant_id=tenant2.id)
        
        assert len(tenant1_addresses) == 1
        assert len(tenant2_addresses) == 1
        assert tenant1_addresses[0].tenant_id == tenant1.id
        assert tenant2_addresses[0].tenant_id == tenant2.id
    
    def test_delete_address(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test deleting an address"""
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Delete Me St",
            city="DeleteCity",
            state="DL",
            zip_code="99999"
        )
        created = address_repository.create(address)
        
        # Delete the address
        address_repository.delete(created)
        
        # Verify it's deleted
        retrieved = address_repository.get_by_id(created.id, test_tenant.id)
        assert retrieved is None
    
    def test_update_address(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test updating an address"""
        address = Address(
            tenant_id=test_tenant.id,
            company_id=test_company.id,
            street_address="100 Old St",
            city="OldCity",
            state="OL",
            zip_code="11111"
        )
        created = address_repository.create(address)
        
        # Update the address
        created.street_address = "200 New St"
        created.city = "NewCity"
        updated = address_repository.update(created)
        
        assert updated.street_address == "200 New St"
        assert updated.city == "NewCity"
        
        # Verify persistence
        retrieved = address_repository.get_by_id(created.id, test_tenant.id)
        assert retrieved.street_address == "200 New St"
        assert retrieved.city == "NewCity"
    
    def test_pagination(
        self,
        address_repository,
        test_tenant,
        test_company
    ):
        """Test pagination of address results"""
        # Create 10 addresses
        for i in range(10):
            address = Address(
                tenant_id=test_tenant.id,
                company_id=test_company.id,
                street_address=f"{i}00 Street {i}",
                city=f"City{i}",
                state="ST",
                zip_code=f"{i:05d}"
            )
            address_repository.create(address)
        
        # Get first page (5 items)
        page1 = address_repository.get_by_company(
            test_company.id,
            test_tenant.id,
            skip=0,
            limit=5
        )
        
        # Get second page (5 items)
        page2 = address_repository.get_by_company(
            test_company.id,
            test_tenant.id,
            skip=5,
            limit=5
        )
        
        assert len(page1) == 5
        assert len(page2) == 5
        
        # Verify no overlap
        page1_ids = {a.id for a in page1}
        page2_ids = {a.id for a in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0
