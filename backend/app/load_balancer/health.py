"""Health checker for backend servers."""

import asyncio
import httpx
from typing import Dict, Any
from app.logging_config import get_logger
from .pool import BackendPoolManager

logger = get_logger("health_checker")


class HealthChecker:
    """Periodic health checker for backend servers."""
    
    def __init__(self, pool_manager: BackendPoolManager):
        self.pool_manager = pool_manager
        self.running = False
        self.tasks = {}
    
    async def check_backend_health(self, url: str, health_check_url: str = "/health") -> bool:
        """Check if a backend is healthy."""
        try:
            # Construct full health check URL
            if health_check_url.startswith("http"):
                check_url = health_check_url
            else:
                check_url = f"{url.rstrip('/')}{health_check_url}"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(check_url)
                healthy = response.status_code == 200
                
                if not healthy:
                    logger.warning(f"Backend {url} health check failed: {response.status_code}")
                
                return healthy
        except Exception as e:
            logger.error(f"Backend {url} health check error: {e}")
            return False
    
    async def check_pool_health(self, pool_id: int):
        """Check health of all backends in a pool."""
        pool = await self.pool_manager.get_pool(pool_id)
        
        if not pool or not pool.backends:
            return
        
        for backend in pool.backends:
            url = backend.get("url")
            if not url:
                continue
            
            health_check_url = pool.health_check_url or "/health"
            healthy = await self.check_backend_health(url, health_check_url)
            
            # Update backend health
            await self.pool_manager.mark_backend_health(pool_id, url, healthy)
    
    async def run_health_checks(self, pool_id: int, interval: int):
        """Run periodic health checks for a pool."""
        logger.info(f"Starting health checks for pool {pool_id} every {interval}s")
        
        while self.running:
            try:
                await self.check_pool_health(pool_id)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error for pool {pool_id}: {e}")
                await asyncio.sleep(interval)
    
    async def start_health_checks(self):
        """Start health checks for all pools."""
        self.running = True
        pools = await self.pool_manager.list_pools()
        
        for pool in pools:
            if pool.health_check_url:
                task = asyncio.create_task(
                    self.run_health_checks(pool.id, pool.health_check_interval)
                )
                self.tasks[pool.id] = task
        
        logger.info(f"Started health checks for {len(self.tasks)} pools")
    
    async def stop_health_checks(self):
        """Stop all health checks."""
        self.running = False
        
        for task in self.tasks.values():
            task.cancel()
        
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()
        
        logger.info("Stopped all health checks")
