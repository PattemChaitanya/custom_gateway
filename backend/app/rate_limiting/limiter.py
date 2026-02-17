"""RateLimiter shim providing DB-backed limit CRUD used by tests."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import RateLimit
from app.db.session_utils import resolve_session


class RateLimiter:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _sess(self):
        s = await resolve_session(self.session)
        return s

    async def create_limit(self, api_id: int, max_requests: int, window_seconds: int, strategy: str = "fixed_window"):
        s = await self._sess()
        rl = RateLimit(api_id=api_id, limit=max_requests,
                       window_seconds=window_seconds, name=strategy)
        s.add(rl)
        await s.commit()
        await s.refresh(rl)
        # provide `max_requests` attribute expected by tests
        setattr(rl, "max_requests", rl.limit)
        setattr(rl, "strategy", strategy)
        return rl

    async def get_limit(self, api_id: int) -> Optional[RateLimit]:
        s = await self._sess()
        res = await s.execute(select(RateLimit).where(RateLimit.api_id == api_id))
        rl = res.scalars().first()
        if rl:
            setattr(rl, "max_requests", rl.limit)
        return rl

    async def update_limit(self, api_id: int, max_requests: Optional[int] = None, window_seconds: Optional[int] = None):
        s = await self._sess()
        res = await s.execute(select(RateLimit).where(RateLimit.api_id == api_id))
        rl = res.scalars().first()
        if not rl:
            return None
        if max_requests is not None:
            rl.limit = max_requests
        if window_seconds is not None:
            rl.window_seconds = window_seconds
        await s.commit()
        await s.refresh(rl)
        setattr(rl, "max_requests", rl.limit)
        return rl

    async def delete_limit(self, api_id: int) -> bool:
        s = await self._sess()
        res = await s.execute(select(RateLimit).where(RateLimit.api_id == api_id))
        rl = res.scalars().first()
        if not rl:
            return False
        await s.delete(rl)
        await s.commit()
        return True
