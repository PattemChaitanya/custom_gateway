"""Add request_logs table, partitioned by account_id on PostgreSQL.

Revision ID: 0011_add_request_logs
Revises: 0010_add_gateway_routes
Create Date: 2026-04-03

Changes
-------
1. Create ``request_logs`` table as a RANGE-partitioned parent on PostgreSQL.
   Columns: id (serial), account_id (FK), route_id (FK nullable), method,
            path, status_code, latency_ms, timestamp (partitioning key).

2. Create a default catch-all partition ``request_logs_default`` so rows
   can be inserted even before per-account partitions are created.

3. Indexes on: account_id, status_code, timestamp, (account_id, timestamp).

Note on SQLite / in-memory fallback:
   PostgreSQL DDL for partitioning is not valid on SQLite.  We detect the
   dialect at migration time and emit plain CREATE TABLE for non-PG targets.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import Connection


revision = '0011_add_request_logs'
down_revision = '0010_add_gateway_routes'
branch_labels = None
depends_on = None


def _is_postgres(conn: Connection) -> bool:
    return conn.dialect.name == "postgresql"


def upgrade() -> None:
    conn = op.get_bind()

    if _is_postgres(conn):
        # ── PostgreSQL: partitioned parent table ──────────────────────────────
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id          SERIAL,
                account_id  INTEGER NOT NULL
                            REFERENCES accounts(id) ON DELETE CASCADE,
                route_id    INTEGER
                            REFERENCES gateway_routes(id) ON DELETE SET NULL,
                method      VARCHAR(10)  NOT NULL,
                path        TEXT         NOT NULL,
                status_code INTEGER      NOT NULL,
                latency_ms  INTEGER      NOT NULL,
                timestamp   TIMESTAMPTZ  NOT NULL,
                PRIMARY KEY (id, timestamp)
            ) PARTITION BY RANGE (timestamp)
        """))

        # Default partition catches rows that don't match a specific partition
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS request_logs_default
            PARTITION OF request_logs DEFAULT
        """))
    else:
        # ── SQLite / other: plain table (no partitioning syntax) ──────────────
        op.create_table(
            'request_logs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                'account_id', sa.Integer(),
                sa.ForeignKey('accounts.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column(
                'route_id', sa.Integer(),
                sa.ForeignKey('gateway_routes.id', ondelete='SET NULL'),
                nullable=True,
            ),
            sa.Column('method', sa.String(10), nullable=False),
            sa.Column('path', sa.Text(), nullable=False),
            sa.Column('status_code', sa.Integer(), nullable=False),
            sa.Column('latency_ms', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        )

    # ── Indexes (work on both PG and SQLite) ──────────────────────────────────
    op.create_index('ix_request_logs_account_id',  'request_logs', ['account_id'])
    op.create_index('ix_request_logs_status_code', 'request_logs', ['status_code'])
    op.create_index('ix_request_logs_timestamp',   'request_logs', ['timestamp'])
    op.create_index(
        'ix_request_logs_account_ts',
        'request_logs', ['account_id', 'timestamp'],
    )


def downgrade() -> None:
    conn = op.get_bind()

    op.drop_index('ix_request_logs_account_ts',   table_name='request_logs')
    op.drop_index('ix_request_logs_timestamp',     table_name='request_logs')
    op.drop_index('ix_request_logs_status_code',   table_name='request_logs')
    op.drop_index('ix_request_logs_account_id',    table_name='request_logs')

    if _is_postgres(conn):
        conn.execute(sa.text("DROP TABLE IF EXISTS request_logs_default"))
        conn.execute(sa.text("DROP TABLE IF EXISTS request_logs"))
    else:
        op.drop_table('request_logs')
