"""add roles column to users

Revision ID: 0002_add_roles_column
Revises: 0001_create_users
Create Date: 2026-01-26
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_roles_column'
down_revision = '0001_create_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add nullable roles column with default empty string for backward compatibility
    op.add_column('users', sa.Column('roles', sa.String(), nullable=True, server_default=''))


def downgrade() -> None:
    op.drop_column('users', 'roles')
