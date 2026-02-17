"""Rate limit management and configuration."""

from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import RateLimit
from app.logging_config import get_logger

logger = get_logger("rate_limit_manager")


class RateLimitManager:
    """Manager for rate limit configurations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_rate_limit(
        self,
        api_id: int,
        name: str,
        key_type: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimit:
        """Create a new rate limit configuration."""
        rate_limit = RateLimit(
            api_id=api_id,
            name=name,
            key_type=key_type,
            limit=limit,
            window_seconds=window_seconds,
        )
        
        self.session.add(rate_limit)
        await self.session.commit()
        await self.session.refresh(rate_limit)
        
        logger.info(f"Created rate limit: {name} for API {api_id}")
        return rate_limit
    
    async def get_rate_limits_for_api(self, api_id: int) -> List[RateLimit]:
        """Get all rate limits for an API."""
        result = await self.session.execute(
            select(RateLimit).where(RateLimit.api_id == api_id)
        )
        return result.scalars().all()
    
    async def get_rate_limit(self, limit_id: int) -> Optional[RateLimit]:
        """Get a specific rate limit by ID."""
        result = await self.session.execute(
            select(RateLimit).where(RateLimit.id == limit_id)
        )
        return result.scalar_one_or_none()
    
    async def update_rate_limit(
        self,
        limit_id: int,
        **kwargs
    ) -> Optional[RateLimit]:
        """Update a rate limit configuration."""
        rate_limit = await self.get_rate_limit(limit_id)
        
        if not rate_limit:
            return None
        
        for key, value in kwargs.items():
            if hasattr(rate_limit, key) and value is not None:
                setattr(rate_limit, key, value)
        
        await self.session.commit()
        await self.session.refresh(rate_limit)
        
        logger.info(f"Updated rate limit: {limit_id}")
        return rate_limit
    
    async def delete_rate_limit(self, limit_id: int) -> bool:
        """Delete a rate limit configuration."""
        rate_limit = await self.get_rate_limit(limit_id)
        
        if not rate_limit:
            return False
        
        await self.session.delete(rate_limit)
        await self.session.commit()
        
        logger.info(f"Deleted rate limit: {limit_id}")
        return True
