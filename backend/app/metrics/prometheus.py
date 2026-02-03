"""Prometheus metrics collection."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from typing import Optional
from app.logging_config import get_logger

logger = get_logger("metrics")


# Define Prometheus metrics
request_counter = Counter(
    'gateway_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

request_latency = Histogram(
    'gateway_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

error_counter = Counter(
    'gateway_errors_total',
    'Total errors',
    ['endpoint', 'error_type']
)

active_connections = Gauge(
    'gateway_active_connections',
    'Number of active connections'
)


class MetricsCollector:
    """Centralized metrics collector."""
    
    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, latency: float):
        """Record an HTTP request."""
        try:
            request_counter.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            request_latency.labels(
                method=method,
                endpoint=endpoint
            ).observe(latency)
            
            if status_code >= 400:
                error_counter.labels(
                    endpoint=endpoint,
                    error_type=f"http_{status_code}"
                ).inc()
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
    
    @staticmethod
    def record_error(endpoint: str, error_type: str):
        """Record an error."""
        try:
            error_counter.labels(
                endpoint=endpoint,
                error_type=error_type
            ).inc()
        except Exception as e:
            logger.error(f"Failed to record error metric: {e}")
    
    @staticmethod
    def increment_active_connections():
        """Increment active connections."""
        try:
            active_connections.inc()
        except Exception as e:
            logger.error(f"Failed to increment active connections: {e}")
    
    @staticmethod
    def decrement_active_connections():
        """Decrement active connections."""
        try:
            active_connections.dec()
        except Exception as e:
            logger.error(f"Failed to decrement active connections: {e}")


def metrics_endpoint() -> Response:
    """Endpoint to expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
