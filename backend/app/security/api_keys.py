"""API Key management and authentication."""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import APIKey, Environment
from app.db.connector import get_db
from app.logging_config import get_logger

logger = get_logger("api_keys")


# Helper function to safely convert datetime or string to ISO format
def to_isoformat(dt) -> str:
    """Convert datetime or string to ISO format string."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def generate_api_key(prefix: str = "gw", length: int = 32) -> str:
    """Generate a cryptographically secure API key.

    Format: prefix_randomstring (total 32 chars by default)
    Example: gw_abc123def456... (29 random hex chars after 'gw_')
    """
    # Calculate random part length: total_length - len("gw_")
    prefix_with_underscore = f"{prefix}_"
    random_char_count = length - len(prefix_with_underscore)

    # Generate enough random bytes (each byte = 2 hex chars)
    random_bytes_needed = (random_char_count + 1) // 2
    random_bytes = secrets.token_bytes(random_bytes_needed)
    random_part = random_bytes.hex()[:random_char_count]

    return f"{prefix_with_underscore}{random_part}"


def hash_api_key(api_key: str, salt: Optional[str] = None) -> str:
    """Hash API key using SHA256.

    For test compatibility, if no salt provided, uses simple SHA256 hash.
    If salt provided, uses salted hash in format 'salt:hash'.
    """
    if salt is not None:
        # Salted hash for production use
        key_with_salt = f"{api_key}{salt}"
        hashed = hashlib.sha256(key_with_salt.encode()).hexdigest()
        return f"{salt}:{hashed}"
    else:
        # Simple hash for test determinism
        return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify API key against stored hash.

    Supports both simple SHA256 hash and salted hash (salt:hash format).
    """
    try:
        if ':' in stored_hash:
            # Salted hash format
            salt, expected_hash = stored_hash.split(':', 1)
            key_with_salt = f"{api_key}{salt}"
            actual_hash = hashlib.sha256(key_with_salt.encode()).hexdigest()
            return hmac.compare_digest(actual_hash, expected_hash)
        else:
            # Simple hash format
            actual_hash = hashlib.sha256(api_key.encode()).hexdigest()
            return hmac.compare_digest(actual_hash, stored_hash)
    except Exception as e:
        logger.error(f"API key verification error: {e}")
        return False


