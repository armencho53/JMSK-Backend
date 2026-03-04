"""Add metal_prices table for precious metal price caching

This migration creates the metal_prices table to cache precious metal prices
from external APIs, reducing API calls and improving performance.

Revision ID: 004_add_metal_prices
Revises: 003_add_order_line_items
Create Date: 2024-01-15

"""
from alembic import op
import sqlalchemy as sa


revision = '004_add_metal_prices'
down_revision = '003_add_order_line_items'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create metal_prices table with unique constraint and indexes."""
    
    # Create metal_prices table
    op.create_table(
        'metal_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metal_category', sa.String(length=20), nullable=False),
        sa.Column('price_per_gram', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD'),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Unique constraint on metal_category
        sa.UniqueConstraint('metal_category', name='uq_metal_category'),
    )
    
    # Create indexes for performance
    op.create_index(
        'idx_metal_prices_category', 
        'metal_prices', 
        ['metal_category']
    )
    op.create_index(
        'idx_metal_prices_expires', 
        'metal_prices', 
        ['expires_at']
    )


def downgrade() -> None:
    """Drop metal_prices table and its indexes."""
    
    # Drop indexes first
    op.drop_index('idx_metal_prices_expires', table_name='metal_prices')
    op.drop_index('idx_metal_prices_category', table_name='metal_prices')
    
    # Drop table
    op.drop_table('metal_prices')
