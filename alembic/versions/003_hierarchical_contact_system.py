"""Hierarchical contact system migration

Revision ID: 003_hierarchical_contact_system
Revises: 002_remove_deprecated
Create Date: 2025-01-23 10:00:00.000000

This migration implements the hierarchical contact system by:
1. Renaming customers table to contacts
2. Making company_id required for contacts
3. Adding company_id to orders table
4. Creating addresses table for company addresses
5. Adding default_address_id and fax to companies table
6. Adding performance indexes
7. Adding check constraints for data validation
8. Creating database triggers for referential integrity and business rules

Requirements: 1.1, 1.3, 1.4, 1.6, 8.1, 8.2, 8.4

Constraints Added:
- Foreign key constraints for referential integrity
- Unique constraints for contact-company relationships
- Check constraints for email, phone, fax, and zip code validation
- Check constraint to ensure only one default address per company

Triggers Added:
- validate_contact_company_consistency: Ensures contact and company belong to same tenant
- validate_order_relationships: Ensures order, contact, and company relationships are consistent
- prevent_company_deletion_with_contacts: Prevents deletion of companies with existing contacts
- auto_set_first_address_default: Automatically sets first address as default
- prevent_default_address_deletion: Prevents deletion of default addresses in use
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '003_hierarchical_contact_system'
down_revision = '002_remove_deprecated'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade database schema to support hierarchical contact system.
    
    This migration transforms the existing customer-company structure into
    a hierarchical contact system where:
    - Customers become Contacts (renamed table)
    - Every Contact must belong to a Company (company_id becomes NOT NULL)
    - Orders reference both Contact and Company
    - Companies can have multiple Addresses
    - Companies have a default address for shipments
    """
    
    # Step 1: Create addresses table first (needed for companies.default_address_id FK)
    op.create_table('addresses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('street_address', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('zip_code', sa.String(length=20), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False, server_default='USA'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for addresses table
    op.create_index(op.f('ix_addresses_id'), 'addresses', ['id'], unique=False)
    op.create_index(op.f('ix_addresses_tenant_id'), 'addresses', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_addresses_company_id'), 'addresses', ['company_id'], unique=False)
    op.create_index('ix_addresses_company_default', 'addresses', ['company_id', 'is_default'], unique=False)
    
    # Step 2: Add new columns to companies table
    op.add_column('companies', sa.Column('fax', sa.String(length=50), nullable=True))
    op.add_column('companies', sa.Column('default_address_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint for default_address_id (nullable for now)
    op.create_foreign_key(
        'fk_companies_default_address',
        'companies', 'addresses',
        ['default_address_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Step 3: Rename customers table to contacts
    op.rename_table('customers', 'contacts')
    
    # Step 4: Update indexes after table rename
    # Drop old indexes
    op.drop_index('ix_customers_id', table_name='contacts')
    op.drop_index('ix_customers_tenant_id', table_name='contacts')
    op.drop_index('ix_customers_email', table_name='contacts')
    op.drop_index('ix_customers_company_id', table_name='contacts')
    
    # Create new indexes with correct naming
    op.create_index(op.f('ix_contacts_id'), 'contacts', ['id'], unique=False)
    op.create_index(op.f('ix_contacts_tenant_id'), 'contacts', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_contacts_email'), 'contacts', ['email'], unique=False)
    op.create_index(op.f('ix_contacts_company_id'), 'contacts', ['company_id'], unique=False)
    
    # Step 5: Update unique constraint on contacts table
    # Drop old constraint
    op.drop_constraint('uq_customer_email_per_tenant', 'contacts', type_='unique')
    
    # Create new constraint allowing same email across companies but not within same company
    op.create_unique_constraint(
        'uq_contact_email_per_company',
        'contacts',
        ['tenant_id', 'company_id', 'email']
    )
    
    # Step 6: Ensure all contacts have a company_id before making it NOT NULL
    # First, create a default company for any orphaned contacts
    connection = op.get_bind()
    
    # Find tenants with contacts that have NULL company_id
    orphaned_contacts = connection.execute(
        sa.text("""
            SELECT DISTINCT c.tenant_id 
            FROM contacts c 
            WHERE c.company_id IS NULL
        """)
    ).fetchall()
    
    # For each tenant with orphaned contacts, create a default company
    for row in orphaned_contacts:
        tenant_id = row[0]
        
        # Create default company
        result = connection.execute(
            sa.text("""
                INSERT INTO companies (tenant_id, name, created_at, updated_at)
                VALUES (:tenant_id, 'Default Company', :now, :now)
                RETURNING id
            """),
            {"tenant_id": tenant_id, "now": datetime.utcnow()}
        )
        company_id = result.fetchone()[0]
        
        # Update orphaned contacts to use this company
        connection.execute(
            sa.text("""
                UPDATE contacts 
                SET company_id = :company_id 
                WHERE tenant_id = :tenant_id AND company_id IS NULL
            """),
            {"company_id": company_id, "tenant_id": tenant_id}
        )
    
    connection.commit()
    
    # Now make company_id NOT NULL
    op.alter_column('contacts', 'company_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Step 7: Add company_id column to orders table
    op.add_column('orders', sa.Column('company_id', sa.Integer(), nullable=True))
    
    # Populate company_id in orders from the contact's company
    connection.execute(
        sa.text("""
            UPDATE orders o
            SET company_id = c.company_id
            FROM contacts c
            WHERE o.customer_id = c.id
        """)
    )
    connection.commit()
    
    # Make company_id NOT NULL after populating
    op.alter_column('orders', 'company_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Add foreign key constraint for orders.company_id
    op.create_foreign_key(
        'fk_orders_company',
        'orders', 'companies',
        ['company_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add index for orders.company_id for performance
    op.create_index(op.f('ix_orders_company_id'), 'orders', ['company_id'], unique=False)
    
    # Step 8: Rename customer_id to contact_id in orders table
    op.alter_column('orders', 'customer_id',
                    new_column_name='contact_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # Update foreign key constraint name
    op.drop_constraint('orders_customer_id_fkey', 'orders', type_='foreignkey')
    op.create_foreign_key(
        'fk_orders_contact',
        'orders', 'contacts',
        ['contact_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Update index name
    op.drop_index('ix_orders_customer_id', table_name='orders')
    op.create_index(op.f('ix_orders_contact_id'), 'orders', ['contact_id'], unique=False)
    
    # Step 9: Add composite indexes for common query patterns
    # Index for fetching all contacts for a company (filtered by tenant)
    op.create_index(
        'ix_contacts_tenant_company',
        'contacts',
        ['tenant_id', 'company_id'],
        unique=False
    )
    
    # Index for fetching all orders for a company (filtered by tenant)
    op.create_index(
        'ix_orders_tenant_company',
        'orders',
        ['tenant_id', 'company_id'],
        unique=False
    )
    
    # Index for fetching all orders for a contact (filtered by tenant)
    op.create_index(
        'ix_orders_tenant_contact',
        'orders',
        ['tenant_id', 'contact_id'],
        unique=False
    )
    
    # Step 10: Add check constraints for data validation (Requirement 8.4)
    # Validate email format for contacts
    op.create_check_constraint(
        'ck_contacts_email_format',
        'contacts',
        "email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'"
    )
    
    # Validate phone format for contacts (basic validation)
    op.create_check_constraint(
        'ck_contacts_phone_format',
        'contacts',
        "phone IS NULL OR length(phone) >= 10"
    )
    
    # Validate email format for companies
    op.create_check_constraint(
        'ck_companies_email_format',
        'companies',
        "email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'"
    )
    
    # Validate phone format for companies
    op.create_check_constraint(
        'ck_companies_phone_format',
        'companies',
        "phone IS NULL OR length(phone) >= 10"
    )
    
    # Validate fax format for companies
    op.create_check_constraint(
        'ck_companies_fax_format',
        'companies',
        "fax IS NULL OR length(fax) >= 10"
    )
    
    # Validate zip code format for addresses
    op.create_check_constraint(
        'ck_addresses_zip_format',
        'addresses',
        "length(zip_code) >= 5"
    )
    
    # Validate that only one default address per company
    op.create_check_constraint(
        'ck_addresses_one_default_per_company',
        'addresses',
        "is_default = false OR (SELECT COUNT(*) FROM addresses a2 WHERE a2.company_id = addresses.company_id AND a2.is_default = true AND a2.id != addresses.id) = 0"
    )
    
    # Step 11: Create database triggers for data integrity and balance calculations
    # Trigger to ensure contact-company relationship consistency
    connection.execute(sa.text("""
        CREATE OR REPLACE FUNCTION validate_contact_company_consistency()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Ensure contact and company belong to same tenant
            IF NOT EXISTS (
                SELECT 1 FROM companies c 
                WHERE c.id = NEW.company_id 
                AND c.tenant_id = NEW.tenant_id
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
        FOR EACH ROW
        EXECUTE FUNCTION validate_contact_company_consistency();
    """))
    
    # Trigger to ensure order-contact-company relationship consistency
    connection.execute(sa.text("""
        CREATE OR REPLACE FUNCTION validate_order_relationships()
        RETURNS TRIGGER AS $$
        DECLARE
            contact_company_id INTEGER;
            contact_tenant_id INTEGER;
        BEGIN
            -- Get contact's company_id and tenant_id
            SELECT company_id, tenant_id INTO contact_company_id, contact_tenant_id
            FROM contacts
            WHERE id = NEW.contact_id;
            
            -- Ensure contact exists and belongs to same tenant
            IF contact_tenant_id IS NULL THEN
                RAISE EXCEPTION 'Contact does not exist';
            END IF;
            
            IF contact_tenant_id != NEW.tenant_id THEN
                RAISE EXCEPTION 'Order and contact must belong to the same tenant';
            END IF;
            
            -- Ensure order's company_id matches contact's company_id
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
        FOR EACH ROW
        EXECUTE FUNCTION validate_order_relationships();
    """))
    
    # Trigger to prevent deletion of company with existing contacts
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
        FOR EACH ROW
        EXECUTE FUNCTION prevent_company_deletion_with_contacts();
    """))
    
    # Trigger to automatically set default address when first address is created
    connection.execute(sa.text("""
        CREATE OR REPLACE FUNCTION auto_set_first_address_default()
        RETURNS TRIGGER AS $$
        BEGIN
            -- If this is the first address for the company, make it default
            IF NOT EXISTS (
                SELECT 1 FROM addresses 
                WHERE company_id = NEW.company_id 
                AND id != NEW.id
            ) THEN
                NEW.is_default := true;
            END IF;
            
            -- If setting as default, unset other defaults for this company
            IF NEW.is_default = true THEN
                UPDATE addresses 
                SET is_default = false 
                WHERE company_id = NEW.company_id 
                AND id != NEW.id 
                AND is_default = true;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """))
    
    connection.execute(sa.text("""
        CREATE TRIGGER trg_auto_set_first_address_default
        BEFORE INSERT OR UPDATE ON addresses
        FOR EACH ROW
        EXECUTE FUNCTION auto_set_first_address_default();
    """))
    
    # Trigger to prevent deletion of last address if it's set as company default
    connection.execute(sa.text("""
        CREATE OR REPLACE FUNCTION prevent_default_address_deletion()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.is_default = true THEN
                -- Check if company references this address
                IF EXISTS (
                    SELECT 1 FROM companies 
                    WHERE default_address_id = OLD.id
                ) THEN
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
        FOR EACH ROW
        EXECUTE FUNCTION prevent_default_address_deletion();
    """))
    
    connection.commit()


def downgrade() -> None:
    """
    Downgrade database schema back to customer-company structure.
    
    WARNING: This downgrade may result in data loss if:
    - Multiple contacts exist with the same email across different companies
    - Addresses have been created for companies
    """
    
    # Drop triggers and functions
    connection = op.get_bind()
    
    connection.execute(sa.text("DROP TRIGGER IF EXISTS trg_prevent_default_address_deletion ON addresses"))
    connection.execute(sa.text("DROP FUNCTION IF EXISTS prevent_default_address_deletion()"))
    
    connection.execute(sa.text("DROP TRIGGER IF EXISTS trg_auto_set_first_address_default ON addresses"))
    connection.execute(sa.text("DROP FUNCTION IF EXISTS auto_set_first_address_default()"))
    
    connection.execute(sa.text("DROP TRIGGER IF EXISTS trg_prevent_company_deletion ON companies"))
    connection.execute(sa.text("DROP FUNCTION IF EXISTS prevent_company_deletion_with_contacts()"))
    
    connection.execute(sa.text("DROP TRIGGER IF EXISTS trg_validate_order_relationships ON orders"))
    connection.execute(sa.text("DROP FUNCTION IF EXISTS validate_order_relationships()"))
    
    connection.execute(sa.text("DROP TRIGGER IF EXISTS trg_validate_contact_company ON contacts"))
    connection.execute(sa.text("DROP FUNCTION IF EXISTS validate_contact_company_consistency()"))
    
    connection.commit()
    
    # Drop check constraints
    op.drop_constraint('ck_addresses_one_default_per_company', 'addresses', type_='check')
    op.drop_constraint('ck_addresses_zip_format', 'addresses', type_='check')
    op.drop_constraint('ck_companies_fax_format', 'companies', type_='check')
    op.drop_constraint('ck_companies_phone_format', 'companies', type_='check')
    op.drop_constraint('ck_companies_email_format', 'companies', type_='check')
    op.drop_constraint('ck_contacts_phone_format', 'contacts', type_='check')
    op.drop_constraint('ck_contacts_email_format', 'contacts', type_='check')
    
    # Drop composite indexes
    op.drop_index('ix_orders_tenant_contact', table_name='orders')
    op.drop_index('ix_orders_tenant_company', table_name='orders')
    op.drop_index('ix_contacts_tenant_company', table_name='contacts')
    
    # Revert orders table changes
    op.drop_index(op.f('ix_orders_contact_id'), table_name='orders')
    op.create_index('ix_orders_customer_id', 'orders', ['customer_id'], unique=False)
    
    op.drop_constraint('fk_orders_contact', 'orders', type_='foreignkey')
    op.create_foreign_key(
        'orders_customer_id_fkey',
        'orders', 'contacts',
        ['customer_id'], ['id']
    )
    
    op.alter_column('orders', 'contact_id',
                    new_column_name='customer_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    op.drop_index(op.f('ix_orders_company_id'), table_name='orders')
    op.drop_constraint('fk_orders_company', 'orders', type_='foreignkey')
    op.drop_column('orders', 'company_id')
    
    # Revert contacts table changes
    op.alter_column('contacts', 'company_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    op.drop_constraint('uq_contact_email_per_company', 'contacts', type_='unique')
    op.create_unique_constraint(
        'uq_customer_email_per_tenant',
        'contacts',
        ['tenant_id', 'email']
    )
    
    # Rename contacts back to customers
    op.drop_index(op.f('ix_contacts_company_id'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_email'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_tenant_id'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_id'), table_name='contacts')
    
    op.rename_table('contacts', 'customers')
    
    op.create_index('ix_customers_company_id', 'customers', ['company_id'], unique=False)
    op.create_index('ix_customers_email', 'customers', ['email'], unique=False)
    op.create_index('ix_customers_tenant_id', 'customers', ['tenant_id'], unique=False)
    op.create_index('ix_customers_id', 'customers', ['id'], unique=False)
    
    # Remove companies table additions
    op.drop_constraint('fk_companies_default_address', 'companies', type_='foreignkey')
    op.drop_column('companies', 'default_address_id')
    op.drop_column('companies', 'fax')
    
    # Drop addresses table
    op.drop_index('ix_addresses_company_default', table_name='addresses')
    op.drop_index(op.f('ix_addresses_company_id'), table_name='addresses')
    op.drop_index(op.f('ix_addresses_tenant_id'), table_name='addresses')
    op.drop_index(op.f('ix_addresses_id'), table_name='addresses')
    op.drop_table('addresses')
