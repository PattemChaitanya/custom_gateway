"""Rate limit middleware."""

from typing import Callable
from fastapi import FastAPI, Request, Response, HTTPException, status
from app.logging_config import get_logger
from .algorithms import FixedWindowRateLimiter
from .manager import RateLimitManager

logger = get_logger("rate_limit_middleware")


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int, limit: int, remaining: int = 0):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests",
                "limit": limit,
                "remaining": remaining,
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)}
        )


def register_rate_limit_middleware(
    app: FastAPI,
    global_limit: int = 1000,
    global_window: int = 60,
    algorithm: str = "fixed_window",
) -> None:
    """Register rate limit middleware with FastAPI app.
    
    Args:
        app: FastAPI application
        global_limit: Global rate limit (requests per window)
        global_window: Time window in seconds
        algorithm: Rate limiting algorithm ('fixed_window', 'sliding_window', 'token_bucket')
    """
    
    # Initialize rate limiter based on algorithm
    if algorithm == "sliding_window":
        from .algorithms import SlidingWindowRateLimiter
        limiter = SlidingWindowRateLimiter()
    elif algorithm == "token_bucket":
        from .algorithms import TokenBucketRateLimiter
        limiter = TokenBucketRateLimiter()
    else:
        limiter = FixedWindowRateLimiter()
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
        """Middleware to enforce rate limits."""
        # Skip rate limiting for metrics and health check endpoints
        if request.url.path in ["/metrics", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Determine rate limit key (can be IP, user, API key, etc.)
        client_ip = request.client.host if request.client else "unknown"
        
        # Try to get user-specific key from headers
        api_key = request.headers.get("X-API-Key")
        user_id = request.state.__dict__.get("user_id")  # Set by auth middleware
        
        if user_id:
            key = f"user:{user_id}"
        elif api_key:
            key = f"apikey:{api_key[:16]}"  # Use prefix of API key
        else:
            key = f"ip:{client_ip}"
        
        # Check rate limit
        try:
            allowed, info = await limiter.is_allowed(key, global_limit, global_window)
            
            if not allowed:
                retry_after = info.get("reset", 0) - int(__import__("time").time())
                logger.warning(
                    f"Rate limit exceeded for {key}",
                    key=key,
                    limit=global_limit,
                    window=global_window
                )
                raise RateLimitExceeded(
                    retry_after=max(1, retry_after),
                    limit=info["limit"],
                    remaining=info["remaining"]
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])
            
            return response
            
        except RateLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Fail open - allow request if rate limiting fails
            return await call_next(request)
    
    logger.info(f"Rate limit middleware registered: {global_limit} req/{global_window}s ({algorithm})")
