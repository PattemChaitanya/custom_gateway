"""Compatibility shim for app.rate_limiting package name.

Re-export items from `app.rate_limiter` to support older imports.
"""
from app.rate_limiter import (
    FixedWindowRateLimiter,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
)
from app.rate_limiter.manager import RateLimitManager

# Provide the `limiter` and `strategies` modules expected by older tests
from . import limiter as limiter
from . import strategies as strategies

__all__ = [
    "FixedWindowRateLimiter",
    "SlidingWindowRateLimiter",
    "TokenBucketRateLimiter",
    "RateLimitManager",
    "limiter",
    "strategies",
]
