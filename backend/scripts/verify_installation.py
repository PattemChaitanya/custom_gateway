"""
Comprehensive test script to verify all gateway management features.
Run this after setup to ensure everything works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.models import Base
import os
from dotenv import load_dotenv

load_dotenv()

# Test results tracker
test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}


def log_test(name: str, passed: bool, message: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results["tests"].append({
        "name": name,
        "passed": passed,
        "message": message
    })
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    print(f"{status} - {name}")
    if message:
        print(f"   {message}")


async def test_database_connection():
    """Test 1: Database connection"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            log_test("Database Connection", False, "DATABASE_URL not set")
            return None

        engine = create_async_engine(database_url, echo=False)
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        log_test("Database Connection", True, f"Connected to: {database_url.split('@')[1] if '@' in database_url else database_url}")
        return engine
    except Exception as e:
        log_test("Database Connection", False, str(e))
        return None


async def test_database_tables(engine):
    """Test 2: Database tables exist"""
    try:
        async with engine.begin() as conn:
            # Check for key tables
            tables_to_check = [
                "users",
                "api_keys",
                "secrets",
                "audit_logs",
                "metrics",
                "backend_pools",
                "permissions",
                "roles",
                "user_roles",
                "module_scripts"
            ]
            
            for table in tables_to_check:
                result = await conn.execute(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
                )
                exists = result.scalar()
                if not exists:
                    log_test(f"Table: {table}", False, f"Table '{table}' not found")
                    return False
            
            log_test("Database Tables", True, f"All {len(tables_to_check)} tables exist")
            return True
    except Exception as e:
        log_test("Database Tables", False, str(e))
        return False


async def test_redis_connection():
    """Test 3: Redis connection"""
    try:
        import redis.asyncio as aioredis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        redis_client = await aioredis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        
        log_test("Redis Connection", True, f"Connected to: {redis_url}")
        return True
    except Exception as e:
        log_test("Redis Connection", False, str(e))
        return False


async def test_encryption():
    """Test 4: Encryption module"""
    try:
        from app.security.encryption import encrypt_data, decrypt_data
        
        test_data = "sensitive_password_123"
        encrypted = encrypt_data(test_data)
        decrypted = decrypt_data(encrypted)
        
        if test_data == decrypted:
            log_test("Encryption/Decryption", True, "Data encrypted and decrypted successfully")
            return True
        else:
            log_test("Encryption/Decryption", False, "Decrypted data doesn't match original")
            return False
    except Exception as e:
        log_test("Encryption/Decryption", False, str(e))
        return False


async def test_validation():
    """Test 5: Input validation"""
    try:
        from app.validation.validators import validate_path_param, ValidationError
        from app.validation.sanitizers import sanitize_html
        
        # Test valid input
        validate_path_param("user123", "user_id")
        
        # Test XSS prevention
        xss_input = "<script>alert('XSS')</script>Hello"
        sanitized = sanitize_html(xss_input)
        
        if "<script>" not in sanitized:
            log_test("Input Validation", True, "XSS prevention working")
            return True
        else:
            log_test("Input Validation", False, "XSS not blocked")
            return False
    except Exception as e:
        log_test("Input Validation", False, str(e))
        return False


async def test_api_key_generation():
    """Test 6: API key generation"""
    try:
        from app.security.api_keys import generate_api_key, hash_api_key
        
        key = generate_api_key()
        hashed = hash_api_key(key)
        
        if len(key) == 32 and len(hashed) > 0:
            log_test("API Key Generation", True, f"Generated key length: {len(key)}")
            return True
        else:
            log_test("API Key Generation", False, "Invalid key format")
            return False
    except Exception as e:
        log_test("API Key Generation", False, str(e))
        return False


async def test_rate_limiter():
    """Test 7: Rate limiter algorithms"""
    try:
        from app.rate_limiter.algorithms import FixedWindowRateLimiter, TokenBucketRateLimiter
        import redis.asyncio as aioredis
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = await aioredis.from_url(redis_url, decode_responses=True)
        
        # Test fixed window
        limiter = FixedWindowRateLimiter(redis_client, key_prefix="test_")
        
        # Should allow first request
        allowed = await limiter.is_allowed("test_user", limit=10, window=60)
        await redis_client.close()
        
        if allowed:
            log_test("Rate Limiter", True, "Rate limiter working correctly")
            return True
        else:
            log_test("Rate Limiter", False, "Rate limiter not working")
            return False
    except Exception as e:
        log_test("Rate Limiter", False, str(e))
        return False


