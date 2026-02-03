"""Secrets management with encryption."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.logging_config import get_logger
from .encryption import encrypt_data, decrypt_data

logger = get_logger("secrets")


class SecretsManager:
    """Manager for encrypted secrets storage."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def store_secret(
        self,
        name: Optional[str] = None,
        value: str = None,
        description: Optional[str] = None,
        tags: Optional[str] = None,
        key: Optional[str] = None,  # Alias for 'name' parameter
    ) -> Dict[str, Any]:
        """Store a secret with encryption."""
        from app.db.models import Secret
        
        # Support 'key' as alias for 'name'
        if key is not None:
            name = key
        if name is None:
            raise ValueError("Either 'name' or 'key' parameter must be provided")
        
        # Convert tags list to comma-separated string if needed
        if isinstance(tags, list):
            tags = ",".join(tags)
        
        # Encrypt the value
        encrypted_value = encrypt_data(value)
        
        # Check if secret already exists
        result = await self.session.execute(
            select(Secret).where(Secret.name == name)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing secret
            existing.value = encrypted_value
            existing.description = description
            existing.tags = tags
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(existing)
            
            logger.info(f"Updated secret: {name}")
            # Create response object with 'key' attribute for compatibility
            class SecretResponse:
                def __init__(self, secret):
                    self.id = secret.id
                    self.name = secret.name
                    self.key = secret.name  # Alias
                    self.encrypted_value = secret.value
                    self.description = secret.description
                    # Convert tags string to list if it's a comma-separated string
                    if isinstance(secret.tags, str) and secret.tags:
                        self.tags = [t.strip() for t in secret.tags.split(',')]
                    elif secret.tags:
                        self.tags = secret.tags
                    else:
                        self.tags = []
                    self.created_at = secret.created_at
                    self.updated_at = secret.updated_at
            
            return SecretResponse(existing)
        else:
            # Create new secret
            secret = Secret(
                name=name,
                value=encrypted_value,
                description=description,
                tags=tags,
                created_at=datetime.now(timezone.utc),
            )
            
            self.session.add(secret)
            await self.session.commit()
            await self.session.refresh(secret)
            
            logger.info(f"Created secret: {name}")
            # Create response object with 'key' attribute for compatibility
            class SecretResponse:
                def __init__(self, secret):
                    self.id = secret.id
                    self.name = secret.name
                    self.key = secret.name  # Alias
                    self.encrypted_value = secret.value
                    self.description = secret.description
                    # Convert tags string to list if it's a comma-separated string
                    if isinstance(secret.tags, str) and secret.tags:
                        self.tags = [t.strip() for t in secret.tags.split(',')]
                    elif secret.tags:
                        self.tags = secret.tags
                    else:
                        self.tags = []
                    self.created_at = secret.created_at
                    self.updated_at = secret.updated_at
            
            return SecretResponse(secret)
    
    async def get_secret(self, name: str, decrypt: bool = True) -> Optional[Dict[str, Any]]:
        """Retrieve a secret by name."""
        from app.db.models import Secret
        
        result = await self.session.execute(
            select(Secret).where(Secret.name == name)
        )
        secret = result.scalar_one_or_none()
        
        if not secret:
            return None
        
        value = secret.value
        decrypted_value = None
        if decrypt and value:
            try:
                decrypted_value = decrypt_data(value)
            except Exception as e:
                logger.error(f"Failed to decrypt secret {name}: {e}")
        
        # Create response object with both .key and .name attributes
        class SecretDetail:
            def __init__(self, secret, decrypted_val=None, is_decrypted=False):
                self.id = secret.id
                self.name = secret.name
                self.key = secret.name  # Alias
                self.value = decrypted_val if is_decrypted else "***ENCRYPTED***"
                # Only include decrypted_value if decrypt was True
                if is_decrypted:
                    self.decrypted_value = decrypted_val
                self.encrypted_value = secret.value
                self.description = secret.description
                self.tags = secret.tags
                self.created_at = secret.created_at
                self.updated_at = secret.updated_at
        
        return SecretDetail(secret, decrypted_value, decrypt)
    
    async def list_secrets(self, tags: Optional[str] = None) -> list:
        """List all secrets (without decrypted values)."""
        from app.db.models import Secret
        
        query = select(Secret)
        
        if tags:
            query = query.where(Secret.tags.contains(tags))
        
        result = await self.session.execute(query.order_by(Secret.created_at.desc()))
        secrets = result.scalars().all()
        
        # Create response objects with 'key' attribute for compatibility
        class SecretListItem:
            def __init__(self, secret):
                self.id = secret.id
                self.name = secret.name
                self.key = secret.name  # Alias
                self.description = secret.description
                self.tags = secret.tags
                self.created_at = secret.created_at
                self.updated_at = secret.updated_at
        
        return [SecretListItem(secret) for secret in secrets]
    
    async def delete_secret(self, name: str) -> bool:
        """Delete a secret permanently."""
        from app.db.models import Secret
        
        result = await self.session.execute(
            select(Secret).where(Secret.name == name)
        )
        secret = result.scalar_one_or_none()
        
        if secret:
            await self.session.delete(secret)
            await self.session.commit()
            logger.info(f"Deleted secret: {name}")
            return True
        return False
    
    async def rotate_secret(self, name: str, new_value: str) -> Dict[str, Any]:
        """Rotate a secret with a new value."""
        # This is essentially an update, but logs it as a rotation
        result = await self.store_secret(name, new_value)
        logger.info(f"Rotated secret: {name}")
        return result


def encrypt_secret(value: str) -> str:
    """Standalone function to encrypt a secret."""
    return encrypt_data(value)


def decrypt_secret(encrypted_value: str) -> str:
    """Standalone function to decrypt a secret."""
    return decrypt_data(encrypted_value)
