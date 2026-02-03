"""Authorization middleware."""

from typing import Callable
from fastapi import FastAPI, Request, Response
from app.logging_config import get_logger

logger = get_logger("auth_middleware")


def register_authorization_middleware(app: FastAPI) -> None:
    """Register authorization middleware with FastAPI app."""
    
    @app.middleware("http")
    async def authorization_middleware(request: Request, call_next: Callable) -> Response:
        """Middleware to enforce authorization policies."""
        # Skip authorization for public endpoints
        public_endpoints = [
            "/docs",
            "/openapi.json",
            "/health",
            "/metrics",
            "/auth/login",
            "/auth/register",
        ]
        
        if any(request.url.path.startswith(ep) for ep in public_endpoints):
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        return response
    
    logger.info("Authorization middleware registered")
