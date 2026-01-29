"""create api-related tables

Revision ID: 0003_create_api_models
Revises: 0002_add_roles_column
Create Date: 2026-01-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_create_api_models'
down_revision = '0002_add_roles_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # For developer/test environments where the DB may already contain these
    # tables (from a previous failed migration run), drop them first so the
    # migration can be applied idempotently.
    conn = op.get_bind()
    conn.execute(sa.text('DROP TABLE IF EXISTS module_metadata'))
    conn.execute(sa.text('DROP TABLE IF EXISTS api_keys'))
    conn.execute(sa.text('DROP TABLE IF EXISTS environments'))
    conn.execute(sa.text('DROP TABLE IF EXISTS connectors'))
    conn.execute(sa.text('DROP TABLE IF EXISTS rate_limits'))
    conn.execute(sa.text('DROP TABLE IF EXISTS auth_policies'))
    conn.execute(sa.text('DROP TABLE IF EXISTS schemas'))
    conn.execute(sa.text('DROP TABLE IF EXISTS apis'))

    op.create_table(
        'apis',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('resource', sa.JSON(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('name', 'version', name='uq_api_name_version'),
    )
    op.create_index('ix_apis_name', 'apis', ['name'])
    op.create_index('ix_apis_version', 'apis', ['version'])

    op.create_table(
        'schemas',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('api_id', sa.Integer(), sa.ForeignKey('apis.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('definition', sa.JSON(), nullable=True),
        sa.Column('raw', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'auth_policies',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('api_id', sa.Integer(), sa.ForeignKey('apis.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'rate_limits',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('api_id', sa.Integer(), sa.ForeignKey('apis.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_type', sa.String(), nullable=False, server_default='global'),
        sa.Column('limit', sa.Integer(), nullable=False),
        sa.Column('window_seconds', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'connectors',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('api_id', sa.Integer(), sa.ForeignKey('apis.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'environments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('key', sa.String(), nullable=False, unique=True),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('scopes', sa.String(), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('environment_id', sa.Integer(), sa.ForeignKey('environments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'module_metadata',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('module_metadata')
    op.drop_table('api_keys')
    op.drop_table('environments')
    op.drop_table('connectors')
    op.drop_table('rate_limits')
    op.drop_table('auth_policies')
    op.drop_table('schemas')
    op.drop_index('ix_apis_name', table_name='apis')
    op.drop_index('ix_apis_version', table_name='apis')
    op.drop_table('apis')
