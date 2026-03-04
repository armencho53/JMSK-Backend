"""
Integration test to verify database connectivity and basic operations.

This test runs against the actual database specified in DATABASE_URL.
"""

import pytest
from sqlalchemy import text


@pytest.mark.integration
def test_database_connection(integration_db_session):
    """Test that we can connect to the database and execute queries."""
    result = integration_db_session.execute(text("SELECT 1 as value"))
    row = result.fetchone()
    assert row.value == 1


@pytest.mark.integration
def test_database_has_required_tables(integration_db_session):
    """Test that all required tables exist in the database."""
    # Query to get all table names
    result = integration_db_session.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    
    tables = [row.table_name for row in result.fetchall()]
    
    # Verify core tables exist
    required_tables = [
        'tenants',
        'users',
        'companies',
        'contacts',
        'customers',
        'orders',
        'order_line_items',
        'metals',
        'metal_prices',
        'alembic_version'
    ]
    
    for table in required_tables:
        assert table in tables, f"Required table '{table}' not found in database"


@pytest.mark.integration
def test_alembic_version_exists(integration_db_session):
    """Test that the database has migration version tracking."""
    result = integration_db_session.execute(text("""
        SELECT version_num 
        FROM alembic_version 
        LIMIT 1
    """))
    
    row = result.fetchone()
    assert row is not None, "No alembic version found"
    assert row.version_num is not None, "Alembic version is null"
    
    print(f"Database is at migration version: {row.version_num}")


@pytest.mark.integration
def test_tenant_isolation_setup(integration_db_session):
    """Test that tenant_id columns exist on multi-tenant tables."""
    # Check that key tables have tenant_id column
    multi_tenant_tables = [
        'users',
        'companies',
        'contacts',
        'customers',
        'orders',
        'order_line_items',
        'metals',
        'metal_prices'
    ]
    
    for table in multi_tenant_tables:
        result = integration_db_session.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table}' 
            AND column_name = 'tenant_id'
        """))
        
        row = result.fetchone()
        assert row is not None, f"Table '{table}' missing tenant_id column for multi-tenant isolation"
