"""Add api_deployments table and status column to apis.

Revision ID: 0006_add_api_deployments
Revises: 0005_fix_user_boolean_defaults
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '0006_add_api_deployments'
down_revision = '0005_fix_user_boolean_defaults'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add status column to apis (default 'draft' for all existing rows)
    with op.batch_alter_table('apis', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('status', sa.String(), nullable=False,
                      server_default='draft')
        )
        batch_op.create_index('ix_apis_status', ['status'])

    # 2. Create api_deployments table
    op.create_table(
        'api_deployments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('api_id', sa.Integer(),
                  sa.ForeignKey('apis.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('environment_id', sa.Integer(),
                  sa.ForeignKey('environments.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('status', sa.String(), nullable=False,
                  server_default='deployed', index=True),
        sa.Column('target_url_override', sa.String(), nullable=True),
        sa.Column('deployed_by', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('deployed_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.UniqueConstraint('api_id', 'environment_id',
                            name='uq_api_deployment_api_env'),
    )


def downgrade() -> None:
    op.drop_table('api_deployments')
    with op.batch_alter_table('apis', schema=None) as batch_op:
        batch_op.drop_index('ix_apis_status')
        batch_op.drop_column('status')
