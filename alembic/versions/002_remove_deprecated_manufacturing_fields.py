"""remove_deprecated_manufacturing_fields

Revision ID: 002_remove_deprecated
Revises: fa63140935ab
Create Date: 2026-01-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_remove_deprecated'
down_revision = 'fa63140935ab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop deprecated columns from manufacturing_steps table
    # These columns are no longer used in the application
    
    # Drop legacy "goods" tracking columns
    op.drop_column('manufacturing_steps', 'goods_given_quantity')
    op.drop_column('manufacturing_steps', 'goods_given_weight')
    op.drop_column('manufacturing_steps', 'goods_given_at')
    op.drop_column('manufacturing_steps', 'goods_returned_quantity')
    op.drop_column('manufacturing_steps', 'goods_returned_weight')
    op.drop_column('manufacturing_steps', 'goods_returned_at')
    
    # Drop deprecated quantity tracking columns
    op.drop_column('manufacturing_steps', 'quantity_completed')
    op.drop_column('manufacturing_steps', 'quantity_failed')
    op.drop_column('manufacturing_steps', 'quantity_rework')
    
    # Drop deprecated fields
    op.drop_column('manufacturing_steps', 'step_name')
    op.drop_column('manufacturing_steps', 'assigned_to')


def downgrade() -> None:
    # Re-add columns if needed to rollback
    op.add_column('manufacturing_steps', sa.Column('assigned_to', sa.String(), nullable=True))
    op.add_column('manufacturing_steps', sa.Column('step_name', sa.String(), nullable=True))
    
    op.add_column('manufacturing_steps', sa.Column('quantity_rework', sa.Float(), nullable=True))
    op.add_column('manufacturing_steps', sa.Column('quantity_failed', sa.Float(), nullable=True))
    op.add_column('manufacturing_steps', sa.Column('quantity_completed', sa.Float(), nullable=True))
    
    op.add_column('manufacturing_steps', sa.Column('goods_returned_at', sa.DateTime(), nullable=True))
    op.add_column('manufacturing_steps', sa.Column('goods_returned_weight', sa.Float(), nullable=True))
    op.add_column('manufacturing_steps', sa.Column('goods_returned_quantity', sa.Float(), nullable=True))
    op.add_column('manufacturing_steps', sa.Column('goods_given_at', sa.DateTime(), nullable=True))
    op.add_column('manufacturing_steps', sa.Column('goods_given_weight', sa.Float(), nullable=True))
    op.add_column('manufacturing_steps', sa.Column('goods_given_quantity', sa.Float(), nullable=True))
