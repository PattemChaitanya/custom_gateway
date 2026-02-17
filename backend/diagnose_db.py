"""Check database configuration and connection status"""
from app.db.progress_sql import (
    build_aws_database_url,
    get_database_url_from_env,
    validate_postgres_sync,
)
from app.db import get_db_manager
import os
import asyncio
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def print_env_config():
    """Print current environment configuration."""
    print("=" * 70)
    print("ENVIRONMENT CONFIGURATION")
    print("=" * 70)

    env_vars = {
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "AWS_DB_HOST": os.getenv("AWS_DB_HOST"),
        "AWS_DB_NAME": os.getenv("AWS_DB_NAME"),
        "AWS_DB_USER": os.getenv("AWS_DB_USER"),
        "AWS_DB_PASSWORD": "***" if os.getenv("AWS_DB_PASSWORD") else None,
        "AWS_DB_PORT": os.getenv("AWS_DB_PORT"),
        "AWS_REQUIRE_SSL": os.getenv("AWS_REQUIRE_SSL"),
        "AWS_SSLROOTCERT": os.getenv("AWS_SSLROOTCERT"),
        "AWS_DB_SECRET": os.getenv("AWS_DB_SECRET"),
        "AWS_SECRET_NAME": os.getenv("AWS_SECRET_NAME"),
        "AWS_REGION": os.getenv("AWS_REGION"),
    }

    for key, value in env_vars.items():
        status = "✓" if value else "✗"
        print(f"{status} {key}: {value or 'Not set'}")


def check_url_building():
    """Check if database URL can be built."""
    print("\n" + "=" * 70)
    print("URL BUILDING CHECK")
    print("=" * 70)

    # Try building AWS URL
    aws_url = build_aws_database_url()
    if aws_url:
        print("✓ AWS URL built successfully")
        # Mask password in output
        masked_url = aws_url
        if "@" in masked_url:
            parts = masked_url.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split("://")[1]
                user = user_pass.split(":")[0]
                masked_url = masked_url.replace(user_pass, f"{user}:***")
        print(f"  URL: {masked_url}")
    else:
        print("✗ Could not build AWS database URL")
        print("  Missing required environment variables:")
        if not os.getenv("AWS_DB_HOST"):
            print("    - AWS_DB_HOST")
        if not os.getenv("AWS_DB_NAME"):
            print("    - AWS_DB_NAME")
        if not os.getenv("AWS_DB_USER"):
            print("    - AWS_DB_USER")
        if not os.getenv("AWS_DB_PASSWORD"):
            print("    - AWS_DB_PASSWORD")

    # Try getting URL from environment (all methods)
    env_url = get_database_url_from_env()
    if env_url:
        print("\n✓ Database URL resolved from environment")
    else:
        print("\n✗ No database URL could be resolved")

    return aws_url or env_url


def check_connection(url):
    """Check if connection is possible."""
    print("\n" + "=" * 70)
    print("CONNECTION VALIDATION")
    print("=" * 70)

    if not url:
        print("✗ No URL to test")
        return False

    # Check if psycopg2 is available
    import importlib.util
    if importlib.util.find_spec("psycopg2") is None:
        print("✗ psycopg2 not available - cannot validate connection")
        print("  Install with: pip install psycopg2-binary")
        return False

    print("✓ psycopg2 is available for validation")

    # Try to validate connection
    print("\nAttempting connection validation...")
    try:
        result = validate_postgres_sync(url, timeout=5)
        if result:
            print("✓ PostgreSQL connection validation SUCCESSFUL")
            return True
        else:
            print("✗ PostgreSQL connection validation FAILED")
            print("  Possible causes:")
            print("    - Database server not reachable")
            print("    - Incorrect credentials")
            print("    - Network/firewall issues")
            print("    - Security group not configured")
            return False
    except Exception as e:
        print(f"✗ Connection validation error: {e}")
        return False


async def check_db_manager():
    """Check DatabaseManager initialization."""
    print("\n" + "=" * 70)
    print("DATABASE MANAGER INITIALIZATION")
    print("=" * 70)

    db_manager = get_db_manager()

    print("\nInitializing DatabaseManager...")
    # Allow more time for first-time table creation on remote RDS
    await db_manager.initialize(echo_sql=False, timeout=60)

    # Get connection info
    info = db_manager.get_connection_info()
    print(
        f"\n{'✓' if info['is_using_primary'] else '✗'} Using Primary: {info['is_using_primary']}")
    print(f"  Database Type: {info['database_type']}")
    print(f"  Has Engine: {info['has_engine']}")
    print(f"  Has Session Factory: {info['has_session_factory']}")
    print(f"  Has In-Memory DB: {info['has_inmemory_db']}")

    # Health check
    health = await db_manager.health_check()
    print(f"\nHealth Status: {health['status'].upper()}")
    print(f"Database: {health['database']}")
    print(f"Message: {health['message']}")

    await db_manager.shutdown()

    return info['is_using_primary']


async def main():
    """Main diagnostic function."""
    print("\n🔍 AWS PostgreSQL Connection Diagnostic Tool\n")

    # Step 1: Check environment
    print_env_config()

    # Step 2: Check URL building
    url = check_url_building()

    # Step 3: Validate connection
    if url:
        can_connect = check_connection(url)
    else:
        can_connect = False

    # Step 4: Check DatabaseManager
    using_primary = await check_db_manager()

    # Summary
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)

    if using_primary:
        print("✅ AWS PostgreSQL connection is WORKING")
    else:
        print("❌ AWS PostgreSQL connection FAILED - using in-memory fallback")
        print("\n📋 Troubleshooting Steps:")
        print("1. Verify AWS_DB_* environment variables are set correctly")
        print("2. Check database server is running and accessible")
        print("3. Verify network connectivity and firewall rules")
        print("4. Confirm security group allows connections from your IP")
        print("5. Validate credentials are correct")
        if not can_connect:
            print(
                "6. Install psycopg2 for connection validation: pip install psycopg2-binary")


if __name__ == "__main__":
    asyncio.run(main())
