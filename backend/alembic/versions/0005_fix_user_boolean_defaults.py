"""fix user boolean defaults

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-07 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    # Update any existing NULL values to proper defaults
    op.execute("""
        UPDATE users 
        SET is_active = TRUE 
        WHERE is_active IS NULL
    """)

    op.execute("""
        UPDATE users 
        SET is_superuser = FALSE 
        WHERE is_superuser IS NULL
    """)

    # Alter columns to be NOT NULL with defaults (SQLite compatible)
    # Note: SQLite doesn't support ALTER COLUMN directly, so we check dialect
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        op.alter_column('users', 'is_active',
                        existing_type=sa.Boolean(),
                        nullable=False,
                        server_default=sa.text('TRUE'))
        op.alter_column('users', 'is_superuser',
                        existing_type=sa.Boolean(),
                        nullable=False,
                        server_default=sa.text('FALSE'))
    # For SQLite, the defaults are already set in the model


def downgrade():
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        op.alter_column('users', 'is_active',
                        existing_type=sa.Boolean(),
                        nullable=True,
                        server_default=None)
        op.alter_column('users', 'is_superuser',
                        existing_type=sa.Boolean(),
                        nullable=True,
                        server_default=None)
