"""Add order_line_items table for multi-line order support

This migration creates the order_line_items table to support multiple products
per order, each with its own metal type, quantity, weight, and pricing.

Revision ID: 003_add_order_line_items
Revises: 002_fixup_prod_schema
Create Date: 2024-01-15

"""
from alembic import op
import sqlalchemy as sa


revision = '003_add_order_line_items'
down_revision = '002_fixup_prod'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create order_line_items table with foreign key constraints and indexes."""
    
    # Create order_line_items table
    op.create_table(
        'order_line_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_description', sa.Text(), nullable=False),
        sa.Column('specifications', sa.Text(), nullable=True),
        sa.Column('metal_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('target_weight_per_piece', sa.Float(), nullable=True),
        sa.Column('initial_total_weight', sa.Float(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('labor_cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ['tenant_id'], 
            ['tenants.id'], 
            name='fk_order_line_items_tenant'
        ),
        sa.ForeignKeyConstraint(
            ['order_id'], 
            ['orders.id'], 
            name='fk_order_line_items_order',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['metal_id'], 
            ['metals.id'], 
            name='fk_order_line_items_metal'
        ),
    )
    
    # Create indexes for performance
    op.create_index(
        'idx_order_line_items_tenant', 
        'order_line_items', 
        ['tenant_id']
    )
    op.create_index(
        'idx_order_line_items_order', 
        'order_line_items', 
        ['order_id']
    )
    op.create_index(
        'idx_order_line_items_metal', 
        'order_line_items', 
        ['metal_id']
    )


def downgrade() -> None:
    """Drop order_line_items table and its indexes."""
    
    # Drop indexes first
    op.drop_index('idx_order_line_items_metal', table_name='order_line_items')
    op.drop_index('idx_order_line_items_order', table_name='order_line_items')
    op.drop_index('idx_order_line_items_tenant', table_name='order_line_items')
    
    # Drop table
    op.drop_table('order_line_items')
