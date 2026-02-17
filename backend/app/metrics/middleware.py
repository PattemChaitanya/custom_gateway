"""Metrics middleware for automatic request tracking."""

import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from app.logging_config import get_logger
from .prometheus import MetricsCollector

logger = get_logger("metrics_middleware")


def register_metrics_middleware(app: FastAPI) -> None:
    """Register metrics middleware with FastAPI app."""
    
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable) -> Response:
        """Middleware to collect metrics for each request."""
        # Increment active connections
        MetricsCollector.increment_active_connections()
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate latency
            latency = time.time() - start_time
            
            # Record metrics
            MetricsCollector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                latency=latency
            )
            
            # Add latency header
            response.headers["X-Response-Time"] = f"{int(latency * 1000)}ms"
            
            return response
            
        except Exception as e:
            # Record error
            latency = time.time() - start_time
            MetricsCollector.record_error(
                endpoint=request.url.path,
                error_type=type(e).__name__
            )
            MetricsCollector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=500,
                latency=latency
            )
            raise
        finally:
            # Decrement active connections
            MetricsCollector.decrement_active_connections()
    
    logger.info("Metrics middleware registered")
