"""
PostgreSQL Connection Utilities for AWS

This module provides utilities for building and validating PostgreSQL database URLs
from AWS environment variables and AWS Secrets Manager.
"""

import os
import json
import logging
from urllib.parse import quote_plus, urlparse
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

try:
    import boto3
except ImportError:
    boto3 = None
    logger.debug("boto3 not available - AWS Secrets Manager integration disabled")

try:
    import psycopg2
    from psycopg2 import OperationalError
except ImportError:
    psycopg2 = None
    OperationalError = Exception
    logger.debug("psycopg2 not available - sync connection validation disabled")


def load_env_file() -> None:
    """
    Load environment variables from .env file in backend directory.
    
    Only loads if DATABASE_URL is not already set, to avoid overriding
    test environment variables.
    """
    backend_dir = Path(__file__).resolve().parents[2]
    dotenv_path = backend_dir / ".env"
    
    if dotenv_path.exists() and "DATABASE_URL" not in os.environ:
        load_dotenv(dotenv_path=str(dotenv_path))
        logger.debug(f"Loaded environment from {dotenv_path}")


# Load environment file on module import
load_env_file()


def build_aws_database_url() -> Optional[str]:
    """
    Build a PostgreSQL connection URL from AWS environment variables.
    
    Required environment variables:
        - AWS_DB_HOST: Database host
        - AWS_DB_NAME: Database name
        - AWS_DB_USER: Database user
        - AWS_DB_PASSWORD: Database password
        
    Optional environment variables:
        - AWS_DB_PORT: Database port (default: 5432)
        - AWS_REQUIRE_SSL: Require SSL connection (default: False)
        - AWS_SSLROOTCERT: Path to SSL root certificate
    
    Returns:
        str | None: PostgreSQL connection URL or None if required vars are missing
    """
    host = os.getenv("AWS_DB_HOST")
    name = os.getenv("AWS_DB_NAME")
    user = os.getenv("AWS_DB_USER")
    password = os.getenv("AWS_DB_PASSWORD")
    port = os.getenv("AWS_DB_PORT", "5432")

    if not (host and name and user and password):
        logger.debug("AWS database environment variables not fully configured")
        return None

    # URL encode credentials
    user_enc = quote_plus(user)
    pwd_enc = quote_plus(password)
    
    # Determine SSL mode
    # Support both AWS_REQUIRE_SSL values and AWS_SSLROOTCERT/AWS_DB_SSL_FILE_PATH
    require_ssl_env = os.getenv("AWS_REQUIRE_SSL", "False").lower()
    sslroot = os.getenv("AWS_SSLROOTCERT") or os.getenv("AWS_DB_SSL_FILE_PATH")
    
    # Check if SSL is required (supports various formats)
    require_ssl = require_ssl_env in ("1", "true", "yes", "require", "verify-full", "verify-ca")

    if require_ssl_env == "verify-full" or (require_ssl and sslroot):
        ssl_query = "?sslmode=verify-full"
    elif require_ssl or require_ssl_env in ("require", "verify-ca"):
        ssl_query = "?sslmode=require"
    else:
        ssl_query = ""

    url = f"postgresql+asyncpg://{user_enc}:{pwd_enc}@{host}:{port}/{name}{ssl_query}"
    logger.debug(f"Built AWS database URL for {host}:{port}/{name}")
    return url


