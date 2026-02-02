import os
import json
import pytest
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from passlib.context import CryptContext
from datetime import datetime, timezone

# Load environment variables from .env file
load_dotenv()

try:
    import boto3
except Exception:
    boto3 = None

try:
    import psycopg2
except Exception:
    psycopg2 = None


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _build_dsn_from_secret(secret_name: str):
    if not boto3:
        return None
    region = os.getenv("AWS_REGION")
    client = boto3.client("secretsmanager", region_name=region) if region else boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=secret_name)
    secret_str = resp.get("SecretString")
    if not secret_str:
        return None
    data = json.loads(secret_str)
    host = data.get("host") or data.get("hostname")
    name = data.get("dbname") or data.get("database")
    user = data.get("username") or data.get("user")
    password = data.get("password")
    port = str(data.get("port") or 5432)
    if not (host and name and user and password):
        return None
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _resolve_dsn():
    # Prefer explicit DATABASE_URL
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        # accept only Postgres-style URLs; skip sqlite or other schemes
        parsed = urlparse(dsn)
        scheme = parsed.scheme or ""
        if scheme.startswith("postgres") or scheme.startswith("postgresql"):
            # strip asyncpg prefix if present for psycopg2
            if dsn.startswith("postgresql+asyncpg://"):
                return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
            return dsn
        # otherwise ignore (likely sqlite) and fall through to secrets or skip

    # Try AWS secret name
    aws_secret = os.getenv("AWS_DB_SECRET") or os.getenv("AWS_SECRET_NAME")
    if aws_secret:
        return _build_dsn_from_secret(aws_secret)

    return None


@pytest.mark.skipif(not psycopg2, reason="psycopg2 required to run Postgres insertion test")
def test_generate_sql_and_insert_users():
    dsn = _resolve_dsn()
    if not dsn:
        pytest.skip("No DATABASE_URL or AWS secret configured; skipping Postgres insertion test")

    # sample users to insert
    users = [
        {"email": "alice@example.com", "password": "alicepass", "roles": "viewer", "is_superuser": False},
        {"email": "bob@example.com", "password": "bobpass", "roles": "viewer", "is_superuser": False},
        {"email": "admin@example.com", "password": "adminpass", "roles": "admin", "is_superuser": True},
    ]

    # build SQL insert statements with hashed passwords and timestamps
    now = datetime.now(timezone.utc).isoformat()
    stmts = []
    for u in users:
        hashed = pwd_context.hash(u["password"])
        # Use parameterized style for execution; we will also write a literal SQL file for review
        stmt = {
            "email": u["email"],
            "hashed_password": hashed,
            "is_active": True,
            "is_superuser": u["is_superuser"],
            "roles": u["roles"],
            "created_at": now,
        }
        stmts.append(stmt)

    # write a SQL file with INSERT statements (literal values) for visibility
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    sql_path = scripts_dir / "insert_users.sql"
    with sql_path.open("w", encoding="utf-8") as fh:
        fh.write("-- Generated INSERT statements for users\n")
        for s in stmts:
            # Escape single quotes
            hp = s["hashed_password"].replace("'", "''")
            roles = (s["roles"] or "").replace("'", "''")
            fh.write(
                "INSERT INTO users (email, hashed_password, is_active, is_superuser, roles, created_at) VALUES ('{}', '{}', {} , {} , '{}', '{}');\n".format(
                    s["email"].replace("'", "''"), hp, 'true' if s["is_active"] else 'false', 'true' if s["is_superuser"] else 'false', roles, s["created_at"]
                )
            )

    # execute inserts against Postgres using psycopg2
    try:
        conn = psycopg2.connect(dsn)
    except (psycopg2.OperationalError, Exception) as e:
        pytest.skip(f"Cannot connect to PostgreSQL: {e}")
    
    try:
        cur = conn.cursor()
        # ensure users table exists (simple compatible schema) - if Alembic manages schema, this is a no-op
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(320) UNIQUE NOT NULL,
                hashed_password VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
                roles VARCHAR,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ
            )
            """
        )
        conn.commit()

        inserted = 0
        for s in stmts:
            cur.execute(
                "SELECT id FROM users WHERE email = %s",
                (s["email"],),
            )
            if cur.fetchone():
                # already exists, skip
                continue
            cur.execute(
                "INSERT INTO users (email, hashed_password, is_active, is_superuser, roles, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (s["email"], s["hashed_password"], s["is_active"], s["is_superuser"], s["roles"], s["created_at"]),
            )
            inserted += 1
        conn.commit()

        # verify result
        cur.execute("SELECT email FROM users WHERE email IN %s", (tuple(u["email"] for u in users),))
        rows = [r[0] for r in cur.fetchall()]
        assert set(rows).issuperset({u["email"] for u in users})
    finally:
        conn.close()
