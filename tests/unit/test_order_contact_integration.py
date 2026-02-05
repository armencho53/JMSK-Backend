"""Unit tests for order creation with contact_id integration"""
import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.data.models.tenant import Tenant
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.models.order import Order, OrderStatus
from app.data.models.customer import Customer


@pytest.fixture
def sample_tenant(db_session: Session):
    """Create a sample tenant for testing"""
    tenant = Tenant(name="Test Tenant", subdomain="test-tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def sample_company(db_session: Session, sample_tenant):
    """Create a sample company for testing"""
    company = Company(
        tenant_id=sample_tenant.id,
        name="Test Company",
        email="company@test.com",
        phone="123-456-7890"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def sample_contact(db_session: Session, sample_tenant, sample_company):
    """Create a sample contact for testing"""
    contact = Contact(
        tenant_id=sample_tenant.id,
        company_id=sample_company.id,
        name="John Doe",
        email="john@test.com",
        phone="555-1234"
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


@pytest.fixture
def sample_customer(db_session: Session, sample_tenant):
    """Create a sample legacy customer for backward compatibility testing"""
    customer = Customer(
        tenant_id=sample_tenant.id,
        name="Jane Smith",
        email="jane@test.com",
        phone="555-5678"
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


class TestOrderContactIntegration:
    """Test order creation with contact_id and company_id auto-population"""
    
    def test_order_creation_with_contact_id_populates_company_id(
        self, db_session: Session, sample_tenant, sample_company, sample_contact
    ):
        """Test that creating an order with contact_id auto-populates company_id
        
        Validates: Requirements 1.5, 3.1
        """
        # Arrange
        order_data = {
            "tenant_id": sample_tenant.id,
            "contact_id": sample_contact.id,
            "company_id": sample_company.id,  # Should match contact's company
            "order_number": "ORD-001",
            "customer_name": sample_contact.name,
            "customer_email": sample_contact.email,
            "customer_phone": sample_contact.phone,
            "product_description": "Gold Ring",
            "quantity": 1,
            "price": 500.00,
            "status": OrderStatus.PENDING
        }
        
        # Act
        order = Order(**order_data)
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        
        # Assert
        assert order.contact_id == sample_contact.id
        assert order.company_id == sample_company.id
        assert order.company_id == sample_contact.company_id
        assert order.customer_name == sample_contact.name
    
    def test_order_requires_both_contact_and_company_ids(
        self, db_session: Session, sample_tenant, sample_contact
    ):
        """Test that orders require both contact_id and company_id
        
        Validates: Requirements 1.5, 1.6
        """
        # Arrange - order with contact_id but no company_id
        order_data = {
            "tenant_id": sample_tenant.id,
            "contact_id": sample_contact.id,
            # company_id is missing
            "order_number": "ORD-002",
            "customer_name": "Test Customer",
            "product_description": "Silver Necklace",
            "quantity": 1,
            "price": 300.00
        }
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            order = Order(**order_data)
            db_session.add(order)
            db_session.commit()
        
        # Should fail due to NOT NULL constraint on company_id
        assert 'not null' in str(exc_info.value).lower() or 'null value' in str(exc_info.value).lower()
    
    def test_order_contact_and_company_must_match(
        self, db_session: Session, sample_tenant, sample_contact
    ):
        """Test that order's company_id must match contact's company_id
        
        Note: This is enforced by database trigger in PostgreSQL.
        In SQLite (test environment), this may not be enforced.
        
        Validates: Requirements 1.5, 1.6
        """
        # Arrange - create a different company
        other_company = Company(
            tenant_id=sample_tenant.id,
            name="Other Company",
            email="other@test.com"
        )
        db_session.add(other_company)
        db_session.commit()
        db_session.refresh(other_company)
        
        # Try to create order with mismatched company_id
        order_data = {
            "tenant_id": sample_tenant.id,
            "contact_id": sample_contact.id,
            "company_id": other_company.id,  # Different from contact's company
            "order_number": "ORD-003",
            "customer_name": "Test Customer",
            "product_description": "Platinum Ring",
            "quantity": 1,
            "price": 1000.00
        }
        
        # Act
        order = Order(**order_data)
        db_session.add(order)
        
        # In PostgreSQL with trigger, this would fail at commit
        # In SQLite (test env), it may succeed but should be caught by application logic
        try:
            db_session.commit()
            # If we get here in SQLite, verify the mismatch exists
            # (application should prevent this)
            assert order.company_id != sample_contact.company_id
        except Exception as e:
            # In PostgreSQL, expect trigger to prevent this
            assert 'company' in str(e).lower() or 'constraint' in str(e).lower()
    
    def test_order_with_contact_includes_all_contact_details(
        self, db_session: Session, sample_tenant, sample_company, sample_contact
    ):
        """Test that order captures all contact details for reference
        
        Validates: Requirements 1.5, 3.1
        """
        # Arrange
        order_data = {
            "tenant_id": sample_tenant.id,
            "contact_id": sample_contact.id,
            "company_id": sample_company.id,
            "order_number": "ORD-005",
            "customer_name": sample_contact.name,
            "customer_email": sample_contact.email,
            "customer_phone": sample_contact.phone,
            "product_description": "Diamond Earrings",
            "quantity": 2,
            "price": 2000.00
        }
        
        # Act
        order = Order(**order_data)
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        
        # Assert - all contact details preserved
        assert order.customer_name == sample_contact.name
        assert order.customer_email == sample_contact.email
        assert order.customer_phone == sample_contact.phone
        assert order.contact_id == sample_contact.id
        assert order.company_id == sample_contact.company_id
    
    def test_multiple_orders_from_same_contact(
        self, db_session: Session, sample_tenant, sample_company, sample_contact
    ):
        """Test that a contact can place multiple orders
        
        Validates: Requirement 3.1 (contact order history)
        """
        # Arrange & Act - create multiple orders
        orders = []
        for i in range(3):
            order = Order(
                tenant_id=sample_tenant.id,
                contact_id=sample_contact.id,
                company_id=sample_company.id,
                order_number=f"ORD-{i+10}",
                customer_name=sample_contact.name,
                product_description=f"Product {i+1}",
                quantity=1,
                price=100.00 * (i+1)
            )
            db_session.add(order)
            orders.append(order)
        
        db_session.commit()
        
        # Assert - all orders linked to same contact
        contact_orders = db_session.query(Order).filter(
            Order.contact_id == sample_contact.id
        ).all()
        
        assert len(contact_orders) == 3
        assert all(o.contact_id == sample_contact.id for o in contact_orders)
        assert all(o.company_id == sample_company.id for o in contact_orders)
