"""Add algorithm column to rate_limits table.

Revision ID: 0007_add_rate_limit_algorithm
Revises: 0006_add_api_deployments
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '0007_add_rate_limit_algorithm'
down_revision = '0006_add_api_deployments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('rate_limits', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'algorithm',
                sa.String(),
                nullable=False,
                server_default='fixed_window',
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('rate_limits', schema=None) as batch_op:
        batch_op.drop_column('algorithm')
