"""Consolidated schema - complete database schema as of 2026-03-02

This migration replaces all previous migrations (001 through 011) with a single
consolidated migration that creates the entire schema from scratch.

For existing databases: run `alembic stamp 001_consolidated` to mark as current.
For new databases: run `alembic upgrade head` as normal.

Revision ID: 001_consolidated
Revises: (none)
Create Date: 2026-03-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '001_consolidated'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. tenants ──
    op.create_table('tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('subdomain', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tenants_id', 'tenants', ['id'])
    op.create_index('ix_tenants_subdomain', 'tenants', ['subdomain'], unique=True)

    # ── 2. permissions ──
    op.create_table('permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('resource', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_permissions_id', 'permissions', ['id'])
    op.create_index('ix_permissions_name', 'permissions', ['name'], unique=True)

    # ── 3. roles ──
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_roles_id', 'roles', ['id'])
    op.create_index('ix_roles_tenant_id', 'roles', ['tenant_id'])

    # ── 4. role_permissions ──
    op.create_table('role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id']),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    )

    # ── 5. users ──
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('failed_login_attempts', sa.Integer(), server_default='0'),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('last_failed_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_role_id', 'users', ['role_id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── 6. refresh_tokens ──
    op.create_table('refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_tokens_id', 'refresh_tokens', ['id'])
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'], unique=True)

    # ── 7. login_history ──
    op.create_table('login_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_history_id', 'login_history', ['id'])
    op.create_index('ix_login_history_tenant_id', 'login_history', ['tenant_id'])
    op.create_index('ix_login_history_user_id', 'login_history', ['user_id'])
    op.create_index('ix_login_history_timestamp', 'login_history', ['timestamp'])

    # ── 8. companies ──
    op.create_table('companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('fax', sa.String(50), nullable=True),
        sa.Column('default_address_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_company_name_per_tenant'),
    )
    op.create_index('ix_companies_id', 'companies', ['id'])
    op.create_index('ix_companies_tenant_id', 'companies', ['tenant_id'])

    # ── 9. addresses ──
    op.create_table('addresses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('street_address', sa.String(255), nullable=False),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('zip_code', sa.String(20), nullable=False),
        sa.Column('country', sa.String(100), nullable=False, server_default='USA'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_addresses_id', 'addresses', ['id'])
    op.create_index('ix_addresses_tenant_id', 'addresses', ['tenant_id'])
    op.create_index('ix_addresses_company_id', 'addresses', ['company_id'])
    op.create_index('ix_addresses_company_default', 'addresses', ['company_id', 'is_default'])

    # Now add FK from companies.default_address_id -> addresses.id
    op.create_foreign_key(
        'fk_companies_default_address',
        'companies', 'addresses',
        ['default_address_id'], ['id'],
        ondelete='SET NULL',
    )

    # ── 10. contacts (formerly customers) ──
    op.create_table('contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'company_id', 'email', name='uq_contact_email_per_company'),
    )
    op.create_index('ix_contacts_id', 'contacts', ['id'])
    op.create_index('ix_contacts_tenant_id', 'contacts', ['tenant_id'])
    op.create_index('ix_contacts_company_id', 'contacts', ['company_id'])
    op.create_index('ix_contacts_email', 'contacts', ['email'])
    op.create_index('ix_contacts_tenant_company', 'contacts', ['tenant_id', 'company_id'])

    # ── 11. metals ──
    op.create_table('metals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('fine_percentage', sa.Float(), nullable=False),
        sa.Column('average_cost_per_gram', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_metal_code_per_tenant'),
    )
    op.create_index('ix_metals_id', 'metals', ['id'])
    op.create_index('ix_metals_tenant_id', 'metals', ['tenant_id'])

    # ── 12. orders ──
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('order_number', sa.String(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=True),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('quantity', sa.Integer(), server_default='1'),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'IN_PROGRESS', 'COMPLETED', 'SHIPPED', 'CANCELLED', name='orderstatus', create_type=False), server_default='PENDING'),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('metal_id', sa.Integer(), nullable=True),
        sa.Column('target_weight_per_piece', sa.Float(), nullable=True),
        sa.Column('initial_total_weight', sa.Float(), nullable=True),
        sa.Column('labor_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], name='fk_orders_contact', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_orders_company', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['metal_id'], ['metals.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    # Create the enum type first on PostgreSQL
    orderstatus = postgresql.ENUM('PENDING', 'IN_PROGRESS', 'COMPLETED', 'SHIPPED', 'CANCELLED', name='orderstatus', create_type=False)
    orderstatus.create(op.get_bind(), checkfirst=True)

    op.create_index('ix_orders_id', 'orders', ['id'])
    op.create_index('ix_orders_tenant_id', 'orders', ['tenant_id'])
    op.create_index('ix_orders_contact_id', 'orders', ['contact_id'])
    op.create_index('ix_orders_company_id', 'orders', ['company_id'])
    op.create_index('ix_orders_order_number', 'orders', ['order_number'], unique=True)
    op.create_index('ix_orders_tenant_company', 'orders', ['tenant_id', 'company_id'])
    op.create_index('ix_orders_tenant_contact', 'orders', ['tenant_id', 'contact_id'])

    # ── 13. supplies ──
    op.create_table('supplies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Float(), server_default='0'),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('cost_per_unit', sa.Float(), nullable=True),
        sa.Column('supplier', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_supplies_id', 'supplies', ['id'])
    op.create_index('ix_supplies_tenant_id', 'supplies', ['tenant_id'])

    # ── 14. manufacturing_steps_archive ──
    op.create_table('manufacturing_steps_archive',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('parent_step_id', sa.Integer(), nullable=True),
        sa.Column('step_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('department', sa.String(), nullable=True),
        sa.Column('worker_name', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('transferred_by', sa.String(), nullable=True),
        sa.Column('received_by', sa.String(), nullable=True),
        sa.Column('quantity_received', sa.Float(), nullable=True),
        sa.Column('quantity_returned', sa.Float(), nullable=True),
        sa.Column('weight_received', sa.Float(), nullable=True),
        sa.Column('weight_returned', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['parent_step_id'], ['manufacturing_steps_archive.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_manufacturing_steps_archive_id', 'manufacturing_steps_archive', ['id'])
    op.create_index('ix_manufacturing_steps_archive_tenant_id', 'manufacturing_steps_archive', ['tenant_id'])
    op.create_index('ix_manufacturing_steps_archive_order_id', 'manufacturing_steps_archive', ['order_id'])
    op.create_index('ix_manufacturing_steps_archive_parent_step_id', 'manufacturing_steps_archive', ['parent_step_id'])

    # ── 15. shipments ──
    shipmentstatus = postgresql.ENUM('PREPARING', 'SHIPPED', 'IN_TRANSIT', 'DELIVERED', 'RETURNED', name='shipmentstatus', create_type=False)
    shipmentstatus.create(op.get_bind(), checkfirst=True)

    op.create_table('shipments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('tracking_number', sa.String(), nullable=True),
        sa.Column('carrier', sa.String(), nullable=True),
        sa.Column('shipping_address', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('PREPARING', 'SHIPPED', 'IN_TRANSIT', 'DELIVERED', 'RETURNED', name='shipmentstatus', create_type=False), server_default='PREPARING'),
        sa.Column('shipping_cost', sa.Float(), nullable=True),
        sa.Column('shipped_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_shipments_id', 'shipments', ['id'])
    op.create_index('ix_shipments_tenant_id', 'shipments', ['tenant_id'])
    op.create_index('ix_shipments_order_id', 'shipments', ['order_id'])
    op.create_index('ix_shipments_tracking_number', 'shipments', ['tracking_number'], unique=True)

    # ── 16. departments ──
    op.create_table('departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_departments_id', 'departments', ['id'])
    op.create_index('ix_departments_tenant_id', 'departments', ['tenant_id'])

    # ── 17. department_balances ──
    op.create_table('department_balances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('metal_id', sa.Integer(), nullable=False),
        sa.Column('balance_grams', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['metal_id'], ['metals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id', 'metal_id', name='uq_department_metal_id'),
    )
    op.create_index('ix_department_balances_id', 'department_balances', ['id'])
    op.create_index('ix_department_balances_tenant_id', 'department_balances', ['tenant_id'])
    op.create_index('ix_department_balances_department_id', 'department_balances', ['department_id'])

    # ── 18. lookup_values ──
    op.create_table('lookup_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('display_label', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'category', 'code', name='uq_tenant_category_code'),
    )
    op.create_index('ix_lookup_values_id', 'lookup_values', ['id'])
    op.create_index('ix_lookup_values_tenant_id', 'lookup_values', ['tenant_id'])
    op.create_index('ix_lookup_values_category', 'lookup_values', ['category'])

    # ── 19. safe_supplies ──
    op.create_table('safe_supplies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('metal_id', sa.Integer(), nullable=True),
        sa.Column('supply_type', sa.String(20), nullable=False),
        sa.Column('quantity_grams', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['metal_id'], ['metals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'metal_id', 'supply_type', name='uq_safe_supply'),
    )
    op.create_index('ix_safe_supplies_id', 'safe_supplies', ['id'])
    op.create_index('ix_safe_supplies_tenant_id', 'safe_supplies', ['tenant_id'])

    # ── 20. metal_transactions ──
    op.create_table('metal_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(30), nullable=False),
        sa.Column('metal_id', sa.Integer(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('quantity_grams', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['metal_id'], ['metals.id']),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_metal_transactions_id', 'metal_transactions', ['id'])
    op.create_index('ix_metal_transactions_tenant_id', 'metal_transactions', ['tenant_id'])

    # ── 21. company_metal_balances ──
    op.create_table('company_metal_balances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('metal_id', sa.Integer(), nullable=False),
        sa.Column('balance_grams', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['metal_id'], ['metals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'company_id', 'metal_id', name='uq_company_metal_balance'),
    )
    op.create_index('ix_company_metal_balances_id', 'company_metal_balances', ['id'])
    op.create_index('ix_company_metal_balances_tenant_id', 'company_metal_balances', ['tenant_id'])
    op.create_index('ix_company_metal_balances_company_id', 'company_metal_balances', ['company_id'])
    op.create_index('ix_company_metal_balances_metal_id', 'company_metal_balances', ['metal_id'])

    # ── 22. department_ledger_entries ──
    op.create_table('department_ledger_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('metal_id', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(3), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('fine_weight', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['metal_id'], ['metals.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_department_ledger_entries_id', 'department_ledger_entries', ['id'])
    op.create_index('ix_department_ledger_entries_tenant_id', 'department_ledger_entries', ['tenant_id'])
    op.create_index('ix_department_ledger_entries_department_id', 'department_ledger_entries', ['department_id'])
    op.create_index('ix_department_ledger_entries_order_id', 'department_ledger_entries', ['order_id'])

    # ── Database triggers (PostgreSQL only) ──
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        # Trigger: validate contact-company tenant consistency
        connection.execute(sa.text("""
            CREATE OR REPLACE FUNCTION validate_contact_company_consistency()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM companies c
                    WHERE c.id = NEW.company_id AND c.tenant_id = NEW.tenant_id
                ) THEN
                    RAISE EXCEPTION 'Contact and company must belong to the same tenant';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        connection.execute(sa.text("""
            CREATE TRIGGER trg_validate_contact_company
            BEFORE INSERT OR UPDATE ON contacts
            FOR EACH ROW EXECUTE FUNCTION validate_contact_company_consistency();
        """))

        # Trigger: validate order-contact-company consistency
        connection.execute(sa.text("""
            CREATE OR REPLACE FUNCTION validate_order_relationships()
            RETURNS TRIGGER AS $$
            DECLARE
                contact_company_id INTEGER;
                contact_tenant_id INTEGER;
            BEGIN
                SELECT company_id, tenant_id INTO contact_company_id, contact_tenant_id
                FROM contacts WHERE id = NEW.contact_id;
                IF contact_tenant_id IS NULL THEN
                    RAISE EXCEPTION 'Contact does not exist';
                END IF;
                IF contact_tenant_id != NEW.tenant_id THEN
                    RAISE EXCEPTION 'Order and contact must belong to the same tenant';
                END IF;
                IF contact_company_id != NEW.company_id THEN
                    RAISE EXCEPTION 'Order company_id must match contact company_id';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        connection.execute(sa.text("""
            CREATE TRIGGER trg_validate_order_relationships
            BEFORE INSERT OR UPDATE ON orders
            FOR EACH ROW EXECUTE FUNCTION validate_order_relationships();
        """))

        # Trigger: prevent company deletion with existing contacts
        connection.execute(sa.text("""
            CREATE OR REPLACE FUNCTION prevent_company_deletion_with_contacts()
            RETURNS TRIGGER AS $$
            BEGIN
                IF EXISTS (SELECT 1 FROM contacts WHERE company_id = OLD.id) THEN
                    RAISE EXCEPTION 'Cannot delete company with existing contacts. Delete contacts first.';
                END IF;
                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
        """))
        connection.execute(sa.text("""
            CREATE TRIGGER trg_prevent_company_deletion
            BEFORE DELETE ON companies
            FOR EACH ROW EXECUTE FUNCTION prevent_company_deletion_with_contacts();
        """))

        # Trigger: auto-set first address as default
        connection.execute(sa.text("""
            CREATE OR REPLACE FUNCTION auto_set_first_address_default()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM addresses
                    WHERE company_id = NEW.company_id AND id != NEW.id
                ) THEN
                    NEW.is_default := true;
                END IF;
                IF NEW.is_default = true THEN
                    UPDATE addresses SET is_default = false
                    WHERE company_id = NEW.company_id AND id != NEW.id AND is_default = true;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        connection.execute(sa.text("""
            CREATE TRIGGER trg_auto_set_first_address_default
            BEFORE INSERT OR UPDATE ON addresses
            FOR EACH ROW EXECUTE FUNCTION auto_set_first_address_default();
        """))

        # Trigger: prevent deletion of default address in use
        connection.execute(sa.text("""
            CREATE OR REPLACE FUNCTION prevent_default_address_deletion()
            RETURNS TRIGGER AS $$
            BEGIN
                IF OLD.is_default = true THEN
                    IF EXISTS (SELECT 1 FROM companies WHERE default_address_id = OLD.id) THEN
                        RAISE EXCEPTION 'Cannot delete default address that is referenced by company. Set a different default address first.';
                    END IF;
                END IF;
                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
        """))
        connection.execute(sa.text("""
            CREATE TRIGGER trg_prevent_default_address_deletion
            BEFORE DELETE ON addresses
            FOR EACH ROW EXECUTE FUNCTION prevent_default_address_deletion();
        """))

        connection.commit()


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        # Drop triggers and functions
        for trigger, table in [
            ('trg_prevent_default_address_deletion', 'addresses'),
            ('trg_auto_set_first_address_default', 'addresses'),
            ('trg_prevent_company_deletion', 'companies'),
            ('trg_validate_order_relationships', 'orders'),
            ('trg_validate_contact_company', 'contacts'),
        ]:
            connection.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger} ON {table}"))
        for func in [
            'prevent_default_address_deletion',
            'auto_set_first_address_default',
            'prevent_company_deletion_with_contacts',
            'validate_order_relationships',
            'validate_contact_company_consistency',
        ]:
            connection.execute(sa.text(f"DROP FUNCTION IF EXISTS {func}()"))
        connection.commit()

    # Drop tables in reverse dependency order
    op.drop_table('department_ledger_entries')
    op.drop_table('company_metal_balances')
    op.drop_table('metal_transactions')
    op.drop_table('safe_supplies')
    op.drop_table('lookup_values')
    op.drop_table('department_balances')
    op.drop_table('departments')
    op.drop_table('shipments')
    op.drop_table('manufacturing_steps_archive')
    op.drop_table('supplies')
    op.drop_table('orders')
    op.drop_table('metals')
    op.drop_table('contacts')

    # Drop FK before dropping addresses
    op.drop_constraint('fk_companies_default_address', 'companies', type_='foreignkey')
    op.drop_table('addresses')
    op.drop_table('companies')
    op.drop_table('login_history')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('tenants')

    # Drop enum types
    if op.get_bind().dialect.name == 'postgresql':
        sa.Enum(name='shipmentstatus').drop(op.get_bind(), checkfirst=True)
        sa.Enum(name='orderstatus').drop(op.get_bind(), checkfirst=True)
