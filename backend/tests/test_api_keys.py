"""
Test cases for Enhanced API Keys module.

Tests:
1. API key generation
2. API key hashing
3. API key expiration
4. Usage tracking
5. Scopes/permissions
6. Revocation
7. CRUD operations
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, APIKey
from app.security.api_keys import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    APIKeyManager
)


@pytest.fixture
async def db_session():
    """Create an in-memory database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


class TestAPIKeyGeneration:
    """Test API key generation."""
    
    def test_generate_key_length(self):
        """Test that generated keys have correct length."""
        key = generate_api_key()
        
        assert len(key) == 32
        assert key.startswith("gw_")
    
    def test_generate_key_uniqueness(self):
        """Test that generated keys are unique."""
        keys = [generate_api_key() for _ in range(100)]
        
        # All keys should be unique
        assert len(keys) == len(set(keys))
    
    def test_generate_key_format(self):
        """Test that generated keys have correct format."""
        key = generate_api_key()
        
        # Should start with 'gw_' prefix
        assert key.startswith("gw_")
        # Should only contain alphanumeric characters and underscore
        assert all(c.isalnum() or c == "_" for c in key)


class TestAPIKeyHashing:
    """Test API key hashing."""
    
    def test_hash_api_key(self):
        """Test that API keys are hashed correctly."""
        key = "gw_test_key_12345678901234567890"
        hashed = hash_api_key(key)
        
        # Hash should be different from original
        assert hashed != key
        # Hash should be consistent
        assert hash_api_key(key) == hashed
    
    def test_hash_different_keys(self):
        """Test that different keys produce different hashes."""
        key1 = "gw_key1_12345678901234567890123"
        key2 = "gw_key2_12345678901234567890123"
        
        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)
        
        assert hash1 != hash2
    
    def test_verify_api_key(self):
        """Test API key verification."""
        key = "gw_test_key_12345678901234567890"
        hashed = hash_api_key(key)
        
        # Correct key should verify
        assert verify_api_key(key, hashed)
        
        # Wrong key should not verify
        wrong_key = "gw_wrong_key_1234567890123456"
        assert not verify_api_key(wrong_key, hashed)


