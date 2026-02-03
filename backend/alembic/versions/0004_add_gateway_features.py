"""Add all new gateway management tables.

Revision ID: 0004_add_gateway_features
Revises: 0003_create_api_models
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = '0004_add_gateway_features'
down_revision = '0003_create_api_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new tables for secrets, audit logs, metrics, permissions, roles, etc."""
    
    # 1. Update API Keys table
    with op.batch_alter_table('api_keys', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('usage_count', sa.Integer(), default=0))
        batch_op.add_column(sa.Column('metadata', JSON, nullable=True))
    
    # 2. Create Secrets table
    op.create_table('secrets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('secrets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_secrets_name'), ['name'], unique=True)
    
    # 3. Create Audit Logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_resource_type'), ['resource_type'], unique=False)
    
    # 4. Create Metrics table
    op.create_table('metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('metric_type', sa.String(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=True),
        sa.Column('method', sa.String(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('api_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('metadata', JSON, nullable=True),
        sa.ForeignKeyConstraint(['api_id'], ['apis.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('metrics', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_metrics_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_metrics_metric_type'), ['metric_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_metrics_endpoint'), ['endpoint'], unique=False)
        batch_op.create_index(batch_op.f('ix_metrics_api_id'), ['api_id'], unique=False)
    
    # 5. Create Backend Pools table
    op.create_table('backend_pools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('api_id', sa.Integer(), nullable=True),
        sa.Column('algorithm', sa.String(), nullable=False, default='round_robin'),
        sa.Column('backends', JSON, nullable=False),
        sa.Column('health_check_url', sa.String(), nullable=True),
        sa.Column('health_check_interval', sa.Integer(), default=30),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['api_id'], ['apis.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('backend_pools', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_backend_pools_name'), ['name'], unique=True)
        batch_op.create_index(batch_op.f('ix_backend_pools_api_id'), ['api_id'], unique=False)
    
    # 6. Create Permissions table
    op.create_table('permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('resource', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('permissions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_permissions_name'), ['name'], unique=True)
        batch_op.create_index(batch_op.f('ix_permissions_resource'), ['resource'], unique=False)
        batch_op.create_index(batch_op.f('ix_permissions_action'), ['action'], unique=False)
    
    # 7. Create Roles table
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_roles_name'), ['name'], unique=True)
    
    # 8. Create User Roles junction table
    op.create_table('user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('user_roles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_roles_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_user_roles_role_id'), ['role_id'], unique=False)
    
    # 9. Create Module Scripts table
    op.create_table('module_scripts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('script_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['module_id'], ['module_metadata.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('module_scripts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_module_scripts_module_id'), ['module_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_module_scripts_name'), ['name'], unique=False)


def downgrade() -> None:
    """Remove all new tables."""
    
    # Drop tables in reverse order
    op.drop_table('module_scripts')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('backend_pools')
    op.drop_table('metrics')
    op.drop_table('audit_logs')
    op.drop_table('secrets')
    
    # Remove columns from API Keys
    with op.batch_alter_table('api_keys', schema=None) as batch_op:
        batch_op.drop_column('metadata')
        batch_op.drop_column('usage_count')
        batch_op.drop_column('last_used_at')
        batch_op.drop_column('expires_at')
