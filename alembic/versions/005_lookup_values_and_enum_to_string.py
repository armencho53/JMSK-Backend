"""Create lookup_values table and convert configurable enum columns to String

Revision ID: 005_lookup_values_enum_to_string
Revises: 004_remove_customer_fields
Create Date: 2025-07-14 00:00:00.000000

This migration:
1. Creates the lookup_values table with all columns and unique constraint
2. Converts orders.metal_type from Enum(MetalType) to String(50)
3. Converts manufacturing_steps.step_type from Enum(StepType) to String(50)
4. Converts supplies.type from Enum(SupplyType) to String(50)
5. Converts department_balances.metal_type from Enum(MetalType) to String(50)
6. Drops the old PostgreSQL enum types (metaltype, steptype, supplytype)

Status columns (orders.status, manufacturing_steps.status, shipments.status)
are intentionally left as SQLAlchemy Enum type.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 10.7
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_lookup_values_enum_to_string'
down_revision = '004_remove_customer_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create lookup_values table (if not already present)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'lookup_values' not in existing_tables:
        op.create_table(
            'lookup_values',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('category', sa.String(), nullable=False),
            sa.Column('code', sa.String(), nullable=False),
            sa.Column('display_label', sa.String(), nullable=False),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('tenant_id', 'category', 'code', name='uq_tenant_category_code'),
        )
        op.create_index(op.f('ix_lookup_values_id'), 'lookup_values', ['id'], unique=False)
        op.create_index(op.f('ix_lookup_values_tenant_id'), 'lookup_values', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_lookup_values_category'), 'lookup_values', ['category'], unique=False)

    # 2. Convert enum columns to String(50)
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        # Only alter columns that are still enum types (skip if already varchar)
        def col_is_enum(table, column):
            cols = {c['name']: c for c in inspector.get_columns(table)}
            if column not in cols:
                return False
            return not isinstance(cols[column]['type'], sa.String)

        if col_is_enum('orders', 'metal_type'):
            op.execute(
                "ALTER TABLE orders ALTER COLUMN metal_type TYPE VARCHAR(50) "
                "USING metal_type::text"
            )
        if col_is_enum('manufacturing_steps', 'step_type'):
            op.execute(
                "ALTER TABLE manufacturing_steps ALTER COLUMN step_type TYPE VARCHAR(50) "
                "USING step_type::text"
            )
        if col_is_enum('supplies', 'type'):
            op.execute(
                "ALTER TABLE supplies ALTER COLUMN type TYPE VARCHAR(50) "
                "USING type::text"
            )
        if col_is_enum('department_balances', 'metal_type'):
            op.execute(
                "ALTER TABLE department_balances ALTER COLUMN metal_type TYPE VARCHAR(50) "
                "USING metal_type::text"
            )

        # 3. Drop old PostgreSQL enum types now that no columns reference them
        op.execute("DROP TYPE IF EXISTS metaltype")
        op.execute("DROP TYPE IF EXISTS steptype")
        op.execute("DROP TYPE IF EXISTS supplytype")
    else:
        pass


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'postgresql':
        # 1. Recreate the PostgreSQL enum types
        op.execute(
            "CREATE TYPE metaltype AS ENUM "
            "('GOLD_24K', 'GOLD_22K', 'GOLD_18K', 'GOLD_14K', 'SILVER_925', 'PLATINUM', 'OTHER')"
        )
        op.execute(
            "CREATE TYPE steptype AS ENUM "
            "('DESIGN', 'CASTING', 'STONE_SETTING', 'POLISHING', 'ENGRAVING', "
            "'QUALITY_CHECK', 'FINISHING', 'OTHER')"
        )
        op.execute(
            "CREATE TYPE supplytype AS ENUM "
            "('METAL', 'GEMSTONE', 'TOOL', 'PACKAGING', 'OTHER')"
        )

        # 2. Convert String columns back to Enum types
        op.execute(
            "ALTER TABLE orders ALTER COLUMN metal_type TYPE metaltype "
            "USING metal_type::metaltype"
        )
        op.execute(
            "ALTER TABLE manufacturing_steps ALTER COLUMN step_type TYPE steptype "
            "USING step_type::steptype"
        )
        op.execute(
            "ALTER TABLE supplies ALTER COLUMN type TYPE supplytype "
            "USING type::supplytype"
        )
        op.execute(
            "ALTER TABLE department_balances ALTER COLUMN metal_type TYPE metaltype "
            "USING metal_type::metaltype"
        )

    # 3. Drop lookup_values table
    op.drop_index(op.f('ix_lookup_values_category'), table_name='lookup_values')
    op.drop_index(op.f('ix_lookup_values_tenant_id'), table_name='lookup_values')
    op.drop_index(op.f('ix_lookup_values_id'), table_name='lookup_values')
    op.drop_table('lookup_values')
