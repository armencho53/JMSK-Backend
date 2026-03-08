"""Add username column to users table, make email nullable

Revision ID: 006_add_username
Revises: 005_add_metal_type
Create Date: 2026-03-07

"""
from alembic import op
import sqlalchemy as sa


revision = '006_add_username'
down_revision = '005_add_metal_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add username column (nullable initially for backfill)
    op.add_column('users', sa.Column('username', sa.String(50), nullable=True))

    # Backfill username from email (take part before @)
    op.execute("UPDATE users SET username = LOWER(SPLIT_PART(email, '@', 1)) WHERE username IS NULL")

    # Handle duplicates by appending user id
    op.execute("""
        UPDATE users SET username = username || '_' || CAST(id AS VARCHAR)
        WHERE id NOT IN (
            SELECT MIN(id) FROM users GROUP BY username
        )
    """)

    # Make username NOT NULL and add unique index
    op.alter_column('users', 'username', nullable=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # Make email nullable (no longer required for login)
    op.alter_column('users', 'email', nullable=True)


def downgrade() -> None:
    # Make email NOT NULL again
    op.execute("UPDATE users SET email = username || '@migrated.local' WHERE email IS NULL")
    op.alter_column('users', 'email', nullable=False)

    # Drop username
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'username')
