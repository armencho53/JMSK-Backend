"""Add company_metal_balances table

Revision ID: 008_company_metal_balances
Revises: 007_safe_supply_transactions
Create Date: 2026-02-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_company_metal_balances'
down_revision = '007_safe_supply_transactions'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'company_metal_balances',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
        sa.Column('metal_id', sa.Integer(), sa.ForeignKey('metals.id'), nullable=False, index=True),
        sa.Column('balance_grams', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('tenant_id', 'company_id', 'metal_id', name='uq_company_metal_balance'),
    )


def downgrade():
    op.drop_table('company_metal_balances')
