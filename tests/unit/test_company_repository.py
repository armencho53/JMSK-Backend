"""Unit tests for CompanyRepository"""
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.models.order import Order, OrderStatus
from app.data.repositories.company_repository import CompanyRepository


class TestCompanyRepository:
    """Test suite for CompanyRepository"""
    
    def test_get_by_name_returns_company_when_exists(self, db: Session, sample_tenant):
        """Test getting company by name returns the correct company"""
        # Arrange
        company = Company(
            tenant_id=sample_tenant.id,
            name="Test Company",
            email="test@company.com"
        )
        db.add(company)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_by_name("Test Company", sample_tenant.id)
        
        # Assert
        assert result is not None
        assert result.name == "Test Company"
        assert result.email == "test@company.com"
    
    def test_get_by_name_returns_none_when_not_exists(self, db: Session, sample_tenant):
        """Test getting company by name returns None when company doesn't exist"""
        # Arrange
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_by_name("Nonexistent Company", sample_tenant.id)
        
        # Assert
        assert result is None
    
    def test_get_by_name_respects_tenant_isolation(self, db: Session, sample_tenant, other_tenant):
        """Test that get_by_name respects multi-tenant isolation"""
        # Arrange
        company1 = Company(tenant_id=sample_tenant.id, name="Shared Name")
        company2 = Company(tenant_id=other_tenant.id, name="Shared Name")
        db.add_all([company1, company2])
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_by_name("Shared Name", sample_tenant.id)
        
        # Assert
        assert result is not None
        assert result.tenant_id == sample_tenant.id
        assert result.id == company1.id
    
    def test_get_with_contacts_loads_contacts_relationship(self, db: Session, sample_tenant):
        """Test that get_with_contacts eagerly loads contacts"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        contact1 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 1")
        contact2 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 2")
        db.add_all([contact1, contact2])
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_with_contacts(company.id, sample_tenant.id)
        
        # Assert
        assert result is not None
        assert len(result.contacts) == 2
        assert {c.name for c in result.contacts} == {"Contact 1", "Contact 2"}
    
    def test_get_contacts_returns_all_company_contacts(self, db: Session, sample_tenant):
        """Test getting all contacts for a company"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        contact1 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 1")
        contact2 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 2")
        contact3 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 3")
        db.add_all([contact1, contact2, contact3])
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_contacts(company.id, sample_tenant.id)
        
        # Assert
        assert len(result) == 3
        assert {c.name for c in result} == {"Contact 1", "Contact 2", "Contact 3"}
    
    def test_get_contacts_respects_pagination(self, db: Session, sample_tenant):
        """Test that get_contacts respects skip and limit parameters"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        for i in range(5):
            contact = Contact(tenant_id=sample_tenant.id, company_id=company.id, name=f"Contact {i}")
            db.add(contact)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_contacts(company.id, sample_tenant.id, skip=1, limit=2)
        
        # Assert
        assert len(result) == 2
    
    def test_get_balance_returns_zero_when_no_orders(self, db: Session, sample_tenant):
        """Test that get_balance returns 0.00 when company has no orders"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_balance(company.id, sample_tenant.id)
        
        # Assert
        assert result == Decimal('0.00')
    
    def test_get_balance_aggregates_all_contact_orders(self, db: Session, sample_tenant):
        """Test that get_balance aggregates orders from all contacts"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        contact1 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 1")
        contact2 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 2")
        db.add_all([contact1, contact2])
        db.commit()
        
        order1 = Order(
            tenant_id=sample_tenant.id,
            company_id=company.id,
            contact_id=contact1.id,
            order_number="ORD-001",
            customer_name="Contact 1",
            price=100.50,
            status=OrderStatus.PENDING
        )
        order2 = Order(
            tenant_id=sample_tenant.id,
            company_id=company.id,
            contact_id=contact1.id,
            order_number="ORD-002",
            customer_name="Contact 1",
            price=200.75,
            status=OrderStatus.PENDING
        )
        order3 = Order(
            tenant_id=sample_tenant.id,
            company_id=company.id,
            contact_id=contact2.id,
            order_number="ORD-003",
            customer_name="Contact 2",
            price=150.25,
            status=OrderStatus.PENDING
        )
        db.add_all([order1, order2, order3])
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_balance(company.id, sample_tenant.id)
        
        # Assert
        expected = Decimal('100.50') + Decimal('200.75') + Decimal('150.25')
        assert result == expected
    
    def test_get_balance_respects_tenant_isolation(self, db: Session, sample_tenant, other_tenant):
        """Test that get_balance respects multi-tenant isolation"""
        # Arrange
        company1 = Company(tenant_id=sample_tenant.id, name="Company 1")
        company2 = Company(tenant_id=other_tenant.id, name="Company 2")
        db.add_all([company1, company2])
        db.commit()
        
        contact1 = Contact(tenant_id=sample_tenant.id, company_id=company1.id, name="Contact 1")
        contact2 = Contact(tenant_id=other_tenant.id, company_id=company2.id, name="Contact 2")
        db.add_all([contact1, contact2])
        db.commit()
        
        order1 = Order(
            tenant_id=sample_tenant.id,
            company_id=company1.id,
            contact_id=contact1.id,
            order_number="ORD-001",
            customer_name="Contact 1",
            price=100.00,
            status=OrderStatus.PENDING
        )
        order2 = Order(
            tenant_id=other_tenant.id,
            company_id=company2.id,
            contact_id=contact2.id,
            order_number="ORD-002",
            customer_name="Contact 2",
            price=200.00,
            status=OrderStatus.PENDING
        )
        db.add_all([order1, order2])
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_balance(company1.id, sample_tenant.id)
        
        # Assert
        assert result == Decimal('100.00')
    
    def test_get_order_count_returns_zero_when_no_orders(self, db: Session, sample_tenant):
        """Test that get_order_count returns 0 when company has no orders"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_order_count(company.id, sample_tenant.id)
        
        # Assert
        assert result == 0
    
    def test_get_order_count_counts_all_contact_orders(self, db: Session, sample_tenant):
        """Test that get_order_count counts orders from all contacts"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        contact1 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 1")
        contact2 = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 2")
        db.add_all([contact1, contact2])
        db.commit()
        
        for i in range(3):
            order = Order(
                tenant_id=sample_tenant.id,
                company_id=company.id,
                contact_id=contact1.id,
                order_number=f"ORD-00{i}",
                customer_name="Contact 1",
                price=100.00,
                status=OrderStatus.PENDING
            )
            db.add(order)
        
        for i in range(2):
            order = Order(
                tenant_id=sample_tenant.id,
                company_id=company.id,
                contact_id=contact2.id,
                order_number=f"ORD-10{i}",
                customer_name="Contact 2",
                price=100.00,
                status=OrderStatus.PENDING
            )
            db.add(order)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_order_count(company.id, sample_tenant.id)
        
        # Assert
        assert result == 5
    
    def test_get_contact_count_returns_correct_count(self, db: Session, sample_tenant):
        """Test that get_contact_count returns correct number of contacts"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        for i in range(4):
            contact = Contact(tenant_id=sample_tenant.id, company_id=company.id, name=f"Contact {i}")
            db.add(contact)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.get_contact_count(company.id, sample_tenant.id)
        
        # Assert
        assert result == 4
    
    def test_has_contacts_returns_true_when_contacts_exist(self, db: Session, sample_tenant):
        """Test that has_contacts returns True when company has contacts"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        contact = Contact(tenant_id=sample_tenant.id, company_id=company.id, name="Contact 1")
        db.add(contact)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.has_contacts(company.id, sample_tenant.id)
        
        # Assert
        assert result is True
    
    def test_has_contacts_returns_false_when_no_contacts(self, db: Session, sample_tenant):
        """Test that has_contacts returns False when company has no contacts"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.has_contacts(company.id, sample_tenant.id)
        
        # Assert
        assert result is False
    
    def test_search_finds_companies_by_partial_name(self, db: Session, sample_tenant):
        """Test that search finds companies by partial name match"""
        # Arrange
        company1 = Company(tenant_id=sample_tenant.id, name="Acme Corporation")
        company2 = Company(tenant_id=sample_tenant.id, name="Acme Industries")
        company3 = Company(tenant_id=sample_tenant.id, name="Other Company")
        db.add_all([company1, company2, company3])
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.search(sample_tenant.id, "Acme")
        
        # Assert
        assert len(result) == 2
        assert {c.name for c in result} == {"Acme Corporation", "Acme Industries"}
    
    def test_search_is_case_insensitive(self, db: Session, sample_tenant):
        """Test that search is case insensitive"""
        # Arrange
        company = Company(tenant_id=sample_tenant.id, name="Test Company")
        db.add(company)
        db.commit()
        
        repo = CompanyRepository(db)
        
        # Act
        result = repo.search(sample_tenant.id, "test")
        
        # Assert
        assert len(result) == 1
        assert result[0].name == "Test Company"
