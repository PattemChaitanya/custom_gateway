"""Add multi-tenancy Account model and account_id FKs to all tenant-scoped tables.

Revision ID: 0008_add_account_tenancy
Revises: 0007_add_rate_limit_algorithm
Create Date: 2026-04-01

Changes
-------
1. Create ``accounts`` table (id, slug, name, plan, status, metadata, timestamps)
2. Add nullable ``account_id`` FK to:
   - users         (SET NULL on account delete — superusers stay)
   - apis          (CASCADE — APIs belong to exactly one account)
   - api_keys      (CASCADE)
   - environments  (CASCADE — drop global unique on slug; add per-account unique)
   - secrets       (CASCADE — drop global unique on name; add per-account unique)
   - audit_logs    (SET NULL — retain log entries even if account is deleted)
   - metrics       (SET NULL — retain metrics history)

All new FK columns are nullable so existing rows survive the migration without
needing a default account.  Phase 2 will backfill a "system" account for
existing data when single-tenancy → multi-tenancy migration runs.
"""
from alembic import op
import sqlalchemy as sa

revision = '0008_add_account_tenancy'
down_revision = '0007_add_rate_limit_algorithm'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Create accounts table ─────────────────────────────────────────────
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=63), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_accounts_slug'),
        # Slug must start with a letter — ensures /gw/{account_slug}/{api_id}/...
        # is unambiguous (numeric slugs would collide with api_id integers).
        # NOTE: PostgreSQL only; SQLite ignores CHECK constraints at DDL time
        #       but the application-level regex in AccountCreate enforces this.
        sa.CheckConstraint("slug ~ '^[a-z][a-z0-9\\-]*$'", name='ck_accounts_slug_format'),
    )
    op.create_index('ix_accounts_id', 'accounts', ['id'])
    op.create_index('ix_accounts_slug', 'accounts', ['slug'])
    op.create_index('ix_accounts_status', 'accounts', ['status'])

    # ── 2. users ─────────────────────────────────────────────────────────────
    op.add_column('users', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_index('ix_users_account_id', 'users', ['account_id'])
    op.create_foreign_key(
        'fk_users_account_id', 'users', 'accounts', ['account_id'], ['id'],
        ondelete='SET NULL',
    )

    # ── 3. apis ───────────────────────────────────────────────────────────────
    op.add_column('apis', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_index('ix_apis_account_id', 'apis', ['account_id'])
    op.create_foreign_key(
        'fk_apis_account_id', 'apis', 'accounts', ['account_id'], ['id'],
        ondelete='CASCADE',
    )
    # Replace global (name, version) unique with per-account unique
    op.drop_constraint('uq_api_name_version', 'apis', type_='unique')
    op.create_unique_constraint(
        'uq_api_account_name_version', 'apis', ['account_id', 'name', 'version'],
    )

    # ── 4. api_keys ───────────────────────────────────────────────────────────
    op.add_column('api_keys', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_index('ix_api_keys_account_id', 'api_keys', ['account_id'])
    op.create_foreign_key(
        'fk_api_keys_account_id', 'api_keys', 'accounts', ['account_id'], ['id'],
        ondelete='CASCADE',
    )

    # ── 5. environments ───────────────────────────────────────────────────────
    op.add_column('environments', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_index('ix_environments_account_id', 'environments', ['account_id'])
    op.create_foreign_key(
        'fk_environments_account_id', 'environments', 'accounts', ['account_id'], ['id'],
        ondelete='CASCADE',
    )
    # Drop global unique on slug; replace with per-account unique
    op.drop_constraint('uq_environments_slug', 'environments', type_='unique')
    op.create_unique_constraint(
        'uq_environment_account_slug', 'environments', ['account_id', 'slug'],
    )

    # ── 6. secrets ────────────────────────────────────────────────────────────
    op.add_column('secrets', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_index('ix_secrets_account_id', 'secrets', ['account_id'])
    op.create_foreign_key(
        'fk_secrets_account_id', 'secrets', 'accounts', ['account_id'], ['id'],
        ondelete='CASCADE',
    )
    # Drop global unique on name; replace with per-account unique
    op.drop_constraint('uq_secrets_name', 'secrets', type_='unique')
    op.create_unique_constraint(
        'uq_secret_account_name', 'secrets', ['account_id', 'name'],
    )

    # ── 7. audit_logs ─────────────────────────────────────────────────────────
    op.add_column('audit_logs', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_index('ix_audit_logs_account_id', 'audit_logs', ['account_id'])
    op.create_foreign_key(
        'fk_audit_logs_account_id', 'audit_logs', 'accounts', ['account_id'], ['id'],
        ondelete='SET NULL',
    )

    # ── 8. metrics ────────────────────────────────────────────────────────────
    op.add_column('metrics', sa.Column('account_id', sa.Integer(), nullable=True))
    op.create_index('ix_metrics_account_id', 'metrics', ['account_id'])
    op.create_foreign_key(
        'fk_metrics_account_id', 'metrics', 'accounts', ['account_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # metrics
    op.drop_constraint('fk_metrics_account_id', 'metrics', type_='foreignkey')
    op.drop_index('ix_metrics_account_id', table_name='metrics')
    op.drop_column('metrics', 'account_id')

    # audit_logs
    op.drop_constraint('fk_audit_logs_account_id', 'audit_logs', type_='foreignkey')
    op.drop_index('ix_audit_logs_account_id', table_name='audit_logs')
    op.drop_column('audit_logs', 'account_id')

    # secrets — restore global unique on name
    op.drop_constraint('uq_secret_account_name', 'secrets', type_='unique')
    op.drop_constraint('fk_secrets_account_id', 'secrets', type_='foreignkey')
    op.drop_index('ix_secrets_account_id', table_name='secrets')
    op.drop_column('secrets', 'account_id')
    op.create_unique_constraint('uq_secrets_name', 'secrets', ['name'])

    # environments — restore global unique on slug
    op.drop_constraint('uq_environment_account_slug', 'environments', type_='unique')
    op.drop_constraint('fk_environments_account_id', 'environments', type_='foreignkey')
    op.drop_index('ix_environments_account_id', table_name='environments')
    op.drop_column('environments', 'account_id')
    op.create_unique_constraint('uq_environments_slug', 'environments', ['slug'])

    # api_keys
    op.drop_constraint('fk_api_keys_account_id', 'api_keys', type_='foreignkey')
    op.drop_index('ix_api_keys_account_id', table_name='api_keys')
    op.drop_column('api_keys', 'account_id')

    # apis — restore global (name, version) unique
    op.drop_constraint('uq_api_account_name_version', 'apis', type_='unique')
    op.drop_constraint('fk_apis_account_id', 'apis', type_='foreignkey')
    op.drop_index('ix_apis_account_id', table_name='apis')
    op.drop_column('apis', 'account_id')
    op.create_unique_constraint('uq_api_name_version', 'apis', ['name', 'version'])

    # users
    op.drop_constraint('fk_users_account_id', 'users', type_='foreignkey')
    op.drop_index('ix_users_account_id', table_name='users')
    op.drop_column('users', 'account_id')

    # accounts table
    op.drop_index('ix_accounts_status', table_name='accounts')
    op.drop_index('ix_accounts_slug', table_name='accounts')
    op.drop_index('ix_accounts_id', table_name='accounts')
    op.drop_table('accounts')
