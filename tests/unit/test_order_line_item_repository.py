"""Unit tests for OrderLineItemRepository"""
import pytest
from app.data.repositories.order_line_item_repository import OrderLineItemRepository
from app.data.models.order_line_item import OrderLineItem
from app.data.models.order import Order
from app.data.models.tenant import Tenant
from app.data.models.contact import Contact
from app.data.models.company import Company
from app.data.models.metal import Metal
from app.domain.enums import OrderStatus


@pytest.fixture
def seed_data(db_session):
    """Create test data for order line item repository tests."""
    # Create tenant
    tenant = Tenant(
        name="Test Jewelry Co",
        subdomain="testjewelry",
        is_active=True
    )
    db_session.add(tenant)
    db_session.flush()
    
    # Create another tenant for isolation testing
    tenant2 = Tenant(
        name="Other Jewelry Co",
        subdomain="otherjewelry",
        is_active=True
    )
    db_session.add(tenant2)
    db_session.flush()
    
    # Create metal
    metal = Metal(
        tenant_id=tenant.id,
        code="GOLD24K",
        name="Gold 24K",
        fine_percentage=99.9,
        average_cost_per_gram=50.0,
        is_active=True
    )
    db_session.add(metal)
    db_session.flush()
    
    # Create company
    company = Company(
        tenant_id=tenant.id,
        name="Test Company",
        email="company@test.com"
    )
    db_session.add(company)
    db_session.flush()
    
    # Create contact
    contact = Contact(
        tenant_id=tenant.id,
        company_id=company.id,
        name="Test Contact",
        email="contact@test.com"
    )
    db_session.add(contact)
    db_session.flush()
    
    # Create order
    order = Order(
        tenant_id=tenant.id,
        order_number="ORD-001",
        contact_id=contact.id,
        company_id=company.id,
        product_description="Test Order",
        quantity=1,
        price=1000.0,
        status=OrderStatus.PENDING
    )
    db_session.add(order)
    db_session.flush()
    
    # Create another order for the same tenant
    order2 = Order(
        tenant_id=tenant.id,
        order_number="ORD-002",
        contact_id=contact.id,
        company_id=company.id,
        product_description="Test Order 2",
        quantity=1,
        price=2000.0,
        status=OrderStatus.PENDING
    )
    db_session.add(order2)
    db_session.flush()
    
    # Create line items for order 1
    line_item1 = OrderLineItem(
        tenant_id=tenant.id,
        order_id=order.id,
        product_description="Gold Ring",
        specifications="24K Gold, Size 7",
        metal_id=metal.id,
        quantity=2,
        target_weight_per_piece=5.0,
        initial_total_weight=12.0,
        price=500.0,
        labor_cost=100.0
    )
    db_session.add(line_item1)
    
    line_item2 = OrderLineItem(
        tenant_id=tenant.id,
        order_id=order.id,
        product_description="Gold Necklace",
        specifications="24K Gold, 18 inches",
        metal_id=metal.id,
        quantity=1,
        target_weight_per_piece=15.0,
        initial_total_weight=16.0,
        price=800.0,
        labor_cost=200.0
    )
    db_session.add(line_item2)
    
    # Create line item for order 2
    line_item3 = OrderLineItem(
        tenant_id=tenant.id,
        order_id=order2.id,
        product_description="Gold Bracelet",
        metal_id=metal.id,
        quantity=1,
        target_weight_per_piece=10.0,
        initial_total_weight=11.0,
        price=600.0
    )
    db_session.add(line_item3)
    
    # Create line item for tenant 2 (for isolation testing)
    order_tenant2 = Order(
        tenant_id=tenant2.id,
        order_number="ORD-T2-001",
        contact_id=contact.id,  # Using same contact ID (different tenant)
        company_id=company.id,  # Using same company ID (different tenant)
        product_description="Tenant 2 Order",
        quantity=1,
        price=500.0,
        status=OrderStatus.PENDING
    )
    db_session.add(order_tenant2)
    db_session.flush()
    
    line_item_tenant2 = OrderLineItem(
        tenant_id=tenant2.id,
        order_id=order_tenant2.id,
        product_description="Tenant 2 Item",
        quantity=1,
        price=300.0
    )
    db_session.add(line_item_tenant2)
    
    db_session.commit()
    
    return {
        "tenant_id": tenant.id,
        "tenant2_id": tenant2.id,
        "order_id": order.id,
        "order2_id": order2.id,
        "order_tenant2_id": order_tenant2.id,
        "line_item1_id": line_item1.id,
        "line_item2_id": line_item2.id,
        "line_item3_id": line_item3.id,
        "line_item_tenant2_id": line_item_tenant2.id,
        "metal_id": metal.id
    }


