"""Audit logging for sensitive operations."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog
from app.logging_config import get_logger

logger = get_logger("audit")


class AuditLogger:
    """Audit logger for tracking sensitive operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_event(
        self,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """Log an audit event."""
        audit_log = AuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata,
            status=status,
            error_message=error_message,
        )
        
        self.session.add(audit_log)
        await self.session.commit()
        await self.session.refresh(audit_log)
        
        logger.info(
            f"Audit log: {action}",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            status=status,
        )
        
        return audit_log
    
    async def log_api_creation(self, api_id: int, user_id: int, ip_address: str):
        """Log API creation."""
        return await self.log_event(
            action="API_CREATE",
            resource_type="api",
            resource_id=str(api_id),
            user_id=user_id,
            ip_address=ip_address,
        )
    
    async def log_api_deletion(self, api_id: int, user_id: int, ip_address: str):
        """Log API deletion."""
        return await self.log_event(
            action="API_DELETE",
            resource_type="api",
            resource_id=str(api_id),
            user_id=user_id,
            ip_address=ip_address,
        )
    
    async def log_key_creation(self, key_id: int, user_id: int, ip_address: str):
        """Log API key creation."""
        return await self.log_event(
            action="KEY_CREATE",
            resource_type="api_key",
            resource_id=str(key_id),
            user_id=user_id,
            ip_address=ip_address,
        )
    
    async def log_key_revocation(self, key_id: int, user_id: int, ip_address: str):
        """Log API key revocation."""
        return await self.log_event(
            action="KEY_REVOKE",
            resource_type="api_key",
            resource_id=str(key_id),
            user_id=user_id,
            ip_address=ip_address,
        )
    
    async def log_login(self, user_id: int, ip_address: str, user_agent: str = None, success: bool = True):
        """Log login attempt."""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILURE"
        return await self.log_event(
            action=action,
            resource_type="user",
            resource_id=str(user_id),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status="success" if success else "failure",
        )
    
    async def log_permission_change(
        self,
        user_id: int,
        target_user_id: int,
        action: str,
        ip_address: str,
    ):
        """Log permission changes."""
        return await self.log_event(
            action=f"PERMISSION_{action.upper()}",
            resource_type="user",
            resource_id=str(target_user_id),
            user_id=user_id,
            ip_address=ip_address,
        )


async def log_audit_event(
    session: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Convenience function to log audit events."""
    auditor = AuditLogger(session)
    return await auditor.log_event(
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        metadata=metadata,
    )
