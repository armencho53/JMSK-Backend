"""Add metal_id foreign keys to orders, department_ledger_entries, department_balances

Revision ID: 009_metal_id_foreign_keys
Revises: 011_create_dept_ledger_entries
Create Date: 2026-02-18

This migration:
1. Adds nullable metal_id FK column to orders, department_ledger_entries, department_balances
2. Backfills metal_id by matching metal_type against metals.code within the same tenant_id
3. Logs warnings and deletes unmatched rows in department_ledger_entries and department_balances
4. Sets metal_id to NOT NULL on department_ledger_entries and department_balances
5. Drops metal_type column from all three tables
6. Replaces uq_department_metal_type with uq_department_metal_id on department_balances

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
"""
import logging
from alembic import op
import sqlalchemy as sa

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision = '009_metal_id_foreign_keys'
down_revision = '011_create_dept_ledger_entries'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    # 1. Add nullable metal_id columns with FK to metals.id
    op.add_column('orders', sa.Column('metal_id', sa.Integer(), sa.ForeignKey('metals.id'), nullable=True))
    op.add_column('department_ledger_entries', sa.Column('metal_id', sa.Integer(), sa.ForeignKey('metals.id'), nullable=True))
    op.add_column('department_balances', sa.Column('metal_id', sa.Integer(), sa.ForeignKey('metals.id'), nullable=True))

    # 2. Backfill metal_id by matching metal_type against metals.code within the same tenant_id
    conn.execute(sa.text(
        "UPDATE orders SET metal_id = ("
        "  SELECT m.id FROM metals m"
        "  WHERE m.code = orders.metal_type AND m.tenant_id = orders.tenant_id"
        "  LIMIT 1"
        ") WHERE metal_type IS NOT NULL"
    ))

    conn.execute(sa.text(
        "UPDATE department_ledger_entries SET metal_id = ("
        "  SELECT m.id FROM metals m"
        "  WHERE m.code = department_ledger_entries.metal_type"
        "  AND m.tenant_id = department_ledger_entries.tenant_id"
        "  LIMIT 1"
        ")"
    ))

    conn.execute(sa.text(
        "UPDATE department_balances SET metal_id = ("
        "  SELECT m.id FROM metals m"
        "  WHERE m.code = department_balances.metal_type"
        "  AND m.tenant_id = department_balances.tenant_id"
        "  LIMIT 1"
        ")"
    ))

    # 3. Log warnings for unmatched rows in department_ledger_entries and department_balances
    unmatched_ledger = conn.execute(sa.text(
        "SELECT id, tenant_id, metal_type FROM department_ledger_entries WHERE metal_id IS NULL"
    )).fetchall()
    for row in unmatched_ledger:
        logger.warning(
            "department_ledger_entries id=%s (tenant_id=%s) has unmatched metal_type='%s' — will be deleted",
            row[0], row[1], row[2]
        )

    unmatched_balances = conn.execute(sa.text(
        "SELECT id, tenant_id, metal_type FROM department_balances WHERE metal_id IS NULL"
    )).fetchall()
    for row in unmatched_balances:
        logger.warning(
            "department_balances id=%s (tenant_id=%s) has unmatched metal_type='%s' — will be deleted",
            row[0], row[1], row[2]
        )

    # Delete unmatched rows before applying NOT NULL
    conn.execute(sa.text(
        "DELETE FROM department_ledger_entries WHERE metal_id IS NULL"
    ))
    conn.execute(sa.text(
        "DELETE FROM department_balances WHERE metal_id IS NULL"
    ))

    # 4. Set metal_id to NOT NULL on department_ledger_entries and department_balances
    with op.batch_alter_table('department_ledger_entries') as batch_op:
        batch_op.alter_column('metal_id', nullable=False)

    with op.batch_alter_table('department_balances') as batch_op:
        batch_op.alter_column('metal_id', nullable=False)

    # 5. Drop uq_department_metal_type constraint
    if dialect == 'sqlite':
        # SQLite doesn't support DROP CONSTRAINT directly; batch mode handles it
        with op.batch_alter_table('department_balances') as batch_op:
            batch_op.drop_constraint('uq_department_metal_type', type_='unique')
    else:
        op.drop_constraint('uq_department_metal_type', 'department_balances', type_='unique')

    # 6. Drop metal_type column from all three tables
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_column('metal_type')

    with op.batch_alter_table('department_ledger_entries') as batch_op:
        batch_op.drop_column('metal_type')

    with op.batch_alter_table('department_balances') as batch_op:
        batch_op.drop_column('metal_type')

    # 7. Create new unique constraint on (department_id, metal_id) for department_balances
    op.create_unique_constraint('uq_department_metal_id', 'department_balances', ['department_id', 'metal_id'])


def downgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name

    # 1. Drop uq_department_metal_id constraint
    if dialect == 'sqlite':
        with op.batch_alter_table('department_balances') as batch_op:
            batch_op.drop_constraint('uq_department_metal_id', type_='unique')
    else:
        op.drop_constraint('uq_department_metal_id', 'department_balances', type_='unique')

    # 2. Add metal_type columns back
    op.add_column('orders', sa.Column('metal_type', sa.String(50), nullable=True))
    op.add_column('department_ledger_entries', sa.Column('metal_type', sa.String(50), nullable=True))
    op.add_column('department_balances', sa.Column('metal_type', sa.String(50), nullable=True))

    # 3. Backfill metal_type from metals.code
    conn.execute(sa.text(
        "UPDATE orders SET metal_type = ("
        "  SELECT m.code FROM metals m WHERE m.id = orders.metal_id LIMIT 1"
        ") WHERE metal_id IS NOT NULL"
    ))

    conn.execute(sa.text(
        "UPDATE department_ledger_entries SET metal_type = ("
        "  SELECT m.code FROM metals m WHERE m.id = department_ledger_entries.metal_id LIMIT 1"
        ")"
    ))

    conn.execute(sa.text(
        "UPDATE department_balances SET metal_type = ("
        "  SELECT m.code FROM metals m WHERE m.id = department_balances.metal_id LIMIT 1"
        ")"
    ))

    # 4. Set metal_type to NOT NULL on department_ledger_entries and department_balances
    with op.batch_alter_table('department_ledger_entries') as batch_op:
        batch_op.alter_column('metal_type', nullable=False)

    with op.batch_alter_table('department_balances') as batch_op:
        batch_op.alter_column('metal_type', nullable=False)

    # 5. Drop metal_id columns
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_column('metal_id')

    with op.batch_alter_table('department_ledger_entries') as batch_op:
        batch_op.drop_column('metal_id')

    with op.batch_alter_table('department_balances') as batch_op:
        batch_op.drop_column('metal_id')

    # 6. Restore original unique constraint on (department_id, metal_type)
    op.create_unique_constraint('uq_department_metal_type', 'department_balances', ['department_id', 'metal_type'])
