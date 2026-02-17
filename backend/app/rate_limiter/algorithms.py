"""Rate limiting algorithms."""

import time
from typing import Optional
import redis.asyncio as redis
import os
from app.logging_config import get_logger

logger = get_logger("rate_limiter")


def get_redis_client() -> redis.Redis:
    """Get Redis client for rate limiting."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        # Try a quick ping to detect obvious connection issues early.
        # Do not await here (sync ping) because redis.asyncio's ping is coroutine;
        # we'll rely on runtime errors during operations and handle them gracefully.
        return client
    except Exception as e:
        logger.warning(f"Redis client unavailable for rate limiter: {e}")
        return None


class FixedWindowRateLimiter:
    """Fixed window rate limiting algorithm."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or get_redis_client()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, dict]:
        """Check if request is allowed under rate limit.

        Returns:
            (allowed: bool, info: dict)
        """
        try:
            # If redis client is not available, fail-open with explanatory info
            if not self.redis:
                current_time = int(time.time())
                return True, {
                    "limit": limit,
                    "remaining": limit,
                    "reset": current_time + window_seconds,
                    "error": "redis_unavailable",
                    "algorithm": "fixed_window",
                }
            current_window = int(time.time() / window_seconds)
            redis_key = f"rate_limit:fixed:{key}:{current_window}"

            # Increment counter
            count = await self.redis.incr(redis_key)

            # Set expiration on first request
            if count == 1:
                await self.redis.expire(redis_key, window_seconds)

            allowed = count <= limit
            remaining = max(0, limit - count)
            reset_time = (current_window + 1) * window_seconds

            return allowed, {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "algorithm": "fixed_window"
            }
        except Exception as e:
            logger.debug(f"Rate limit error (falling back): {e}")
            current_time = int(time.time())
            return True, {
                "limit": limit,
                "remaining": limit,
                "reset": current_time + window_seconds,
                "error": str(e),
                "algorithm": "fixed_window",
            }


class SlidingWindowRateLimiter:
    """Sliding window log rate limiting algorithm."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or get_redis_client()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, dict]:
        """Check if request is allowed under rate limit."""
        try:
            now = time.time()
            redis_key = f"rate_limit:sliding:{key}"

            # Remove old entries
            await self.redis.zremrangebyscore(redis_key, 0, now - window_seconds)

            # Count current requests
            count = await self.redis.zcard(redis_key)

            if count < limit:
                # Add new request
                await self.redis.zadd(redis_key, {str(now): now})
                await self.redis.expire(redis_key, window_seconds)
                allowed = True
                remaining = limit - count - 1
            else:
                allowed = False
                remaining = 0

            return allowed, {
                "limit": limit,
                "remaining": remaining,
                "reset": int(now + window_seconds),
                "algorithm": "sliding_window"
            }
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            current_time = int(time.time())
            return True, {
                "limit": limit,
                "remaining": limit,
                "reset": current_time + window_seconds,
                "error": str(e)
            }


class TokenBucketRateLimiter:
    """Token bucket rate limiting algorithm."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or get_redis_client()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, dict]:
        """Check if request is allowed under rate limit.

        Token bucket refills at rate of limit/window_seconds tokens per second.
        """
        try:
            now = time.time()
            redis_key = f"rate_limit:token:{key}"

            # Get current state
            state = await self.redis.hgetall(redis_key)

            if state:
                tokens = float(state.get("tokens", limit))
                last_update = float(state.get("last_update", now))
            else:
                tokens = float(limit)
                last_update = now

            # Calculate tokens to add based on time elapsed
            time_elapsed = now - last_update
            refill_rate = limit / window_seconds
            tokens_to_add = time_elapsed * refill_rate
            tokens = min(limit, tokens + tokens_to_add)

            if tokens >= 1:
                # Consume one token
                tokens -= 1
                await self.redis.hset(redis_key, mapping={
                    "tokens": str(tokens),
                    "last_update": str(now)
                })
                await self.redis.expire(redis_key, window_seconds * 2)
                allowed = True
                remaining = int(tokens)
            else:
                allowed = False
                remaining = 0

            return allowed, {
                "limit": limit,
                "remaining": remaining,
                "reset": int(now + (1 - tokens) / refill_rate) if tokens < 1 else int(now),
                "algorithm": "token_bucket"
            }
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            current_time = int(time.time())
            return True, {
                "limit": limit,
                "remaining": limit,
                "reset": current_time + window_seconds,
                "error": str(e)
            }
