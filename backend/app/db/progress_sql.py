import os
from urllib.parse import quote_plus


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
# provided, try to build one from AWS_* environment variables; otherwise fall
# back to a local SQLite async DB for development/testing to avoid requiring an
# external Postgres instance.
# Examples:
#   - Explicit full URL: DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
#   - AWS parts: AWS_DB_HOST, AWS_DB_NAME, AWS_DB_USER, AWS_DB_PASSWORD
DATABASE_URL = os.getenv("DATABASE_URL") or build_aws_database_url() or "sqlite+aiosqlite:///./dev.db"


# SQLAlchemy echo flag
SQL_ECHO = os.getenv("SQL_ECHO", "False").lower() in ("1", "true", "yes")