class TestOrderLineItemRepository:
    """Test suite for OrderLineItemRepository (Requirements 3.6, 3.9)"""
    
    def test_get_by_order_returns_all_line_items(self, db_session, seed_data):
        """get_by_order should return all line items for a specific order (Requirement 3.6)"""
        repo = OrderLineItemRepository(db_session)
        
        line_items = repo.get_by_order(
            order_id=seed_data["order_id"],
            tenant_id=seed_data["tenant_id"]
        )
        
        assert len(line_items) == 2
        descriptions = [item.product_description for item in line_items]
        assert "Gold Ring" in descriptions
        assert "Gold Necklace" in descriptions
    
    def test_get_by_order_returns_empty_list_for_no_items(self, db_session, seed_data):
        """get_by_order should return empty list when order has no line items (Requirement 3.6)"""
        repo = OrderLineItemRepository(db_session)
        
        # Create a new order without line items
        company = db_session.query(Company).filter_by(tenant_id=seed_data["tenant_id"]).first()
        contact = db_session.query(Contact).filter_by(tenant_id=seed_data["tenant_id"]).first()
        
        empty_order = Order(
            tenant_id=seed_data["tenant_id"],
            order_number="ORD-EMPTY",
            contact_id=contact.id,
            company_id=company.id,
            product_description="Empty Order",
            quantity=1,
            price=100.0,
            status=OrderStatus.PENDING
        )
        db_session.add(empty_order)
        db_session.commit()
        
        line_items = repo.get_by_order(
            order_id=empty_order.id,
            tenant_id=seed_data["tenant_id"]
        )
        
        assert len(line_items) == 0
    
    def test_get_by_order_enforces_tenant_isolation(self, db_session, seed_data):
        """get_by_order should not return line items from other tenants (Requirement 3.6)"""
        repo = OrderLineItemRepository(db_session)
        
        # Try to get tenant 2's order using tenant 1's ID
        line_items = repo.get_by_order(
            order_id=seed_data["order_tenant2_id"],
            tenant_id=seed_data["tenant_id"]
        )
        
        assert len(line_items) == 0
    
    def test_get_by_order_filters_by_specific_order(self, db_session, seed_data):
        """get_by_order should only return line items for the specified order (Requirement 3.6)"""
        repo = OrderLineItemRepository(db_session)
        
        # Get line items for order 2
        line_items = repo.get_by_order(
            order_id=seed_data["order2_id"],
            tenant_id=seed_data["tenant_id"]
        )
        
        assert len(line_items) == 1
        assert line_items[0].product_description == "Gold Bracelet"
        assert line_items[0].order_id == seed_data["order2_id"]
    
    def test_delete_by_order_removes_all_line_items(self, db_session, seed_data):
        """delete_by_order should remove all line items for a specific order (Requirement 3.9)"""
        repo = OrderLineItemRepository(db_session)
        
        # Verify line items exist before deletion
        line_items_before = repo.get_by_order(
            order_id=seed_data["order_id"],
            tenant_id=seed_data["tenant_id"]
        )
        assert len(line_items_before) == 2
        
        # Delete line items
        repo.delete_by_order(
            order_id=seed_data["order_id"],
            tenant_id=seed_data["tenant_id"]
        )
        
        # Verify line items are deleted
        line_items_after = repo.get_by_order(
            order_id=seed_data["order_id"],
            tenant_id=seed_data["tenant_id"]
        )
        assert len(line_items_after) == 0
    
    def test_delete_by_order_enforces_tenant_isolation(self, db_session, seed_data):
        """delete_by_order should not delete line items from other tenants (Requirement 3.9)"""
        repo = OrderLineItemRepository(db_session)
        
        # Try to delete tenant 2's line items using tenant 1's ID
        repo.delete_by_order(
            order_id=seed_data["order_tenant2_id"],
            tenant_id=seed_data["tenant_id"]
        )
        
        # Verify tenant 2's line items still exist
        line_items = repo.get_by_order(
            order_id=seed_data["order_tenant2_id"],
            tenant_id=seed_data["tenant2_id"]
        )
        assert len(line_items) == 1
    
    def test_delete_by_order_only_deletes_specified_order(self, db_session, seed_data):
        """delete_by_order should only delete line items for the specified order (Requirement 3.9)"""
        repo = OrderLineItemRepository(db_session)
        
        # Delete line items for order 1
        repo.delete_by_order(
            order_id=seed_data["order_id"],
            tenant_id=seed_data["tenant_id"]
        )
        
        # Verify order 2's line items still exist
        line_items_order2 = repo.get_by_order(
            order_id=seed_data["order2_id"],
            tenant_id=seed_data["tenant_id"]
        )
        assert len(line_items_order2) == 1
        assert line_items_order2[0].product_description == "Gold Bracelet"
    
    def test_create_line_item(self, db_session, seed_data):
        """create should add a new line item to the database (BaseRepository method)"""
        repo = OrderLineItemRepository(db_session)
        
        new_line_item = OrderLineItem(
            tenant_id=seed_data["tenant_id"],
            order_id=seed_data["order_id"],
            product_description="Gold Earrings",
            specifications="24K Gold, Stud style",
            metal_id=seed_data["metal_id"],
            quantity=1,
            target_weight_per_piece=3.0,
            initial_total_weight=3.5,
            price=300.0,
            labor_cost=50.0
        )
        
        created_item = repo.create(new_line_item)
        
        assert created_item.id is not None
        assert created_item.product_description == "Gold Earrings"
        assert created_item.quantity == 1
        assert created_item.price == 300.0
        
        # Verify it's in the database
        line_items = repo.get_by_order(
            order_id=seed_data["order_id"],
            tenant_id=seed_data["tenant_id"]
        )
        assert len(line_items) == 3
    
    def test_update_line_item(self, db_session, seed_data):
        """update should modify an existing line item (BaseRepository method)"""
        repo = OrderLineItemRepository(db_session)
        
        # Get existing line item
        line_item = repo.get_by_id(
            id=seed_data["line_item1_id"],
            tenant_id=seed_data["tenant_id"]
        )
        
        # Update fields
        line_item.quantity = 5
        line_item.price = 1200.0
        line_item.specifications = "Updated specifications"
        
        updated_item = repo.update(line_item)
        
        assert updated_item.quantity == 5
        assert updated_item.price == 1200.0
        assert updated_item.specifications == "Updated specifications"
        
        # Verify changes persisted
        retrieved_item = repo.get_by_id(
            id=seed_data["line_item1_id"],
            tenant_id=seed_data["tenant_id"]
        )
        assert retrieved_item.quantity == 5
        assert retrieved_item.price == 1200.0
    
    def test_get_by_id_with_tenant_filtering(self, db_session, seed_data):
        """get_by_id should enforce tenant isolation (BaseRepository method)"""
        repo = OrderLineItemRepository(db_session)
        
        # Get line item with correct tenant
        line_item = repo.get_by_id(
            id=seed_data["line_item1_id"],
            tenant_id=seed_data["tenant_id"]
        )
        assert line_item is not None
        assert line_item.product_description == "Gold Ring"
        
        # Try to get same line item with wrong tenant
        line_item_wrong_tenant = repo.get_by_id(
            id=seed_data["line_item1_id"],
            tenant_id=seed_data["tenant2_id"]
        )
        assert line_item_wrong_tenant is None
