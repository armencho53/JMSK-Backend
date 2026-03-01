"""Rename manufacturing_steps to manufacturing_steps_archive

Revision ID: 010_rename_mfg_steps_archive
Revises: 009_add_labor_cost_orders
Create Date: 2026-02-17

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '010_rename_mfg_steps_archive'
down_revision = '009_add_labor_cost_orders'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('manufacturing_steps', 'manufacturing_steps_archive')

    # Rename indexes to reflect the new table name
    op.execute('ALTER INDEX ix_manufacturing_steps_id RENAME TO ix_manufacturing_steps_archive_id')
    op.execute('ALTER INDEX ix_manufacturing_steps_tenant_id RENAME TO ix_manufacturing_steps_archive_tenant_id')
    op.execute('ALTER INDEX ix_manufacturing_steps_order_id RENAME TO ix_manufacturing_steps_archive_order_id')
    op.execute('ALTER INDEX ix_manufacturing_steps_parent_step_id RENAME TO ix_manufacturing_steps_archive_parent_step_id')


def downgrade():
    # Restore original index names
    op.execute('ALTER INDEX ix_manufacturing_steps_archive_parent_step_id RENAME TO ix_manufacturing_steps_parent_step_id')
    op.execute('ALTER INDEX ix_manufacturing_steps_archive_order_id RENAME TO ix_manufacturing_steps_order_id')
    op.execute('ALTER INDEX ix_manufacturing_steps_archive_tenant_id RENAME TO ix_manufacturing_steps_tenant_id')
    op.execute('ALTER INDEX ix_manufacturing_steps_archive_id RENAME TO ix_manufacturing_steps_id')

    op.rename_table('manufacturing_steps_archive', 'manufacturing_steps')
