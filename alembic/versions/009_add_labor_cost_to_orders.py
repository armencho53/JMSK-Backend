"""Add labor_cost column to orders table

Revision ID: 009_add_labor_cost_orders
Revises: 008_company_metal_balances
Create Date: 2026-02-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_add_labor_cost_orders'
down_revision = '008_company_metal_balances'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('labor_cost', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('orders', 'labor_cost')
