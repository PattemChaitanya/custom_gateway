import os
from urllib.parse import quote_plus
from pathlib import Path


# Build a SQLAlchemy async URL for AWS Postgres when individual AWS_* env vars are
# provided. This allows deploying to AWS RDS/Aurora using explicit environment
# variables instead of a single DATABASE_URL.
def build_aws_database_url() -> str | None:
        """Return a postgresql+asyncpg URL constructed from AWS environment vars.

        Expected environment variables (all required for construction):
            - AWS_DB_HOST
            - AWS_DB_NAME
            - AWS_DB_USER
            - AWS_DB_PASSWORD
            - AWS_DB_PORT (optional, default 5432)
            - AWS_REQUIRE_SSL (optional, '1'/'true'/'yes' to enable sslmode=require)

        Returns None when required vars are missing.
        """
        host = os.getenv("AWS_DB_HOST")
        name = os.getenv("AWS_DB_NAME")
        user = os.getenv("AWS_DB_USER")
        password = os.getenv("AWS_DB_PASSWORD")
        port = os.getenv("AWS_DB_PORT", "5432")

        if not (host and name and user and password):
                return None

        # percent-encode user/password
        user_enc = quote_plus(user)
        pwd_enc = quote_plus(password)

        # Add sslmode if requested. asyncpg understands sslmode in query string.
        require_ssl = os.getenv("AWS_REQUIRE_SSL", "False").lower() in ("1", "true", "yes")
        ssl_query = "?sslmode=require" if require_ssl else ""

        return f"postgresql+asyncpg://{user_enc}:{pwd_enc}@{host}:{port}/{name}{ssl_query}"


# Database URL. Prefer setting DATABASE_URL in environment for production. If not
# provided, try to build one from AWS_* environment variables. When neither are
# present, keep DATABASE_URL as None so the connector can choose an in-memory
# fallback instead of implicitly creating a sqlite DB here.
# Examples:
#   - Explicit full URL: DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
#   - AWS parts: AWS_DB_HOST, AWS_DB_NAME, AWS_DB_USER, AWS_DB_PASSWORD
# Resolve a sensible default sqlite path relative to the backend package so that
# running the server from the `backend/` working directory does not produce a
# duplicate `backend/backend/dev.db` path. For development we prefer an actual
# sqlite file located at backend/dev.db. If you want an in-memory fallback,
# unset DATABASE_URL and ensure AWS_* vars are not set (the connector will
# fallback to the in-memory DB when DATABASE_URL is None).
default_db_path = Path(__file__).resolve().parents[2] / "dev.db"
DATABASE_URL = os.getenv("DATABASE_URL") or build_aws_database_url() or f"sqlite+aiosqlite:///{default_db_path}"


# SQLAlchemy echo flag
SQL_ECHO = os.getenv("SQL_ECHO", "False").lower() in ("1", "true", "yes")
