"""Fixup production schema to match consolidated state

This migration brings an existing production database up to the consolidated
schema state. It checks for each change before applying, making it safe to
run on databases that already have some or all changes applied.

Revision ID: 002_fixup_prod
Revises: 001_consolidated
Create Date: 2026-03-02

"""
from alembic import op
import sqlalchemy as sa


revision = '002_fixup_prod'
down_revision = '001_consolidated'
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def _column_exists(conn, table, column):
    insp = sa.inspect(conn)
    return any(c['name'] == column for c in insp.get_columns(table))


def _index_exists(conn, name):
    insp = sa.inspect(conn)
    for table in insp.get_table_names():
        for idx in insp.get_indexes(table):
            if idx['name'] == name:
                return True
    return False


def _constraint_exists(conn, table, name):
    insp = sa.inspect(conn)
    for uc in insp.get_unique_constraints(table):
        if uc['name'] == name:
            return True
    return False


def _fk_exists(conn, table, name):
    insp = sa.inspect(conn)
    for fk in insp.get_foreign_keys(table):
        if fk['name'] == name:
            return True
    return False


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    # ── Fix: addresses table ──
    if not _table_exists(conn, 'addresses'):
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

    # ── Fix: companies columns ──
    if not _column_exists(conn, 'companies', 'fax'):
        op.add_column('companies', sa.Column('fax', sa.String(50), nullable=True))
    if not _column_exists(conn, 'companies', 'default_address_id'):
        op.add_column('companies', sa.Column('default_address_id', sa.Integer(), nullable=True))
        if not _fk_exists(conn, 'companies', 'fk_companies_default_address'):
            op.create_foreign_key('fk_companies_default_address', 'companies', 'addresses',
                                  ['default_address_id'], ['id'], ondelete='SET NULL')

    # ── Fix: customers -> contacts rename ──
    if _table_exists(conn, 'customers') and not _table_exists(conn, 'contacts'):
        op.rename_table('customers', 'contacts')
        # Recreate indexes with new names
        for old, new, cols in [
            ('ix_customers_id', 'ix_contacts_id', ['id']),
            ('ix_customers_tenant_id', 'ix_contacts_tenant_id', ['tenant_id']),
            ('ix_customers_email', 'ix_contacts_email', ['email']),
            ('ix_customers_company_id', 'ix_contacts_company_id', ['company_id']),
        ]:
            if _index_exists(conn, old):
                op.drop_index(old, table_name='contacts')
            if not _index_exists(conn, new):
                op.create_index(new, 'contacts', cols)

    # Ensure contacts.company_id is NOT NULL (may still be nullable from old schema)
    if _table_exists(conn, 'contacts') and _column_exists(conn, 'contacts', 'company_id'):
        # Make company_id NOT NULL if it isn't already
        try:
            op.alter_column('contacts', 'company_id', existing_type=sa.Integer(), nullable=False)
        except Exception:
            pass  # Already NOT NULL

    # ── Fix: contacts unique constraint ──
    if _table_exists(conn, 'contacts'):
        if not _constraint_exists(conn, 'contacts', 'uq_contact_email_per_company'):
            try:
                op.drop_constraint('uq_customer_email_per_tenant', 'contacts', type_='unique')
            except Exception:
                pass
            op.create_unique_constraint('uq_contact_email_per_company', 'contacts',
                                        ['tenant_id', 'company_id', 'email'])
        if not _index_exists(conn, 'ix_contacts_tenant_company'):
            op.create_index('ix_contacts_tenant_company', 'contacts', ['tenant_id', 'company_id'])

    # ── Fix: convert enum columns to String(50) ──
    # (must run before metals/orders fixes that reference these tables)
    if dialect == 'postgresql':
        insp = sa.inspect(conn)

        def col_is_enum(table, column):
            if not _table_exists(conn, table):
                return False
            cols = {c['name']: c for c in insp.get_columns(table)}
            if column not in cols:
                return False
            return not isinstance(cols[column]['type'], sa.String)

        if _table_exists(conn, 'supplies') and col_is_enum('supplies', 'type'):
            op.execute("ALTER TABLE supplies ALTER COLUMN type TYPE VARCHAR(50) USING type::text")

        # Drop old enum types if they exist
        op.execute("DROP TYPE IF EXISTS metaltype")
        op.execute("DROP TYPE IF EXISTS steptype")
        op.execute("DROP TYPE IF EXISTS supplytype")

    # ── Fix: metals table ──
    # (must exist before orders fixes that add metal_id FK)
    if not _table_exists(conn, 'metals'):
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

    # ── Fix: orders table columns ──
    if _table_exists(conn, 'orders'):
        # Rename customer_id -> contact_id if needed
        if _column_exists(conn, 'orders', 'customer_id') and not _column_exists(conn, 'orders', 'contact_id'):
            op.alter_column('orders', 'customer_id', new_column_name='contact_id',
                            existing_type=sa.Integer(), nullable=True)
            if _index_exists(conn, 'ix_orders_customer_id'):
                op.drop_index('ix_orders_customer_id', table_name='orders')
            if not _index_exists(conn, 'ix_orders_contact_id'):
                op.create_index('ix_orders_contact_id', 'orders', ['contact_id'])

        # Add company_id to orders if missing
        if not _column_exists(conn, 'orders', 'company_id'):
            op.add_column('orders', sa.Column('company_id', sa.Integer(), nullable=True))
            # Backfill from contacts
            conn.execute(sa.text("""
                UPDATE orders o SET company_id = c.company_id
                FROM contacts c WHERE o.contact_id = c.id
            """))
            conn.commit()
            op.alter_column('orders', 'company_id', existing_type=sa.Integer(), nullable=False)
            if not _fk_exists(conn, 'orders', 'fk_orders_company'):
                op.create_foreign_key('fk_orders_company', 'orders', 'companies',
                                      ['company_id'], ['id'], ondelete='CASCADE')
            if not _index_exists(conn, 'ix_orders_company_id'):
                op.create_index('ix_orders_company_id', 'orders', ['company_id'])

        # Add labor_cost if missing
        if not _column_exists(conn, 'orders', 'labor_cost'):
            op.add_column('orders', sa.Column('labor_cost', sa.Float(), nullable=True))

        # Add metal_id FK if missing
        if not _column_exists(conn, 'orders', 'metal_id'):
            op.add_column('orders', sa.Column('metal_id', sa.Integer(), nullable=True))
            op.create_foreign_key(None, 'orders', 'metals', ['metal_id'], ['id'])
            # Backfill from metal_type if that column exists
            if _column_exists(conn, 'orders', 'metal_type'):
                conn.execute(sa.text("""
                    UPDATE orders SET metal_id = (
                        SELECT m.id FROM metals m
                        WHERE m.code = orders.metal_type AND m.tenant_id = orders.tenant_id
                        LIMIT 1
                    ) WHERE metal_type IS NOT NULL
                """))
                conn.commit()

        # Drop old customer_* and metal_type columns
        for col in ['customer_name', 'customer_email', 'customer_phone', 'metal_type']:
            if _column_exists(conn, 'orders', col):
                op.drop_column('orders', col)

        # Composite indexes
        if not _index_exists(conn, 'ix_orders_tenant_company'):
            op.create_index('ix_orders_tenant_company', 'orders', ['tenant_id', 'company_id'])
        if not _index_exists(conn, 'ix_orders_tenant_contact'):
            op.create_index('ix_orders_tenant_contact', 'orders', ['tenant_id', 'contact_id'])

    # ── Fix: lookup_values table ──
    if not _table_exists(conn, 'lookup_values'):
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

    # ── Fix: safe_supplies table ──
    if not _table_exists(conn, 'safe_supplies'):
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

    # ── Fix: metal_transactions table ──
    if not _table_exists(conn, 'metal_transactions'):
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

    # ── Fix: company_metal_balances table ──
    if not _table_exists(conn, 'company_metal_balances'):
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

    # ── Fix: manufacturing_steps -> manufacturing_steps_archive rename ──
    if _table_exists(conn, 'manufacturing_steps') and not _table_exists(conn, 'manufacturing_steps_archive'):
        # Drop deprecated columns first (from old migration 002)
        for col in ['goods_given_quantity', 'goods_given_weight', 'goods_given_at',
                     'goods_returned_quantity', 'goods_returned_weight', 'goods_returned_at',
                     'quantity_completed', 'quantity_failed', 'quantity_rework',
                     'step_name', 'assigned_to']:
            if _column_exists(conn, 'manufacturing_steps', col):
                op.drop_column('manufacturing_steps', col)

        # Convert step_type from enum to string if needed
        if dialect == 'postgresql':
            insp = sa.inspect(conn)
            cols = {c['name']: c for c in insp.get_columns('manufacturing_steps')}
            if 'step_type' in cols and not isinstance(cols['step_type']['type'], sa.String):
                op.execute("ALTER TABLE manufacturing_steps ALTER COLUMN step_type TYPE VARCHAR(50) USING step_type::text")

        op.rename_table('manufacturing_steps', 'manufacturing_steps_archive')

        # Rename indexes
        for old, new in [
            ('ix_manufacturing_steps_id', 'ix_manufacturing_steps_archive_id'),
            ('ix_manufacturing_steps_tenant_id', 'ix_manufacturing_steps_archive_tenant_id'),
            ('ix_manufacturing_steps_order_id', 'ix_manufacturing_steps_archive_order_id'),
            ('ix_manufacturing_steps_parent_step_id', 'ix_manufacturing_steps_archive_parent_step_id'),
        ]:
            if _index_exists(conn, old):
                op.execute(f'ALTER INDEX {old} RENAME TO {new}')

    # ── Fix: department_balances.metal_type -> metal_id ──
    if _table_exists(conn, 'department_balances'):
        if _column_exists(conn, 'department_balances', 'metal_type') and not _column_exists(conn, 'department_balances', 'metal_id'):
            op.add_column('department_balances', sa.Column('metal_id', sa.Integer(), nullable=True))
            op.create_foreign_key(None, 'department_balances', 'metals', ['metal_id'], ['id'])
            conn.execute(sa.text("""
                UPDATE department_balances SET metal_id = (
                    SELECT m.id FROM metals m
                    WHERE m.code = department_balances.metal_type
                    AND m.tenant_id = department_balances.tenant_id LIMIT 1
                )
            """))
            conn.execute(sa.text("DELETE FROM department_balances WHERE metal_id IS NULL"))
            conn.commit()
            op.alter_column('department_balances', 'metal_id', nullable=False)
            if _constraint_exists(conn, 'department_balances', 'uq_department_metal_type'):
                op.drop_constraint('uq_department_metal_type', 'department_balances', type_='unique')
            op.drop_column('department_balances', 'metal_type')
        if not _constraint_exists(conn, 'department_balances', 'uq_department_metal_id'):
            op.create_unique_constraint('uq_department_metal_id', 'department_balances',
                                        ['department_id', 'metal_id'])

    # ── Fix: department_ledger_entries table ──
    if not _table_exists(conn, 'department_ledger_entries'):
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

    # ── Fix: triggers (PostgreSQL only) ──
    if dialect == 'postgresql':
        # Create triggers only if they don't exist
        for func_name, func_body, trigger_name, table in [
            ('validate_contact_company_consistency', """
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
            """, 'trg_validate_contact_company', 'contacts'),
            ('validate_order_relationships', """
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
            """, 'trg_validate_order_relationships', 'orders'),
            ('prevent_company_deletion_with_contacts', """
                CREATE OR REPLACE FUNCTION prevent_company_deletion_with_contacts()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM contacts WHERE company_id = OLD.id) THEN
                        RAISE EXCEPTION 'Cannot delete company with existing contacts.';
                    END IF;
                    RETURN OLD;
                END;
                $$ LANGUAGE plpgsql;
            """, 'trg_prevent_company_deletion', 'companies'),
            ('auto_set_first_address_default', """
                CREATE OR REPLACE FUNCTION auto_set_first_address_default()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM addresses WHERE company_id = NEW.company_id AND id != NEW.id
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
            """, 'trg_auto_set_first_address_default', 'addresses'),
            ('prevent_default_address_deletion', """
                CREATE OR REPLACE FUNCTION prevent_default_address_deletion()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF OLD.is_default = true THEN
                        IF EXISTS (SELECT 1 FROM companies WHERE default_address_id = OLD.id) THEN
                            RAISE EXCEPTION 'Cannot delete default address referenced by company.';
                        END IF;
                    END IF;
                    RETURN OLD;
                END;
                $$ LANGUAGE plpgsql;
            """, 'trg_prevent_default_address_deletion', 'addresses'),
        ]:
            # CREATE OR REPLACE handles the function idempotently
            conn.execute(sa.text(func_body))
            # Check if trigger exists before creating
            exists = conn.execute(sa.text(
                f"SELECT 1 FROM pg_trigger WHERE tgname = '{trigger_name}'"
            )).fetchone()
            if not exists:
                conn.execute(sa.text(
                    f"CREATE TRIGGER {trigger_name} BEFORE INSERT OR UPDATE ON {table} "
                    f"FOR EACH ROW EXECUTE FUNCTION {func_name}();"
                ))
        # Fix: prevent_company_deletion trigger is BEFORE DELETE, not BEFORE INSERT OR UPDATE
        conn.execute(sa.text("DROP TRIGGER IF EXISTS trg_prevent_company_deletion ON companies"))
        conn.execute(sa.text(
            "CREATE TRIGGER trg_prevent_company_deletion BEFORE DELETE ON companies "
            "FOR EACH ROW EXECUTE FUNCTION prevent_company_deletion_with_contacts();"
        ))
        # Fix: prevent_default_address_deletion trigger is BEFORE DELETE
        conn.execute(sa.text("DROP TRIGGER IF EXISTS trg_prevent_default_address_deletion ON addresses"))
        conn.execute(sa.text(
            "CREATE TRIGGER trg_prevent_default_address_deletion BEFORE DELETE ON addresses "
            "FOR EACH ROW EXECUTE FUNCTION prevent_default_address_deletion();"
        ))
        conn.commit()


def downgrade() -> None:
    # This is a one-time fixup migration — no downgrade needed
    pass
