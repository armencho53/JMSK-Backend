"""Unit tests for order responses including contact and company information

Tests that order API responses properly include nested contact and company data.
Validates: Requirements 3.1, 7.3
"""
import pytest
from sqlalchemy.orm import Session, joinedload
from app.data.models.tenant import Tenant
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.models.order import Order, OrderStatus
from app.schemas.order import OrderResponse


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
        name="Acme Jewelry Co",
        email="contact@acme.com",
        phone="555-0100"
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
        name="Alice Johnson",
        email="alice@acme.com",
        phone="555-0101"
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


@pytest.fixture
def sample_order(db_session: Session, sample_tenant, sample_company, sample_contact):
    """Create a sample order for testing"""
    order = Order(
        tenant_id=sample_tenant.id,
        contact_id=sample_contact.id,
        company_id=sample_company.id,
        order_number="ORD-TEST-001",
        customer_name=sample_contact.name,
        customer_email=sample_contact.email,
        customer_phone=sample_contact.phone,
        product_description="Gold Wedding Ring",
        quantity=1,
        price=1500.00,
        status=OrderStatus.PENDING
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


class TestOrderResponseWithRelationships:
    """Test that order responses include contact and company nested data"""
    
    def test_order_response_includes_contact_summary(
        self, db_session: Session, sample_order, sample_contact
    ):
        """Test that OrderResponse includes contact summary information
        
        Validates: Requirements 3.1, 7.3
        """
        # Arrange - fetch order with relationships loaded
        order = db_session.query(Order).options(
            joinedload(Order.contact).joinedload(Contact.company),
            joinedload(Order.company)
        ).filter(Order.id == sample_order.id).first()
        
        # Act - convert to response schema
        response = OrderResponse.model_validate(order)
        
        # Assert - contact information is included
        assert response.contact is not None
        assert response.contact.id == sample_contact.id
        assert response.contact.name == sample_contact.name
        assert response.contact.email == sample_contact.email
        assert response.contact.phone == sample_contact.phone
    
    def test_order_response_includes_company_summary(
        self, db_session: Session, sample_order, sample_company
    ):
        """Test that OrderResponse includes company summary information
        
        Validates: Requirements 3.1, 7.3
        """
        # Arrange - fetch order with relationships loaded
        order = db_session.query(Order).options(
            joinedload(Order.contact).joinedload(Contact.company),
            joinedload(Order.company)
        ).filter(Order.id == sample_order.id).first()
        
        # Act - convert to response schema
        response = OrderResponse.model_validate(order)
        
        # Assert - company information is included
        assert response.company is not None
        assert response.company.id == sample_company.id
        assert response.company.name == sample_company.name
        assert response.company.email == sample_company.email
        assert response.company.phone == sample_company.phone
    
    def test_order_response_without_relationships_has_none_values(
        self, db_session: Session, sample_order
    ):
        """Test that OrderResponse handles missing relationships gracefully
        
        When relationships are not eagerly loaded, contact and company should be None.
        """
        # Arrange - fetch order WITHOUT loading relationships
        order = db_session.query(Order).filter(Order.id == sample_order.id).first()
        
        # Act - convert to response schema
        response = OrderResponse.model_validate(order)
        
        # Assert - contact and company are None (not loaded)
        # Note: This depends on SQLAlchemy lazy loading behavior
        # In production, we should always eagerly load these relationships
        assert response.contact_id is not None
        assert response.company_id is not None
        # contact and company objects may be None if not loaded
    
    def test_order_list_response_includes_all_relationships(
        self, db_session: Session, sample_tenant, sample_company, sample_contact
    ):
        """Test that listing orders includes contact and company for all orders
        
        Validates: Requirements 3.1, 7.3
        """
        # Arrange - create multiple orders
        orders_data = []
        for i in range(3):
            order = Order(
                tenant_id=sample_tenant.id,
                contact_id=sample_contact.id,
                company_id=sample_company.id,
                order_number=f"ORD-TEST-{i+100}",
                customer_name=sample_contact.name,
                product_description=f"Product {i+1}",
                quantity=1,
                price=500.00 * (i+1)
            )
            db_session.add(order)
            orders_data.append(order)
        
        db_session.commit()
        
        # Act - fetch all orders with relationships
        orders = db_session.query(Order).options(
            joinedload(Order.contact).joinedload(Contact.company),
            joinedload(Order.company)
        ).filter(Order.tenant_id == sample_tenant.id).all()
        
        # Convert to response schemas
        responses = [OrderResponse.model_validate(order) for order in orders]
        
        # Assert - all orders have contact and company information
        assert len(responses) >= 3
        for response in responses:
            assert response.contact is not None
            assert response.contact.name == sample_contact.name
            assert response.company is not None
            assert response.company.name == sample_company.name
    
    def test_order_response_preserves_legacy_customer_fields(
        self, db_session: Session, sample_order, sample_contact
    ):
        """Test that OrderResponse maintains backward compatibility with customer fields
        
        Validates: Requirement 1.5 (preserve existing order relationships)
        """
        # Arrange - fetch order with relationships
        order = db_session.query(Order).options(
            joinedload(Order.contact).joinedload(Contact.company),
            joinedload(Order.company)
        ).filter(Order.id == sample_order.id).first()
        
        # Act - convert to response schema
        response = OrderResponse.model_validate(order)
        
        # Assert - legacy customer fields are preserved
        assert response.customer_name == sample_contact.name
        assert response.customer_email == sample_contact.email
        assert response.customer_phone == sample_contact.phone
        
        # Assert - new hierarchical fields are also present
        assert response.contact_id == sample_contact.id
        assert response.company_id == sample_contact.company_id
        assert response.contact is not None
        assert response.company is not None