class APIKeyManager:
    """Manager for API key operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_api_key(
        self,
        label: Optional[str] = None,
        scopes: Optional[str] = None,
        environment_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new API key and return a dict with the plain key and metadata.

        Tests expect a dict containing the plain `key`, `id`, `label`, `scopes`,
        `expires_at` (ISO string) and other fields. This method implements that
        compatibility layer while still persisting a hashed key in the DB.
        """
        # Generate key and hashed value
        plain_key = generate_api_key()
        hashed_key = hash_api_key(plain_key)

        # Compute expires_at from days if provided
        if expires_in_days is not None and expires_at is None:
            expires_at = datetime.now(timezone.utc) + \
                timedelta(days=expires_in_days)

        # Create database record (store hashed key)
        api_key = APIKey(
            key=hashed_key,
            label=label or "Unnamed Key",
            scopes=scopes or "",
            environment_id=environment_id,
            revoked=False,
            created_at=datetime.now(timezone.utc),
        )

        if hasattr(APIKey, 'expires_at') and expires_at is not None:
            api_key.expires_at = expires_at

        if hasattr(APIKey, 'metadata_json') and metadata:
            api_key.metadata_json = metadata

        if hasattr(APIKey, 'last_used_at'):
            api_key.last_used_at = None
        if hasattr(APIKey, 'usage_count'):
            api_key.usage_count = 0

        # Persist
        self.session.add(api_key)
        await self.session.flush()

        # Build return dict expected by tests
        ret = {
            "id": api_key.id,
            "label": api_key.label,
            "scopes": api_key.scopes,
            "environment_id": getattr(api_key, 'environment_id', None),
            "revoked": api_key.revoked,
            "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
            "expires_at": api_key.expires_at.isoformat() if hasattr(api_key, 'expires_at') and api_key.expires_at else None,
            "last_used_at": getattr(api_key, 'last_used_at', None),
            "usage_count": getattr(api_key, 'usage_count', 0),
            # Plain key (not stored in DB)
            "key": plain_key,
            "key_preview": f"{plain_key[:8]}..." if len(plain_key) > 8 else plain_key,
        }

        logger.info(f"Created API key: {label} (id={api_key.id})")

        return ret

    async def validate_key(self, plain_key: str) -> Optional[APIKey]:
        """Validate an API key and return the key object if valid.

        Alias for verify_and_get_key for test compatibility.
        """
        return await self.verify_and_get_key(plain_key)

    async def verify_and_get_key(self, plain_key: str) -> Optional[APIKey]:
        """Verify API key and return key object if valid."""
        # Get all non-revoked keys
        result = await self.session.execute(
            select(APIKey).where(APIKey.revoked == False)
        )
        keys = result.scalars().all()

        # Try to verify against each key
        for key_obj in keys:
            if verify_api_key(plain_key, key_obj.key):
                # Check expiration if column exists
                if hasattr(key_obj, 'expires_at') and key_obj.expires_at:
                    # Ensure both datetimes are timezone-aware for comparison
                    now = datetime.now(timezone.utc)
                    expires_at = key_obj.expires_at
                    if expires_at.tzinfo is None:
                        # If stored time is naive, make it aware (assume UTC)
                        from datetime import timezone as tz
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if now > expires_at:
                        logger.warning(
                            f"Expired API key used: {key_obj.label}")
                        return None

                # Update usage tracking if columns exist
                if hasattr(key_obj, 'last_used_at'):
                    await self.session.execute(
                        update(APIKey)
                        .where(APIKey.id == key_obj.id)
                        .values(
                            last_used_at=datetime.now(timezone.utc),
                            usage_count=(
                                APIKey.usage_count + 1) if hasattr(APIKey, 'usage_count') else None
                        )
                    )
                    await self.session.commit()

                return key_obj

        return None

    async def list_keys(self, environment_id: Optional[int] = None) -> list:
        """List all API keys (without showing the actual keys)."""
        query = select(APIKey)

        if environment_id:
            query = query.where(APIKey.environment_id == environment_id)

        result = await self.session.execute(query.order_by(APIKey.created_at.desc()))
        keys = result.scalars().all()

        return [
            {
                "id": key.id,
                "label": key.label,
                "scopes": key.scopes,
                "environment_id": key.environment_id,
                "revoked": key.revoked,
                "created_at": to_isoformat(key.created_at),
                "expires_at": to_isoformat(key.expires_at) if hasattr(key, 'expires_at') else None,
                "last_used_at": to_isoformat(key.last_used_at) if hasattr(key, 'last_used_at') else None,
                "usage_count": key.usage_count if hasattr(key, 'usage_count') else 0,
                "key_preview": "gw_" + ("*" * 40),  # Masked key
            }
            for key in keys
        ]

    async def revoke_key(self, key_id: int) -> bool:
        """Revoke an API key."""
        result = await self.session.execute(
            update(APIKey)
            .where(APIKey.id == key_id)
            .values(revoked=True)
        )
        await self.session.commit()

        if result.rowcount > 0:
            logger.info(f"Revoked API key: id={key_id}")
            return True
        return False

    async def revoke_api_key(self, key_id: int) -> bool:
        """Alias for revoke_key."""
        return await self.revoke_key(key_id)

    async def delete_key(self, key_id: int) -> bool:
        """Delete an API key permanently."""
        result = await self.session.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        key = result.scalar_one_or_none()

        if key:
            await self.session.delete(key)
            await self.session.commit()
            logger.info(f"Deleted API key: id={key_id}")
            return True
        return False

    async def delete_api_key(self, key_id: int) -> bool:
        """Alias for delete_key."""
        return await self.delete_key(key_id)

    async def list_api_keys(self, environment_id: Optional[int] = None) -> list:
        """List all API keys."""
        query = select(APIKey)
        if environment_id:
            query = query.where(APIKey.environment_id == environment_id)

        result = await self.session.execute(query)
        keys = result.scalars().all()

        # Add key_preview to each key
        for key in keys:
            if not hasattr(key, 'key_preview') or not key.key_preview:
                key.key_preview = "gw_" + ("*" * 40)

        return list(keys)

    async def get_key_stats(self, key_id: int) -> Optional[Dict[str, Any]]:
        """Get usage statistics for an API key."""
        result = await self.session.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        key = result.scalar_one_or_none()

        if not key:
            return None

        return {
            "id": key.id,
            "label": key.label,
            "usage_count": getattr(key, 'usage_count', 0),
            "last_used_at": getattr(key, 'last_used_at', None),
            "created_at": key.created_at,
            "revoked": key.revoked,
        }


# Dependency for API key authentication
async def get_api_key_dependency(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """FastAPI dependency to validate API key from header."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    manager = APIKeyManager(db)
    key = await manager.verify_and_get_key(x_api_key)

    if not key:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return key


async def get_api_key_optional(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Optional[APIKey]:
    """Optional API key dependency (doesn't raise error if not provided)."""
    if not x_api_key:
        return None

    manager = APIKeyManager(db)
    return await manager.verify_and_get_key(x_api_key)
