"""
Unit tests for the order line items data migration script.

Tests verify that the migration correctly converts single-line orders
to order_line_items records while preserving all data.

Requirements: 3.6, 3.7
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.data.database import Base
from app.data.models.tenant import Tenant
from app.data.models.company import Company
from app.data.models.contact import Contact
from app.data.models.order import Order
from app.domain.enums import OrderStatus


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_data(test_session):
    """Create sample tenant, company, contact, and orders for testing."""
    # Create tenant
    tenant = Tenant(
        id=1,
        name="Test Jewelry Co",
        subdomain="testjewelry",
        is_active=True
    )
    test_session.add(tenant)
    
    # Create company
    company = Company(
        id=1,
        tenant_id=1,
        name="Test Company",
        email="company@test.com"
    )
    test_session.add(company)
    
    # Create contact
    contact = Contact(
        id=1,
        tenant_id=1,
        company_id=1,
        name="John Doe",
        email="john@test.com"
    )
    test_session.add(contact)
    
    # Create orders with product descriptions (need migration)
    order1 = Order(
        id=1,
        tenant_id=1,
        order_number="ORD-001",
        contact_id=1,
        company_id=1,
        product_description="Gold Ring",
        specifications="18K, size 7",
        metal_id=1,
        quantity=10,
        target_weight_per_piece=8.5,
        initial_total_weight=90.0,
        price=500.00,
        labor_cost=100.00,
        status=OrderStatus.PENDING
    )
    test_session.add(order1)
    
    order2 = Order(
        id=2,
        tenant_id=1,
        order_number="ORD-002",
        contact_id=1,
        company_id=1,
        product_description="Silver Necklace",
        specifications="925 Sterling",
        metal_id=2,
        quantity=5,
        target_weight_per_piece=15.0,
        initial_total_weight=80.0,
        price=300.00,
        labor_cost=50.00,
        status=OrderStatus.PENDING
    )
    test_session.add(order2)
    
    # Create order without product description (should be skipped)
    order3 = Order(
        id=3,
        tenant_id=1,
        order_number="ORD-003",
        contact_id=1,
        company_id=1,
        product_description=None,
        status=OrderStatus.PENDING
    )
    test_session.add(order3)
    
    # Create order with empty product description (should be skipped)
    order4 = Order(
        id=4,
        tenant_id=1,
        order_number="ORD-004",
        contact_id=1,
        company_id=1,
        product_description="",
        status=OrderStatus.PENDING
    )
    test_session.add(order4)
    
    test_session.commit()
    
    return {
        "tenant": tenant,
        "company": company,
        "contact": contact,
        "orders": [order1, order2, order3, order4]
    }


def test_migration_creates_line_items(test_session, sample_data):
    """Test that migration creates line items for orders with product descriptions."""
    # Import migration function
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from scripts.migrate_orders_to_line_items import migrate_orders_to_line_items
    
    # Run migration
    orders_processed, line_items_created, orders_skipped = migrate_orders_to_line_items(
        database_url=TEST_DATABASE_URL,
        dry_run=False
    )
    
    # Verify counts
    assert orders_processed == 2, "Should process 2 orders with product descriptions"
    assert line_items_created == 2, "Should create 2 line items"
    assert orders_skipped == 0, "Should skip 0 orders (none already migrated)"
    
    # Verify line items were created
    result = test_session.execute(text("SELECT COUNT(*) FROM order_line_items"))
    count = result.scalar()
    assert count == 2, "Should have 2 line items in database"
    
    # Verify line item data for order 1
    result = test_session.execute(
        text("""
            SELECT product_description, specifications, metal_id, quantity, 
                   target_weight_per_piece, initial_total_weight, price, labor_cost
            FROM order_line_items 
            WHERE order_id = 1
        """)
    )
    line_item = result.fetchone()
    assert line_item is not None
    assert line_item.product_description == "Gold Ring"
    assert line_item.specifications == "18K, size 7"
    assert line_item.metal_id == 1
    assert line_item.quantity == 10
    assert line_item.target_weight_per_piece == 8.5
    assert line_item.initial_total_weight == 90.0
    assert line_item.price == 500.00
    assert line_item.labor_cost == 100.00


def test_migration_is_idempotent(test_session, sample_data):
    """Test that running migration multiple times doesn't create duplicates."""
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from scripts.migrate_orders_to_line_items import migrate_orders_to_line_items
    
    # Run migration first time
    orders_processed_1, line_items_created_1, orders_skipped_1 = migrate_orders_to_line_items(
        database_url=TEST_DATABASE_URL,
        dry_run=False
    )
    
    assert orders_processed_1 == 2
    assert line_items_created_1 == 2
    assert orders_skipped_1 == 0
    
    # Run migration second time
    orders_processed_2, line_items_created_2, orders_skipped_2 = migrate_orders_to_line_items(
        database_url=TEST_DATABASE_URL,
        dry_run=False
    )
    
    # Should skip all orders since they're already migrated
    assert orders_processed_2 == 0, "Should process 0 orders on second run"
    assert line_items_created_2 == 0, "Should create 0 line items on second run"
    assert orders_skipped_2 == 2, "Should skip 2 orders that are already migrated"
    
    # Verify still only 2 line items (no duplicates)
    result = test_session.execute(text("SELECT COUNT(*) FROM order_line_items"))
    count = result.scalar()
    assert count == 2, "Should still have only 2 line items (no duplicates)"


