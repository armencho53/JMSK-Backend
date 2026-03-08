"""Add metal_type column to metals table

Revision ID: 005_add_metal_type
Revises: 004_add_metal_prices
Create Date: 2026-03-07

"""
from alembic import op
import sqlalchemy as sa


revision = '005_add_metal_type'
down_revision = '004_add_metal_prices'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the enum type
    metal_type_enum = sa.Enum('GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'OTHER', name='metaltype')
    metal_type_enum.create(op.get_bind(), checkfirst=True)

    # Add column with default OTHER
    op.add_column('metals', sa.Column('metal_type', sa.Enum('GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'OTHER', name='metaltype'), nullable=False, server_default='OTHER'))

    # Backfill existing rows based on code prefix
    op.execute("UPDATE metals SET metal_type = 'GOLD' WHERE UPPER(code) LIKE 'GOLD%'")
    op.execute("UPDATE metals SET metal_type = 'SILVER' WHERE UPPER(code) LIKE 'SILVER%'")
    op.execute("UPDATE metals SET metal_type = 'PLATINUM' WHERE UPPER(code) LIKE 'PLAT%'")
    op.execute("UPDATE metals SET metal_type = 'PALLADIUM' WHERE UPPER(code) LIKE 'PALLAD%'")


def downgrade() -> None:
    op.drop_column('metals', 'metal_type')
    sa.Enum(name='metaltype').drop(op.get_bind(), checkfirst=True)