def build_database_url_from_secret(secret_name: str) -> Optional[str]:
    """
    Build a PostgreSQL connection URL from AWS Secrets Manager.
    
    Expects secret to contain JSON with keys:
        - host/hostname/Host
        - dbname/database/db_name/name
        - username/user/Username
        - password/pwd/Password
        - port/Port (optional, default: 5432)
    
    Args:
        secret_name: Name or ARN of the secret in AWS Secrets Manager
        
    Returns:
        str | None: PostgreSQL connection URL or None on error
    """
    if not boto3:
        logger.warning("boto3 not available - cannot retrieve AWS secrets")
        return None
        
    region = os.getenv("AWS_REGION")
    
    try:
        client = boto3.client(
            "secretsmanager",
            region_name=region
        ) if region else boto3.client("secretsmanager")
        
        response = client.get_secret_value(SecretId=secret_name)
        secret_str = response.get("SecretString")
        
        if not secret_str:
            logger.error(f"Secret {secret_name} has no SecretString")
            return None
            
        data = json.loads(secret_str)

        # Extract database credentials with fallback key names
        host = data.get("host") or data.get("hostname") or data.get("Host")
        name = (
            data.get("dbname") or data.get("database") or 
            data.get("db_name") or data.get("name")
        )
        user = data.get("username") or data.get("user") or data.get("Username")
        password = data.get("password") or data.get("pwd") or data.get("Password")
        port = str(data.get("port") or data.get("Port") or 5432)

        if not (host and name and user and password):
            logger.error(f"Secret {secret_name} missing required database credentials")
            return None

        # URL encode credentials
        user_enc = quote_plus(str(user))
        pwd_enc = quote_plus(str(password))
        
        # Determine SSL mode
        require_ssl = os.getenv("AWS_REQUIRE_SSL", "False").lower() in ("1", "true", "yes")
        sslroot = os.getenv("AWS_SSLROOTCERT")

        if require_ssl and sslroot:
            ssl_query = "?sslmode=verify-full"
        elif require_ssl:
            ssl_query = "?sslmode=require"
        else:
            ssl_query = ""

        url = f"postgresql+asyncpg://{user_enc}:{pwd_enc}@{host}:{port}/{name}{ssl_query}"
        logger.info(f"Successfully retrieved database URL from secret {secret_name}")
        return url
        
    except Exception as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}", exc_info=True)
        return None


def is_postgres_url(url: str) -> bool:
    """
    Check if a URL is a PostgreSQL connection string.
    
    Args:
        url: Database connection URL
        
    Returns:
        bool: True if URL is a PostgreSQL connection string
    """
    try:
        parsed = urlparse(url)
        return parsed.scheme.startswith("postgres")
    except Exception:
        return False


def validate_postgres_sync(url: str, timeout: int = 3) -> bool:
    """
    Validate PostgreSQL connection using synchronous psycopg2.
    
    This is used to quickly test connectivity before creating async engines.
    
    Args:
        url: PostgreSQL connection URL
        timeout: Connection timeout in seconds
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    if not psycopg2:
        logger.warning("psycopg2 not available - skipping connection validation")
        return True  # Assume valid if we can't test
        
    try:
        # Convert asyncpg URL to psycopg2 URL if needed
        if url.startswith("postgresql+asyncpg://"):
            probe_url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        else:
            probe_url = url

        # Configure connection parameters
        connect_kwargs = {"connect_timeout": timeout}
        
        # Support both SSL certificate path variable names
        sslroot = os.getenv("AWS_SSLROOTCERT") or os.getenv("AWS_DB_SSL_FILE_PATH")
        if sslroot and os.path.exists(sslroot):
            connect_kwargs["sslrootcert"] = sslroot

        # Attempt connection
        conn = psycopg2.connect(probe_url, **connect_kwargs)
        conn.close()
        
        logger.debug("PostgreSQL connection validation successful")
        return True
        
    except OperationalError as e:
        logger.warning(f"PostgreSQL connection validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during connection validation: {e}")
        return False


async def validate_postgres_connection(url: str, timeout: int = 5) -> bool:
    """
    Validate PostgreSQL connection asynchronously.
    
    Runs the synchronous validation in a thread pool to avoid blocking.
    
    Args:
        url: PostgreSQL connection URL
        timeout: Connection timeout in seconds
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        validate_postgres_sync,
        url,
        timeout
    )


def get_database_url_from_env() -> Optional[str]:
    """
    Get database URL from environment with priority order:
    1. Explicit DATABASE_URL environment variable
    2. AWS Secrets Manager (if AWS_DB_SECRET or AWS_SECRET_NAME is set)
    3. AWS environment variables (AWS_DB_HOST, AWS_DB_NAME, etc.)
    
    Returns:
        str | None: Database connection URL or None if not configured
    """
    # Check for explicit DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if url:
        logger.debug("Using DATABASE_URL from environment")
        return url
    
    # Check for AWS Secrets Manager
    secret_name = os.getenv("AWS_DB_SECRET") or os.getenv("AWS_SECRET_NAME")
    if secret_name:
        logger.info(f"Attempting to retrieve database URL from secret: {secret_name}")
        url = build_database_url_from_secret(secret_name)
        if url:
            return url
    
    # Check for AWS environment variables
    url = build_aws_database_url()
    if url:
        return url
    
    logger.debug("No database URL found in environment")
    return None


# Module-level constants
SQL_ECHO = os.getenv("SQL_ECHO", "False").lower() in ("1", "true", "yes")
DATABASE_URL = get_database_url_from_env()