def test_migration_dry_run(test_session, sample_data):
    """Test that dry run mode doesn't make any changes."""
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from scripts.migrate_orders_to_line_items import migrate_orders_to_line_items
    
    # Run migration in dry-run mode
    orders_processed, line_items_created, orders_skipped = migrate_orders_to_line_items(
        database_url=TEST_DATABASE_URL,
        dry_run=True
    )
    
    # Should report what would be done
    assert orders_processed == 2, "Should report 2 orders would be processed"
    assert line_items_created == 2, "Should report 2 line items would be created"
    
    # Verify no line items were actually created
    result = test_session.execute(text("SELECT COUNT(*) FROM order_line_items"))
    count = result.scalar()
    assert count == 0, "Should have 0 line items after dry run"


def test_migration_skips_orders_without_description(test_session, sample_data):
    """Test that orders without product_description are not migrated."""
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from scripts.migrate_orders_to_line_items import migrate_orders_to_line_items
    
    # Run migration
    migrate_orders_to_line_items(database_url=TEST_DATABASE_URL, dry_run=False)
    
    # Verify orders 3 and 4 (without descriptions) have no line items
    result = test_session.execute(
        text("SELECT COUNT(*) FROM order_line_items WHERE order_id IN (3, 4)")
    )
    count = result.scalar()
    assert count == 0, "Orders without product_description should not have line items"


def test_migration_preserves_all_fields(test_session, sample_data):
    """Test that all order fields are correctly copied to line items."""
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from scripts.migrate_orders_to_line_items import migrate_orders_to_line_items
    
    # Run migration
    migrate_orders_to_line_items(database_url=TEST_DATABASE_URL, dry_run=False)
    
    # Get original order data
    order = test_session.query(Order).filter(Order.id == 2).first()
    
    # Get line item data
    result = test_session.execute(
        text("""
            SELECT tenant_id, order_id, product_description, specifications, 
                   metal_id, quantity, target_weight_per_piece, initial_total_weight, 
                   price, labor_cost
            FROM order_line_items 
            WHERE order_id = 2
        """)
    )
    line_item = result.fetchone()
    
    # Verify all fields match
    assert line_item.tenant_id == order.tenant_id
    assert line_item.order_id == order.id
    assert line_item.product_description == order.product_description
    assert line_item.specifications == order.specifications
    assert line_item.metal_id == order.metal_id
    assert line_item.quantity == order.quantity
    assert line_item.target_weight_per_piece == order.target_weight_per_piece
    assert line_item.initial_total_weight == order.initial_total_weight
    assert line_item.price == order.price
    assert line_item.labor_cost == order.labor_cost


def test_migration_handles_null_optional_fields(test_session, sample_data):
    """Test that migration handles orders with null optional fields."""
    # Create order with minimal data
    order = Order(
        id=5,
        tenant_id=1,
        order_number="ORD-005",
        contact_id=1,
        company_id=1,
        product_description="Minimal Order",
        specifications=None,
        metal_id=None,
        quantity=1,
        target_weight_per_piece=None,
        initial_total_weight=None,
        price=None,
        labor_cost=None,
        status=OrderStatus.PENDING
    )
    test_session.add(order)
    test_session.commit()
    
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from scripts.migrate_orders_to_line_items import migrate_orders_to_line_items
    
    # Run migration
    migrate_orders_to_line_items(database_url=TEST_DATABASE_URL, dry_run=False)
    
    # Verify line item was created with null fields
    result = test_session.execute(
        text("""
            SELECT product_description, specifications, metal_id, 
                   target_weight_per_piece, initial_total_weight, price, labor_cost
            FROM order_line_items 
            WHERE order_id = 5
        """)
    )
    line_item = result.fetchone()
    
    assert line_item is not None
    assert line_item.product_description == "Minimal Order"
    assert line_item.specifications is None
    assert line_item.metal_id is None
    assert line_item.target_weight_per_piece is None
    assert line_item.initial_total_weight is None
    assert line_item.price is None
    assert line_item.labor_cost is None
