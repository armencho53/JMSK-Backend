"""Create department_ledger_entries table

Revision ID: 011_create_dept_ledger_entries
Revises: 010_rename_mfg_steps_archive
Create Date: 2026-02-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011_create_dept_ledger_entries'
down_revision = '010_rename_mfg_steps_archive'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'department_ledger_entries',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id'), nullable=False, index=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=False, index=True),
        sa.Column('metal_type', sa.String(50), nullable=False),
        sa.Column('direction', sa.String(3), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('fine_weight', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('department_ledger_entries')
