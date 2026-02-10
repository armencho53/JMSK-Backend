"""remove customer fields from orders

Revision ID: 004_remove_customer_fields
Revises: 003_hierarchical_contact_system
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_remove_customer_fields'
down_revision = '003_hierarchical_contact_system'
branch_labels = None
depends_on = None

def upgrade():
    # Remove customer fields from orders table
    # These are now replaced by contact_id and company_id relationships
    op.drop_column('orders', 'customer_name')
    op.drop_column('orders', 'customer_email')
    op.drop_column('orders', 'customer_phone')

def downgrade():
    # Add back customer fields if needed to rollback
    op.add_column('orders', sa.Column('customer_name', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('customer_email', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('customer_phone', sa.String(), nullable=True))
