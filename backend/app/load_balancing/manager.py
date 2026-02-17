"""Load balancer manager compatibility layer.

Provides `LoadBalancerManager` used by existing tests. Operates on the
`LoadBalancer` and `Backend` models defined in `app.db.models`.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import LoadBalancer, Backend
from app.logging_config import get_logger

logger = get_logger("load_balancer_manager")


class LoadBalancerManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_load_balancer(self, api_id: int, algorithm: str = "round_robin") -> LoadBalancer:
        lb = LoadBalancer(api_id=api_id, algorithm=algorithm)
        self.session.add(lb)
        await self.session.commit()
        await self.session.refresh(lb)
        logger.info(f"Created load balancer {lb.id} for api {api_id}")
        return lb

    async def add_backend(self, load_balancer_id: int, url: str, weight: int = 1) -> Backend:
        backend = Backend(load_balancer_id=load_balancer_id,
                          url=url, weight=weight)
        self.session.add(backend)
        await self.session.commit()
        await self.session.refresh(backend)
        logger.info(
            f"Added backend {backend.id} to load balancer {load_balancer_id}")
        return backend

    async def get_load_balancer(self, lb_id: int) -> Optional[LoadBalancer]:
        res = await self.session.execute(select(LoadBalancer).where(LoadBalancer.id == lb_id))
        return res.scalars().first()

    async def get_backend(self, backend_id: int) -> Optional[Backend]:
        res = await self.session.execute(select(Backend).where(Backend.id == backend_id))
        return res.scalars().first()
