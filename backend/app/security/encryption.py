"""Encryption utilities for secure data storage."""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
from app.logging_config import get_logger

logger = get_logger("encryption")


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode('utf-8')


def get_encryption_key_from_env() -> bytes:
    """Get encryption key from environment or generate a new one."""
    key_str = os.getenv("ENCRYPTION_KEY")
    
    if not key_str:
        logger.warning("ENCRYPTION_KEY not set in environment. Using derived key from SECRET_KEY.")
        # Derive key from SECRET_KEY if available
        secret_key = os.getenv("SECRET_KEY", "default-secret-change-in-production")
        salt = os.getenv("ENCRYPTION_SALT", "default-salt").encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return key
    
    return key_str.encode()


def encrypt_data(data: str, key: Optional[bytes] = None) -> str:
    """Encrypt data using Fernet symmetric encryption.
    
    Args:
        data: Plain text data to encrypt
        key: Optional encryption key (uses env key if not provided)
    
    Returns:
        Base64 encoded encrypted data
    """
    if not data:
        return data
    
    if key is None:
        key = get_encryption_key_from_env()
    
    try:
        fernet = Fernet(key)
        encrypted = fernet.encrypt(data.encode())
        return encrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise ValueError(f"Failed to encrypt data: {e}")


def decrypt_data(encrypted_data: str, key: Optional[bytes] = None) -> str:
    """Decrypt data using Fernet symmetric encryption.
    
    Args:
        encrypted_data: Base64 encoded encrypted data
        key: Optional encryption key (uses env key if not provided)
    
    Returns:
        Decrypted plain text data
    """
    if not encrypted_data:
        return encrypted_data
    
    if key is None:
        key = get_encryption_key_from_env()
    
    try:
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise ValueError(f"Failed to decrypt data: {e}")


def encrypt_dict(data: dict, key: Optional[bytes] = None) -> str:
    """Encrypt a dictionary by converting to JSON string first."""
    import json
    json_str = json.dumps(data)
    return encrypt_data(json_str, key)


def decrypt_dict(encrypted_data: str, key: Optional[bytes] = None) -> dict:
    """Decrypt and parse dictionary from encrypted JSON string."""
    import json
    decrypted = decrypt_data(encrypted_data, key)
    return json.loads(decrypted)


# Alias for tests
def get_encryption_key() -> bytes:
    """Get the encryption key. Alias for get_encryption_key_from_env()."""
    return get_encryption_key_from_env()
