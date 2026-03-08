"""Integration tests for database connectivity (require PostgreSQL)."""
import pytest
from sqlalchemy import text


@pytest.mark.integration
def test_database_connection(integration_db_session):
    result = integration_db_session.execute(text("SELECT 1 as value"))
    assert result.fetchone().value == 1


@pytest.mark.integration
def test_required_tables_exist(integration_db_session):
    result = integration_db_session.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    ))
    tables = [row.table_name for row in result.fetchall()]

    for table in ['tenants', 'users', 'companies', 'contacts', 'customers',
                  'orders', 'order_line_items', 'metals', 'alembic_version']:
        assert table in tables, f"Required table '{table}' not found"


@pytest.mark.integration
def test_tenant_isolation_columns(integration_db_session):
    for table in ['users', 'companies', 'contacts', 'customers',
                  'orders', 'order_line_items', 'metals']:
        result = integration_db_session.execute(text(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table}' AND column_name = 'tenant_id'"
        ))
        assert result.fetchone() is not None, f"'{table}' missing tenant_id"