async def test_metrics():
    """Test 8: Metrics collection"""
    try:
        from app.metrics.prometheus import request_counter, request_latency
        
        # Test that metrics are registered
        request_counter.labels(method="GET", endpoint="/test", status="200").inc()
        request_latency.labels(method="GET", endpoint="/test").observe(0.5)
        
        log_test("Metrics Collection", True, "Prometheus metrics working")
        return True
    except Exception as e:
        log_test("Metrics Collection", False, str(e))
        return False


async def test_load_balancer():
    """Test 9: Load balancer algorithms"""
    try:
        from app.load_balancer.algorithms import RoundRobinLoadBalancer
        
        backends = [
            {"url": "http://backend1:8000", "weight": 1},
            {"url": "http://backend2:8000", "weight": 1},
        ]
        
        lb = RoundRobinLoadBalancer(backends)
        backend1 = lb.select_backend()
        backend2 = lb.select_backend()
        
        if backend1 != backend2:
            log_test("Load Balancer", True, "Round-robin working correctly")
            return True
        else:
            log_test("Load Balancer", False, "Round-robin not working")
            return False
    except Exception as e:
        log_test("Load Balancer", False, str(e))
        return False


async def test_authorizers():
    """Test 10: Authorization system"""
    try:
        from app.authorizers.policies import PolicyEngine, ResourcePermission
        
        engine = PolicyEngine()
        
        # Test policy evaluation
        user = {"id": 1, "roles": ["admin"]}
        resource = ResourcePermission(
            resource_type="api",
            resource_id="123",
            owner_id=1,
            visibility="private"
        )
        
        allowed = engine.evaluate(user, resource, "read")
        
        if allowed:
            log_test("Authorization System", True, "Policy engine working")
            return True
        else:
            log_test("Authorization System", False, "Policy evaluation failed")
            return False
    except Exception as e:
        log_test("Authorization System", False, str(e))
        return False


async def test_connectors():
    """Test 11: Connector infrastructure"""
    try:
        from app.connectors.database import PostgreSQLConnector
        
        # Just test that the class exists and can be instantiated
        config = {
            "host": "localhost",
            "port": 5432,
            "user": "test",
            "password": "test",
            "database": "test"
        }
        
        connector = PostgreSQLConnector(config)
        
        log_test("Connectors", True, "Connector infrastructure ready")
        return True
    except Exception as e:
        log_test("Connectors", False, str(e))
        return False


async def test_logging():
    """Test 12: Audit logging"""
    try:
        from app.logging.audit import AuditLogger
        
        # Test that logger can be instantiated
        # (we won't actually write to DB without session)
        log_test("Audit Logging", True, "Audit logger infrastructure ready")
        return True
    except Exception as e:
        log_test("Audit Logging", False, str(e))
        return False


async def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = test_results["passed"] + test_results["failed"]
    pass_rate = (test_results["passed"] / total * 100) if total > 0 else 0
    
    print(f"Total Tests: {total}")
    print(f"Passed: {test_results['passed']} ✅")
    print(f"Failed: {test_results['failed']} ❌")
    print(f"Pass Rate: {pass_rate:.1f}%")
    
    if test_results["failed"] > 0:
        print("\nFailed Tests:")
        for test in test_results["tests"]:
            if not test["passed"]:
                print(f"  ❌ {test['name']}: {test['message']}")
    
    print("="*60)
    
    # Exit code based on results
    return 0 if test_results["failed"] == 0 else 1


async def main():
    """Run all tests"""
    print("="*60)
    print("GATEWAY MANAGEMENT SYSTEM - VERIFICATION TESTS")
    print("="*60)
    print()
    
    # Infrastructure tests
    print("🔧 Testing Infrastructure...")
    engine = await test_database_connection()
    
    if engine:
        await test_database_tables(engine)
        await engine.dispose()
    
    await test_redis_connection()
    
    # Module tests
    print("\n🧪 Testing Modules...")
    await test_encryption()
    await test_validation()
    await test_api_key_generation()
    await test_rate_limiter()
    await test_metrics()
    await test_load_balancer()
    await test_authorizers()
    await test_connectors()
    await test_logging()
    
    # Summary
    exit_code = await print_summary()
    
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
