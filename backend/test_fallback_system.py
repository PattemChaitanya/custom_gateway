"""
Test script to verify three-tier database fallback implementation.

This script tests the fallback sequence:
1. PostgreSQL (primary)
2. SQLite (secondary)
3. In-memory (final)
"""

from types import SimpleNamespace
from app.db.models import User, API
from app.db import get_db_manager
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))


async def test_database_fallback():
    """Test all three database tiers."""

    print("=" * 70)
    print("Testing Three-Tier Database Fallback")
    print("=" * 70)

    db_manager = get_db_manager()

    # Test 1: Initial connection (will try PostgreSQL first)
    print("\n[TEST 1] Initial Connection Attempt")
    print("-" * 70)

    await db_manager.initialize(echo_sql=False)

    info = db_manager.get_connection_info()
    health = await db_manager.health_check()

    print(f"Database Type: {info['database_type']}")
    print(f"Using Primary (PostgreSQL): {info['is_using_primary']}")
    print(f"Using SQLite: {info['is_using_sqlite']}")
    print(f"Health Status: {health['status']}")
    print(f"Health Message: {health['message']}")

    if info['is_using_primary']:
        print("✓ Connected to PostgreSQL (Primary)")
    elif info['is_using_sqlite']:
        print(
            f"✓ Connected to SQLite (Secondary) at: {info.get('sqlite_path', 'gateway.db')}")
    else:
        print("⚠ Using In-Memory storage (Final Fallback)")

    # Test 2: Basic CRUD operations
    print("\n[TEST 2] Basic CRUD Operations")
    print("-" * 70)

    try:
        async with db_manager.get_session() as session:
            # Test create
            api_data = {
                "name": "Test API",
                "version": "1.0.0",
                "description": "Test API for fallback verification",
                "type": "rest"
            }

            if hasattr(session, 'create_api'):
                # SQLite or In-Memory
                api = await session.create_api(api_data)
                print(f"✓ Created API: {api.name} (id={api.id})")
            else:
                # PostgreSQL
                try:
                    from app.api.apis.crud import create_api_db
                    from app.api.apis.schemas import APICreate
                    api_create = APICreate(**api_data)
                    api = await create_api_db(session, api_create)
                    print(f"✓ Created API: {api.name} (id={api.id})")
                except ImportError:
                    print("⚠ CRUD operations not available, skipping create test")
                    api = None

            # Test read
            if hasattr(session, 'list_apis'):
                apis = await session.list_apis()
            elif api:
                try:
                    from app.api.apis.crud import list_apis_db
                    apis = await list_apis_db(session)
                except ImportError:
                    apis = []
            else:
                apis = []

            print(f"✓ Listed APIs: Found {len(apis)} API(s)")

    except Exception as e:
        print(f"✗ CRUD operation failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Connection info
    print("\n[TEST 3] Connection Information")
    print("-" * 70)

    info = db_manager.get_connection_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    # Test 4: Simulate fallback (if using primary)
    if info['is_using_primary']:
        print("\n[TEST 4] Simulating Fallback to SQLite")
        print("-" * 70)
        print("Shutting down PostgreSQL connection...")

        await db_manager.shutdown()

        # Force SQLite initialization
        print("Attempting SQLite connection...")
        if await db_manager._initialize_sqlite_database():
            print("✓ Successfully fell back to SQLite")

            info = db_manager.get_connection_info()
            print(f"  Database Type: {info['database_type']}")
            print(f"  SQLite Path: {info.get('sqlite_path')}")
        else:
            print("✗ SQLite initialization failed, trying in-memory...")
            db_manager._initialize_fallback_database()
            print("✓ Fell back to in-memory storage")

    elif info['is_using_sqlite']:
        print("\n[TEST 4] Simulating Fallback to In-Memory")
        print("-" * 70)
        print("Shutting down SQLite connection...")

        await db_manager.shutdown()

        print("Falling back to in-memory storage...")
        db_manager._initialize_fallback_database()
        print("✓ Successfully fell back to in-memory storage")

        info = db_manager.get_connection_info()
        print(f"  Database Type: {info['database_type']}")

    else:
        print("\n[TEST 4] Already Using In-Memory (Final Fallback)")
        print("-" * 70)
        print("⚠ No further fallback available")

    # Cleanup
    print("\n[CLEANUP] Shutting down database manager")
    print("-" * 70)
    await db_manager.shutdown()
    print("✓ Database manager shut down successfully")

    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)


async def test_specific_tier(tier: str):
    """Test a specific database tier."""

    print(f"\n[TESTING SPECIFIC TIER: {tier.upper()}]")
    print("=" * 70)

    db_manager = get_db_manager()

    if tier.lower() == "postgresql":
        # Try normal initialization (should connect to PostgreSQL)
        await db_manager.initialize()

    elif tier.lower() == "sqlite":
        # Skip PostgreSQL, go directly to SQLite
        success = await db_manager._initialize_sqlite_database()
        if not success:
            print("✗ Failed to initialize SQLite")
            return

    elif tier.lower() == "inmemory":
        # Skip both PostgreSQL and SQLite
        db_manager._initialize_fallback_database()

    else:
        print(f"Unknown tier: {tier}")
        return

    info = db_manager.get_connection_info()
    health = await db_manager.health_check()

    print(f"\nDatabase Type: {info['database_type']}")
    print(f"Health Status: {health['status']}")
    print(f"Health Message: {health['message']}")

    # Test basic operation
    try:
        async with db_manager.get_session() as session:
            print("\n✓ Session acquired successfully")
            print(f"  Session type: {type(session).__name__}")
    except Exception as e:
        print(f"\n✗ Failed to acquire session: {e}")

    await db_manager.shutdown()
    print("\n✓ Test complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test database fallback system")
    parser.add_argument(
        "--tier",
        choices=["postgresql", "sqlite", "inmemory", "all"],
        default="all",
        help="Specific tier to test (default: all)"
    )

    args = parser.parse_args()

    if args.tier == "all":
        asyncio.run(test_database_fallback())
    else:
        asyncio.run(test_specific_tier(args.tier))
