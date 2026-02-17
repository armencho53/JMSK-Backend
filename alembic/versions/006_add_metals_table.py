"""Add metals table

Revision ID: 006_add_metals_table
Revises: 005_lookup_values_enum_to_string
Create Date: 2026-02-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_add_metals_table'
down_revision = '005_lookup_values_enum_to_string'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'metals' not in inspector.get_table_names():
        op.create_table(
            'metals',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
            sa.Column('code', sa.String(50), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('fine_percentage', sa.Float(), nullable=False),
            sa.Column('average_cost_per_gram', sa.Float(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('tenant_id', 'code', name='uq_metal_code_per_tenant'),
        )


def downgrade():
    op.drop_table('metals')
