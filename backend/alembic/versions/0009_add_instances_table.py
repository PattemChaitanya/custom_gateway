"""Add instances table for per-account gateway runtime tracking.

Revision ID: 0009_add_instances_table
Revises: 0008_add_account_tenancy
Create Date: 2026-04-03

Changes
-------
1. Create ``instances`` table — tracks one Docker container per account:
   id, account_id (unique FK → accounts), container_id, port, status,
   gateway_url, created_at, expires_at (created_at + 48h)
"""
from alembic import op
import sqlalchemy as sa

revision = '0009_add_instances_table'
down_revision = '0008_add_account_tenancy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'instances',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            'account_id', sa.Integer(),
            sa.ForeignKey('accounts.id', ondelete='CASCADE'),
            nullable=False, unique=True,
        ),
        sa.Column('container_id', sa.String(), nullable=True),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='provisioning'),
        sa.Column('gateway_url', sa.String(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_instances_account_id', 'instances', ['account_id'])
    op.create_index('ix_instances_status', 'instances', ['status'])
    op.create_index('ix_instances_expires_at', 'instances', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_instances_expires_at', table_name='instances')
    op.drop_index('ix_instances_status', table_name='instances')
    op.drop_index('ix_instances_account_id', table_name='instances')
    op.drop_table('instances')