@pytest.mark.asyncio
class TestAPIKeyManager:
    """Test API Key Manager operations."""
    
    async def test_create_api_key(self, db_session: AsyncSession):
        """Test creating an API key."""
        manager = APIKeyManager(db_session)
        
        result = await manager.create_api_key(
            label="Test Key",
            scopes="read,write",
            expires_in_days=90
        )
        
        assert result["label"] == "Test Key"
        assert result["scopes"] == "read,write"
        assert result["key"] is not None
        assert result["key"].startswith("gw_")
        assert result["expires_at"] is not None
    
    async def test_create_key_with_expiration(self, db_session: AsyncSession):
        """Test creating an API key with expiration."""
        manager = APIKeyManager(db_session)
        
        result = await manager.create_api_key(
            label="Expiring Key",
            expires_in_days=30
        )
        
        # Check that expires_at is approximately 30 days from now
        expires_at = datetime.fromisoformat(result["expires_at"].replace("Z", "+00:00"))
        expected_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Allow 1 minute difference for test execution time
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 60
    
    async def test_list_keys(self, db_session: AsyncSession):
        """Test listing API keys."""
        manager = APIKeyManager(db_session)
        
        # Create some keys
        await manager.create_api_key(label="Key 1")
        await manager.create_api_key(label="Key 2")
        await manager.create_api_key(label="Key 3")
        
        keys = await manager.list_keys()
        
        assert len(keys) == 3
        # Keys should not contain the actual key value
        for key in keys:
            assert key.get("key") is None
            assert "key_preview" in key
    
    async def test_revoke_key(self, db_session: AsyncSession):
        """Test revoking an API key."""
        manager = APIKeyManager(db_session)
        
        # Create a key
        result = await manager.create_api_key(label="Test Key")
        key_id = result["id"]
        
        # Revoke it
        success = await manager.revoke_key(key_id)
        assert success
        
        # Verify it's revoked
        keys = await manager.list_keys()
        revoked_key = next(k for k in keys if k["id"] == key_id)
        assert revoked_key["revoked"] is True
    
    async def test_delete_key(self, db_session: AsyncSession):
        """Test deleting an API key."""
        manager = APIKeyManager(db_session)
        
        # Create a key
        result = await manager.create_api_key(label="Test Key")
        key_id = result["id"]
        
        # Delete it
        success = await manager.delete_key(key_id)
        assert success
        
        # Verify it's deleted
        keys = await manager.list_keys()
        assert not any(k["id"] == key_id for k in keys)
    
    async def test_validate_key(self, db_session: AsyncSession):
        """Test validating an API key."""
        manager = APIKeyManager(db_session)
        
        # Create a key
        result = await manager.create_api_key(label="Test Key")
        plain_key = result["key"]
        
        # Validate it
        api_key = await manager.validate_key(plain_key)
        
        assert api_key is not None
        assert api_key.label == "Test Key"
        assert api_key.revoked is False
    
    async def test_validate_revoked_key(self, db_session: AsyncSession):
        """Test that revoked keys are not validated."""
        manager = APIKeyManager(db_session)
        
        # Create and revoke a key
        result = await manager.create_api_key(label="Test Key")
        plain_key = result["key"]
        await manager.revoke_key(result["id"])
        
        # Try to validate it
        api_key = await manager.validate_key(plain_key)
        
        assert api_key is None
    
    async def test_validate_expired_key(self, db_session: AsyncSession):
        """Test that expired keys are not validated."""
        manager = APIKeyManager(db_session)
        
        # Create a key
        result = await manager.create_api_key(
            label="Expired Key",
            expires_in_days=30
        )
        plain_key = result["key"]
        
        # Manually expire it by updating the database
        from sqlalchemy import update, select
        stmt = update(APIKey).where(
            APIKey.id == result["id"]
        ).values(
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        await db_session.execute(stmt)
        await db_session.commit()
        
        # Try to validate it
        api_key = await manager.validate_key(plain_key)
        
        assert api_key is None
    
    async def test_usage_tracking(self, db_session: AsyncSession):
        """Test that key usage is tracked."""
        manager = APIKeyManager(db_session)
        
        # Create a key
        result = await manager.create_api_key(label="Test Key")
        plain_key = result["key"]
        key_id = result["id"]
        
        # Validate it multiple times
        await manager.validate_key(plain_key)
        await manager.validate_key(plain_key)
        await manager.validate_key(plain_key)
        
        # Check usage count
        keys = await manager.list_keys()
        test_key = next(k for k in keys if k["id"] == key_id)
        
        assert test_key["usage_count"] == 3
        assert test_key["last_used_at"] is not None


class TestAPIKeyScopes:
    """Test API key scopes/permissions."""
    
    @pytest.mark.asyncio
    async def test_key_with_scopes(self, db_session: AsyncSession):
        """Test creating a key with specific scopes."""
        manager = APIKeyManager(db_session)
        
        result = await manager.create_api_key(
            label="Limited Key",
            scopes="read,write"
        )
        
        assert result["scopes"] == "read,write"
    
    @pytest.mark.asyncio
    async def test_key_scope_validation(self, db_session: AsyncSession):
        """Test validating key scopes."""
        # This would be implemented in the authorization middleware
        # For now, we just test that scopes are stored
        manager = APIKeyManager(db_session)
        
        result = await manager.create_api_key(
            label="Read-only Key",
            scopes="read"
        )
        
        plain_key = result["key"]
        api_key = await manager.validate_key(plain_key)
        
        assert api_key.scopes == "read"


# Run tests with: pytest tests/test_api_keys.py -v
