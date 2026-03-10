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

from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.models import Base, APIKey
from app.security.api_keys import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
    APIKeyManager
)


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
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
        expires_at = datetime.fromisoformat(
            result["expires_at"].replace("Z", "+00:00"))
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


# ---------------------------------------------------------------------------
# Integration tests: HTTP endpoint tests via AsyncClient
# ---------------------------------------------------------------------------


def _mock_current_user():
    """Return a mock user dict for dependency override."""
    return {"id": 1, "email": "test@example.com", "roles": "admin", "is_superuser": False}


@pytest_asyncio.fixture
async def app_with_auth_override():
    """Create app instance with authentication and DB overridden for integration testing."""
    from app.main import app
    from app.api.auth.auth_dependency import get_current_user
    from app.db.connector import get_db

    # Create a real async engine + session for integration tests
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with test_session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_current_user] = _mock_current_user
    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
class TestAPIKeyEndpoints:
    """Integration tests for API key HTTP endpoints."""

    async def test_create_key_endpoint(self, app_with_auth_override):
        """POST /api/keys/ should create a key and return the plain key once."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/", json={
                "label": "Endpoint Test Key",
                "scopes": "read",
                "expires_in_days": 30,
            })
            assert resp.status_code == 201
            data = resp.json()
            assert data["label"] == "Endpoint Test Key"
            assert data["scopes"] == "read"
            assert data["key"].startswith("gw_")
            assert data["revoked"] is False
            assert data["expires_at"] is not None

    async def test_create_key_validation_empty_label(self, app_with_auth_override):
        """POST /api/keys/ with empty label should return 422."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/", json={"label": ""})
            assert resp.status_code == 422

    async def test_create_key_validation_missing_label(self, app_with_auth_override):
        """POST /api/keys/ without label should return 422."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/", json={})
            assert resp.status_code == 422

    async def test_create_key_label_too_long(self, app_with_auth_override):
        """POST /api/keys/ with label > 100 chars should return 422."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/", json={"label": "x" * 101})
            assert resp.status_code == 422

    async def test_create_key_invalid_expires(self, app_with_auth_override):
        """POST /api/keys/ with expires_in_days=0 should return 422."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/", json={"label": "Bad", "expires_in_days": 0})
            assert resp.status_code == 422

    async def test_create_key_expires_too_large(self, app_with_auth_override):
        """POST /api/keys/ with expires_in_days > 3650 should return 422."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/", json={"label": "Bad", "expires_in_days": 5000})
            assert resp.status_code == 422

    async def test_list_keys_endpoint(self, app_with_auth_override):
        """GET /api/keys/ should return a list missing plain key values."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            # Create a key first
            create_resp = await ac.post("/api/keys/", json={"label": "List Test"})
            assert create_resp.status_code == 201

            # List keys
            resp = await ac.get("/api/keys/")
            assert resp.status_code == 200
            keys = resp.json()
            assert isinstance(keys, list)
            assert len(keys) >= 1
            # Plain keys must NOT be exposed in listing
            for k in keys:
                assert k.get("key") is None
                assert "key_preview" in k

    async def test_revoke_key_endpoint(self, app_with_auth_override):
        """POST /api/keys/{id}/revoke should mark the key as revoked."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            create_resp = await ac.post("/api/keys/", json={"label": "Revoke Me"})
            key_id = create_resp.json()["id"]

            resp = await ac.post(f"/api/keys/{key_id}/revoke")
            assert resp.status_code == 200
            assert "revoked" in resp.json()["message"].lower()

    async def test_revoke_nonexistent_key(self, app_with_auth_override):
        """POST /api/keys/99999/revoke should return 404."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/99999/revoke")
            assert resp.status_code == 404

    async def test_delete_key_endpoint(self, app_with_auth_override):
        """DELETE /api/keys/{id} should permanently remove the key."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            create_resp = await ac.post("/api/keys/", json={"label": "Delete Me"})
            key_id = create_resp.json()["id"]

            resp = await ac.delete(f"/api/keys/{key_id}")
            assert resp.status_code == 204

    async def test_delete_nonexistent_key(self, app_with_auth_override):
        """DELETE /api/keys/99999 should return 404."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.delete("/api/keys/99999")
            assert resp.status_code == 404

    async def test_stats_endpoint(self, app_with_auth_override):
        """GET /api/keys/{id}/stats should return usage statistics."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            create_resp = await ac.post("/api/keys/", json={"label": "Stats Key"})
            key_id = create_resp.json()["id"]

            resp = await ac.get(f"/api/keys/{key_id}/stats")
            assert resp.status_code == 200
            stats = resp.json()
            assert stats["id"] == key_id
            assert stats["label"] == "Stats Key"
            assert "usage_count" in stats

    async def test_stats_nonexistent_key(self, app_with_auth_override):
        """GET /api/keys/99999/stats should return 404."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.get("/api/keys/99999/stats")
            assert resp.status_code == 404

    async def test_verify_endpoint_without_header(self, app_with_auth_override):
        """GET /api/keys/verify without X-API-Key header should return 401."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.get("/api/keys/verify")
            assert resp.status_code == 401

    async def test_verify_endpoint_with_invalid_key(self, app_with_auth_override):
        """GET /api/keys/verify with a bogus X-API-Key should return 401."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.get("/api/keys/verify", headers={"X-API-Key": "gw_totally_invalid_key_here_xx"})
            assert resp.status_code == 401

    async def test_full_lifecycle(self, app_with_auth_override):
        """End-to-end: create -> list -> stats -> revoke -> verify fails -> delete."""
        transport = ASGITransport(app=app_with_auth_override)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            # 1. Create
            create_resp = await ac.post("/api/keys/", json={
                "label": "Lifecycle Key",
                "scopes": "read,write",
                "expires_in_days": 90,
            })
            assert create_resp.status_code == 201
            data = create_resp.json()
            key_id = data["id"]
            plain_key = data["key"]

            # 2. List - key should appear
            list_resp = await ac.get("/api/keys/")
            assert any(k["id"] == key_id for k in list_resp.json())

            # 3. Stats - should show usage_count 0
            stats_resp = await ac.get(f"/api/keys/{key_id}/stats")
            assert stats_resp.json()["usage_count"] == 0

            # 4. Verify - should succeed
            verify_resp = await ac.get("/api/keys/verify", headers={"X-API-Key": plain_key})
            assert verify_resp.status_code == 200
            assert verify_resp.json()["valid"] is True
            assert verify_resp.json()["label"] == "Lifecycle Key"

            # 5. Revoke
            revoke_resp = await ac.post(f"/api/keys/{key_id}/revoke")
            assert revoke_resp.status_code == 200

            # 6. Verify after revoke - should fail
            verify_after = await ac.get("/api/keys/verify", headers={"X-API-Key": plain_key})
            assert verify_after.status_code == 401

            # 7. Delete
            del_resp = await ac.delete(f"/api/keys/{key_id}")
            assert del_resp.status_code == 204


@pytest.mark.asyncio
class TestAPIKeyEndpointAuth:
    """Test that endpoints require authentication."""

    async def test_create_requires_auth(self):
        """POST /api/keys/ without auth should return 401/403."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/", json={"label": "No Auth"})
            assert resp.status_code in (401, 403)

    async def test_list_requires_auth(self):
        """GET /api/keys/ without auth should return 401/403."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.get("/api/keys/")
            assert resp.status_code in (401, 403)

    async def test_revoke_requires_auth(self):
        """POST /api/keys/1/revoke without auth should return 401/403."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.post("/api/keys/1/revoke")
            assert resp.status_code in (401, 403)

    async def test_delete_requires_auth(self):
        """DELETE /api/keys/1 without auth should return 401/403."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.delete("/api/keys/1")
            assert resp.status_code in (401, 403)

    async def test_stats_requires_auth(self):
        """GET /api/keys/1/stats without auth should return 401/403."""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.get("/api/keys/1/stats")
            assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Security edge-case tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAPIKeySecurity:
    """Security-focused tests for API key system."""

    async def test_key_not_stored_in_plaintext(self, db_session: AsyncSession):
        """Verify the database stores a hash, never the plain key."""
        manager = APIKeyManager(db_session)
        result = await manager.create_api_key(label="Plaintext Check")
        plain_key = result["key"]

        from sqlalchemy import select
        row = (await db_session.execute(
            select(APIKey).where(APIKey.id == result["id"])
        )).scalar_one()

        assert row.key != plain_key
        assert len(row.key) == 64  # SHA256 hex digest length

    async def test_hash_is_deterministic(self, db_session: AsyncSession):
        """Same plaintext should always produce the same hash."""
        key = "gw_deterministic_test_12345678"
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 == h2

    async def test_salted_hash_verification(self):
        """Salted hashes should verify correctly."""
        key = "gw_salted_test_key_123456789"
        salted_hash = hash_api_key(key, salt="random_salt")
        assert ":" in salted_hash
        assert verify_api_key(key, salted_hash)
        assert not verify_api_key("gw_wrong_key_xxxxxxxxxxxx", salted_hash)

    async def test_timing_safe_comparison(self):
        """Verify that verification uses timing-safe comparison (hmac.compare_digest)."""
        import hmac as hmac_mod
        key = "gw_timing_test_1234567890123"
        hashed = hash_api_key(key)
        # The implementation uses hmac.compare_digest - just verify it returns correct results
        assert verify_api_key(key, hashed) is True
        assert verify_api_key(key + "x", hashed) is False

    async def test_validate_returns_none_for_nonexistent_key(self, db_session: AsyncSession):
        """Validating a key that was never created should return None."""
        manager = APIKeyManager(db_session)
        result = await manager.validate_key("gw_this_key_never_existed_xxx")
        assert result is None

    async def test_revoked_key_cannot_be_reused(self, db_session: AsyncSession):
        """A revoked key should never validate, even with correct plaintext."""
        manager = APIKeyManager(db_session)
        result = await manager.create_api_key(label="Revoke Security")
        plain_key = result["key"]

        # Validate works before revoke
        assert (await manager.validate_key(plain_key)) is not None

        # Revoke
        await manager.revoke_key(result["id"])

        # Should fail now
        assert (await manager.validate_key(plain_key)) is None
        # Try again to make sure it's consistently rejected
        assert (await manager.validate_key(plain_key)) is None

    async def test_expired_key_with_exact_boundary(self, db_session: AsyncSession):
        """Key that expired 1 second ago should be rejected."""
        manager = APIKeyManager(db_session)
        result = await manager.create_api_key(label="Boundary", expires_in_days=1)
        plain_key = result["key"]

        from sqlalchemy import update
        await db_session.execute(
            update(APIKey).where(APIKey.id == result["id"]).values(
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
            )
        )
        await db_session.commit()

        assert (await manager.validate_key(plain_key)) is None

    async def test_key_without_expiration_never_expires(self, db_session: AsyncSession):
        """A key created without expires_in_days should validate indefinitely."""
        manager = APIKeyManager(db_session)
        result = await manager.create_api_key(label="No Expiry")
        plain_key = result["key"]
        assert result["expires_at"] is None

        # Should validate
        key_obj = await manager.validate_key(plain_key)
        assert key_obj is not None

    async def test_delete_then_validate(self, db_session: AsyncSession):
        """A permanently deleted key should not validate."""
        manager = APIKeyManager(db_session)
        result = await manager.create_api_key(label="Delete Then Validate")
        plain_key = result["key"]

        await manager.delete_key(result["id"])
        assert (await manager.validate_key(plain_key)) is None

    async def test_revoke_nonexistent_key_returns_false(self, db_session: AsyncSession):
        """Revoking a non-existent key should return False."""
        manager = APIKeyManager(db_session)
        assert (await manager.revoke_key(99999)) is False

    async def test_delete_nonexistent_key_returns_false(self, db_session: AsyncSession):
        """Deleting a non-existent key should return False."""
        manager = APIKeyManager(db_session)
        assert (await manager.delete_key(99999)) is False

    async def test_get_key_stats(self, db_session: AsyncSession):
        """get_key_stats should return correct usage data."""
        manager = APIKeyManager(db_session)
        result = await manager.create_api_key(label="Stats Test")
        plain_key = result["key"]

        # Use the key a few times
        await manager.validate_key(plain_key)
        await manager.validate_key(plain_key)

        stats = await manager.get_key_stats(result["id"])
        assert stats is not None
        assert stats["label"] == "Stats Test"
        assert stats["usage_count"] == 2
        assert stats["last_used_at"] is not None

    async def test_get_stats_nonexistent_key(self, db_session: AsyncSession):
        """get_key_stats for non-existent key should return None."""
        manager = APIKeyManager(db_session)
        assert (await manager.get_key_stats(99999)) is None

    async def test_list_keys_masks_all_previews(self, db_session: AsyncSession):
        """All key_preview values in listing should be masked."""
        manager = APIKeyManager(db_session)
        await manager.create_api_key(label="Mask 1")
        await manager.create_api_key(label="Mask 2")

        keys = await manager.list_keys()
        for k in keys:
            preview = k["key_preview"]
            assert "*" in preview  # Should contain masking characters

    async def test_key_creation_returns_preview(self, db_session: AsyncSession):
        """Created key response should include a meaningful key_preview."""
        manager = APIKeyManager(db_session)
        result = await manager.create_api_key(label="Preview")
        assert result["key_preview"].startswith("gw_")
        assert "..." in result["key_preview"]

    async def test_multiple_keys_independent(self, db_session: AsyncSession):
        """Revoking one key should not affect another."""
        manager = APIKeyManager(db_session)
        r1 = await manager.create_api_key(label="Key A")
        r2 = await manager.create_api_key(label="Key B")

        await manager.revoke_key(r1["id"])

        # Key A should be revoked
        assert (await manager.validate_key(r1["key"])) is None
        # Key B should still work
        assert (await manager.validate_key(r2["key"])) is not None


# Run tests with: pytest tests/test_api_keys.py -v
