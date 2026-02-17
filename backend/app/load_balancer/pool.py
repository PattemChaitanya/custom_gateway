"""Backend pool management."""

from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import BackendPool
from app.logging_config import get_logger
from .algorithms import create_load_balancer

logger = get_logger("backend_pool")


class BackendPoolManager:
    """Manager for backend pools and load balancing."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.pools_cache = {}  # Cache load balancers
    
    async def create_pool(
        self,
        name: str,
        backends: List[Dict[str, Any]],
        algorithm: str = "round_robin",
        api_id: Optional[int] = None,
        health_check_url: Optional[str] = None,
        health_check_interval: int = 30,
    ) -> BackendPool:
        """Create a new backend pool."""
        pool = BackendPool(
            name=name,
            api_id=api_id,
            algorithm=algorithm,
            backends=backends,
            health_check_url=health_check_url,
            health_check_interval=health_check_interval,
        )
        
        self.session.add(pool)
        await self.session.commit()
        await self.session.refresh(pool)
        
        # Initialize load balancer
        self.pools_cache[pool.id] = create_load_balancer(algorithm, backends)
        
        logger.info(f"Created backend pool: {name} with {len(backends)} backends")
        return pool
    
    async def get_pool(self, pool_id: int) -> Optional[BackendPool]:
        """Get a backend pool by ID."""
        result = await self.session.execute(
            select(BackendPool).where(BackendPool.id == pool_id)
        )
        return result.scalar_one_or_none()
    
    async def get_pool_by_name(self, name: str) -> Optional[BackendPool]:
        """Get a backend pool by name."""
        result = await self.session.execute(
            select(BackendPool).where(BackendPool.name == name)
        )
        return result.scalar_one_or_none()
    
    async def list_pools(self, api_id: Optional[int] = None) -> List[BackendPool]:
        """List all backend pools."""
        query = select(BackendPool)
        if api_id:
            query = query.where(BackendPool.api_id == api_id)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_pool(
        self,
        pool_id: int,
        **kwargs
    ) -> Optional[BackendPool]:
        """Update a backend pool."""
        pool = await self.get_pool(pool_id)
        
        if not pool:
            return None
        
        for key, value in kwargs.items():
            if hasattr(pool, key) and value is not None:
                setattr(pool, key, value)
        
        await self.session.commit()
        await self.session.refresh(pool)
        
        # Recreate load balancer if backends or algorithm changed
        if "backends" in kwargs or "algorithm" in kwargs:
            self.pools_cache[pool.id] = create_load_balancer(
                pool.algorithm,
                pool.backends
            )
        
        logger.info(f"Updated backend pool: {pool_id}")
        return pool
    
    async def delete_pool(self, pool_id: int) -> bool:
        """Delete a backend pool."""
        pool = await self.get_pool(pool_id)
        
        if not pool:
            return False
        
        await self.session.delete(pool)
        await self.session.commit()
        
        # Remove from cache
        if pool_id in self.pools_cache:
            del self.pools_cache[pool_id]
        
        logger.info(f"Deleted backend pool: {pool_id}")
        return True
    
    def get_load_balancer(self, pool_id: int, pool: BackendPool):
        """Get or create load balancer for a pool."""
        if pool_id not in self.pools_cache:
            self.pools_cache[pool_id] = create_load_balancer(
                pool.algorithm,
                pool.backends
            )
        return self.pools_cache[pool_id]
    
    async def select_backend(self, pool_id: int) -> Optional[str]:
        """Select a backend from a pool."""
        pool = await self.get_pool(pool_id)
        
        if not pool:
            logger.error(f"Pool {pool_id} not found")
            return None
        
        lb = self.get_load_balancer(pool_id, pool)
        backend = lb.select_backend()
        
        if not backend:
            logger.warning(f"No healthy backend available in pool {pool_id}")
            return None
        
        return backend.url
    
    async def mark_backend_health(
        self,
        pool_id: int,
        backend_url: str,
        healthy: bool
    ):
        """Mark a backend as healthy or unhealthy."""
        pool = await self.get_pool(pool_id)
        
        if not pool:
            return
        
        lb = self.get_load_balancer(pool_id, pool)
        lb.mark_backend_healthy(backend_url, healthy)
