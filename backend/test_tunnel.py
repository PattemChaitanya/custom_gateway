"""
Test PostgreSQL Connection through SSH Tunnel
This script tests the database connection after the tunnel is established.
"""
import asyncio
import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db import get_db_manager
from sqlalchemy import text


@pytest.mark.asyncio
async def test_tunnel_connection():
    """Test database connection through the SSH tunnel."""
    print("\n" + "="*70)
    print("🔍 Testing PostgreSQL Connection Through SSH Tunnel")
    print("="*70 + "\n")
    
    # Check environment
    print("📋 Environment Check:")
    print(f"  AWS_DB_HOST: {os.getenv('AWS_DB_HOST')}")
    print(f"  AWS_DB_PORT: {os.getenv('AWS_DB_PORT')}")
    print(f"  AWS_DB_NAME: {os.getenv('AWS_DB_NAME')}")
    print(f"  AWS_DB_USER: {os.getenv('AWS_DB_USER')}")
    print(f"  AWS_REQUIRE_SSL: {os.getenv('AWS_REQUIRE_SSL')}")
    
    if os.getenv('AWS_DB_HOST') != 'localhost':
        print("\n⚠️  Warning: AWS_DB_HOST should be 'localhost' when using tunnel")
        print("   Update your .env file or copy .env.tunnel to .env")
    
    print("\n🔌 Initializing Database Manager...")
    db_manager = get_db_manager()
    
    try:
        await db_manager.initialize(echo_sql=False)
        
        info = db_manager.get_connection_info()
        health = await db_manager.health_check()
        
        print("\n📊 Connection Status:")
        print(f"  Database Type: {info['database_type']}")
        print(f"  Using Primary: {info['is_using_primary']}")
        print(f"  Health: {health['status']}")
        print(f"  Message: {health['message']}")
        
        if info['is_using_primary']:
            print("\n✅ SUCCESS! Connected to PostgreSQL through tunnel")
            
            # Try a test query
            print("\n🧪 Running test query...")
            async with db_manager.get_session() as session:
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()
                print(f"  PostgreSQL Version: {version[:50]}...")
                
                # Test database
                result = await session.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                print(f"  Connected to database: {db_name}")
                
                # Test user
                result = await session.execute(text("SELECT current_user"))
                user = result.scalar()
                print(f"  Connected as user: {user}")
                
                # Count tables
                result = await session.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
                table_count = result.scalar()
                print(f"  Tables in database: {table_count}")
            
            print("\n" + "="*70)
            print("🎉 SSH Tunnel is working perfectly!")
            print("="*70)
            print("\n✅ You can now run your application:")
            print("   uvicorn app.main:app --reload")
            
        else:
            print("\n❌ FAILED: Could not connect to PostgreSQL")
            print("\n📋 Troubleshooting:")
            print("  1. Is the SSH tunnel running?")
            print("     Check: .\\setup_tunnel.ps1 -Status")
            print("  2. Is port 5432 accessible?")
            print("     Test: Test-NetConnection localhost -Port 5432")
            print("  3. Are environment variables correct?")
            print("     Check: AWS_DB_HOST should be 'localhost'")
            print("  4. Try restarting the tunnel:")
            print("     Run: .\\setup_tunnel.ps1 -Restart")
        
        await db_manager.shutdown()
        
        return info['is_using_primary']
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n📋 Check:")
        print("  1. SSH tunnel is running")
        print("  2. Environment variables are set correctly")
        print("  3. Database credentials are correct")
        await db_manager.shutdown()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_tunnel_connection())
    sys.exit(0 if success else 1)
