"""Add gateway_routes table for per-account route definitions.

Revision ID: 0010_add_gateway_routes
Revises: 0009_add_instances_table
Create Date: 2026-04-03

Changes
-------
1. Create ``gateway_routes`` table:
   id, account_id (FK → accounts CASCADE), path, method, target_url,
   auth_required, validation_schema (JSONB), active, created_at, updated_at
2. Indexes on account_id, active, (account_id, active) composite
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0010_add_gateway_routes'
down_revision = '0009_add_instances_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'gateway_routes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            'account_id', sa.Integer(),
            sa.ForeignKey('accounts.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('method', sa.String(10), nullable=False, server_default='ANY'),
        sa.Column('target_url', sa.String(), nullable=False),
        sa.Column('auth_required', sa.Boolean(), nullable=False, server_default='false'),
        # JSONB on PostgreSQL, JSON fallback on SQLite
        sa.Column('validation_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "method IN ('GET','POST','PUT','PATCH','DELETE','ANY')",
            name='ck_gateway_routes_method',
        ),
    )
    op.create_index('ix_gateway_routes_account_id', 'gateway_routes', ['account_id'])
    op.create_index('ix_gateway_routes_active', 'gateway_routes', ['active'])
    op.create_index(
        'ix_gateway_routes_account_active',
        'gateway_routes', ['account_id', 'active'],
    )


def downgrade() -> None:
    op.drop_index('ix_gateway_routes_account_active', table_name='gateway_routes')
    op.drop_index('ix_gateway_routes_active', table_name='gateway_routes')
    op.drop_index('ix_gateway_routes_account_id', table_name='gateway_routes')
    op.drop_table('gateway_routes')
