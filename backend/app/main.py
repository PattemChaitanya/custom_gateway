from app.metrics.prometheus import metrics_endpoint
from app.api.admin import router as admin_router
from app.api.authorizers import router as authorizers_router
from app.api.connectors import router as connectors_router
from app.api.keys import router as keys_router
from app.authorizers.middleware import register_authorization_middleware
from app.rate_limiter.middleware import register_rate_limit_middleware
from app.metrics.middleware import register_metrics_middleware
from app.validation.middleware import register_validation_middleware
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from app.api import user
from app.api.auth import auth_router
from app.api.apis import router as apis_router
from .logging_config import configure_logging, get_logger
from app.middleware.request_logging import register_request_logging
from app.db import get_db_manager

# structured logging
configure_logging(level="INFO")
logger = get_logger("gateway")
logger.info("Server starting")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan handler: initialize database connections and cleanup on shutdown.

    The DatabaseManager will attempt to connect to AWS PostgreSQL first,
    and automatically fall back to in-memory storage if that fails.
    """
    # Initialize database manager
    db_manager = get_db_manager()

    try:
        # Determine echo_sql from environment
        import os
        echo_sql = os.getenv("SQL_ECHO", "False").lower() in (
            "1", "true", "yes")

        # Initialize database connections (Primary: AWS PostgreSQL, Fallback: In-memory)
        await db_manager.initialize(echo_sql=echo_sql)

        # Log connection status
        conn_info = db_manager.get_connection_info()
        logger.info(
            f"Database initialized: {conn_info['database_type']} "
            f"(primary={conn_info['is_using_primary']})"
        )

        # Perform health check
        health = await db_manager.health_check()
        logger.info(
            f"Database health: {health['status']} - {health['message']}")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        logger.warning("Application will use in-memory fallback")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")
    try:
        await db_manager.shutdown()
        logger.info("Database connections closed gracefully")
    except Exception as e:
        logger.error(f"Error during database shutdown: {e}", exc_info=True)


app = FastAPI(
    title="Gateway Management API",
    description="API for managing gateways and devices",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Prefer explicit origin when allow_credentials=True to avoid
    # browsers rejecting wildcard origins with credentials.
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    # Explicitly allow Authorization and common headers used by the frontend.
    allow_headers=["Authorization", "Content-Type", "Accept",
                   "Accept-Language", "Content-Language", "X-API-Key"],
    max_age=600,
)

# Register middlewares

register_request_logging(app)  # Request logging with header redaction
register_validation_middleware(
    app, max_body_size=10*1024*1024)  # Input validation
register_metrics_middleware(app)  # Metrics collection
register_rate_limit_middleware(
    app, global_limit=1000, global_window=60)  # Rate limiting
register_authorization_middleware(app)  # Authorization

# Include routers

app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(auth_router.router)
app.include_router(apis_router)
app.include_router(keys_router)
app.include_router(connectors_router)
app.include_router(authorizers_router)
app.include_router(admin_router)

# Metrics endpoint


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return metrics_endpoint()


# Ensure error responses include CORS headers when raised (some errors can bypass
# middleware stack depending on where they occur). This handler wraps exceptions
# and always attaches the appropriate CORS headers for known origins.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the exception and return a safe error payload for the client.
    logger.exception("Unhandled exception: %s", str(exc))

    # Build a minimal JSON error response; do not leak internals in production.
    content = {"error": "internal_server_error"}

    # Respect origin if it's an allowed origin; otherwise omit Access-Control-Allow-Origin.
    origin = request.headers.get("origin")
    headers = {}
    if origin in ("http://localhost:3000", "http://localhost:5173"):
        headers["Access-Control-Allow-Origin"] = origin
        # allow credentials when origin is explicit
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(status_code=500, content=content, headers=headers)

# Note: DB schema creation is managed via Alembic migrations.


@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to the Gateway Management API"}


@app.get("/health")
async def health_check():
    """
    Health check endpoint that includes database connection status.

    Returns:
        dict: Health status including database connection information
    """
    db_manager = get_db_manager()
    db_health = await db_manager.health_check()
    conn_info = db_manager.get_connection_info()

    return {
        "status": "healthy",
        "service": "Gateway Management API",
        "version": "1.0.0",
        "database": {
            "status": db_health["status"],
            "type": db_health["database"],
            "message": db_health["message"],
            "using_primary": conn_info["is_using_primary"],
        }
    }


# lifespan handler replaces on_event startup to avoid deprecation warnings


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
