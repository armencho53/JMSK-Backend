"""Add safe_supplies and metal_transactions tables

Revision ID: 007_safe_supplies_and_transactions
Revises: 006_add_metals_table
Create Date: 2026-02-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_safe_supply_transactions'
down_revision = '006_add_metals_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'safe_supplies',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('metal_id', sa.Integer(), sa.ForeignKey('metals.id'), nullable=True),
        sa.Column('supply_type', sa.String(20), nullable=False),
        sa.Column('quantity_grams', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('tenant_id', 'metal_id', 'supply_type', name='uq_safe_supply'),
    )

    op.create_table(
        'metal_transactions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('transaction_type', sa.String(30), nullable=False),
        sa.Column('metal_id', sa.Integer(), sa.ForeignKey('metals.id'), nullable=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('quantity_grams', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
    )


def downgrade():
    op.drop_table('metal_transactions')
    op.drop_table('safe_supplies')
