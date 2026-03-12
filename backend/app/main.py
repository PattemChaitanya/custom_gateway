from app.load_balancer.pool import BackendPoolManager
from app.load_balancer.health import HealthChecker
from app.control_plane.runtime import restore_state, run_control_loop, snapshot_state
from app.db import get_db_manager
from app.middleware.request_id import register_request_id_middleware
from app.middleware.request_logging import register_request_logging
from app.api.apis import router as apis_router
from app.api.auth import auth_router
from app.api import user
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends
from app.validation.middleware import register_validation_middleware
from app.metrics.middleware import register_metrics_middleware
from app.rate_limiter.middleware import register_rate_limit_middleware
from app.authorizers.middleware import register_authorization_middleware
from app.middleware.audit import register_audit_middleware
from app.gateway.router import router as gateway_router
from app.api.secrets import router as secrets_router
from app.api.keys import router as keys_router
from app.api.connectors import router as connectors_router
from app.api.authorizers import router as authorizers_router
from app.api.admin import router as admin_router
from app.api.audit_logs import router as audit_logs_router
from app.api.mini_cloud import router as mini_cloud_router
import asyncio
from app.metrics.prometheus import metrics_endpoint
from .logging_config import configure_logging, get_logger

# Configure logging before importing modules that may emit startup logs.
configure_logging(level="INFO")
logger = get_logger("gateway")
logger.info("Server starting")


DEFAULT_ENVIRONMENTS = [
    {"name": "Production", "slug": "production",
        "description": "Live production environment"},
    {"name": "Staging", "slug": "staging",
        "description": "Pre-production staging environment"},
    {"name": "Testing", "slug": "testing",
        "description": "QA and testing environment"},
    {"name": "Development", "slug": "development",
        "description": "Local development environment"},
]


async def _seed_default_environments(db_manager):
    """Seed default environments if the table is empty."""
    from app.db.models import Environment
    from sqlalchemy import select

    async for db in db_manager.get_db():
        try:
            result = await db.execute(select(Environment))
            if result.scalars().first() is not None:
                return  # Already seeded

            for env_data in DEFAULT_ENVIRONMENTS:
                env = Environment(**env_data)
                db.add(env)
            await db.flush()
            await db.commit()
            logger.info("Seeded default environments")
        except Exception:
            logger.debug(
                "Environment seeding skipped (table may not exist yet)")
        break


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan handler: initialize database connections and cleanup on shutdown.

    The DatabaseManager will attempt to connect in this order:
    1. AWS PostgreSQL (Primary)
    2. SQLite (Secondary fallback)
    3. In-memory storage (Final fallback)
    """
    # Initialize database manager
    db_manager = get_db_manager()
    control_loop_stop_event = asyncio.Event()
    control_loop_task = None
    health_checker = None
    hc_session = None

    try:
        # Determine echo_sql from environment
        import os
        echo_sql = os.getenv("SQL_ECHO", "False").lower() in (
            "1", "true", "yes")

        # Initialize database connections with timeout to prevent hanging
        logger.info("Initializing database connections...")
        await db_manager.initialize(echo_sql=echo_sql, timeout=15)

        # Log connection status
        conn_info = db_manager.get_connection_info()
        logger.info(
            f"Database initialized: {conn_info['database_type']} "
            f"(primary={conn_info['is_using_primary']}, "
            f"sqlite={conn_info['is_using_sqlite']})"
        )

        # Perform health check
        health = await db_manager.health_check()
        logger.info(
            f"Database health: {health['status']} - {health['message']}")

        # Seed default environments
        try:
            await _seed_default_environments(db_manager)
        except Exception as seed_err:
            logger.warning(f"Failed to seed default environments: {seed_err}")

        # Restore persisted control-plane state when available.
        try:
            restore_info = restore_state()
            logger.info(f"Mini-cloud control-plane restore: {restore_info}")
        except Exception as restore_err:
            logger.warning(
                f"Failed to restore mini-cloud control-plane state: {restore_err}")

        # Start periodic mini-cloud control loop.
        try:
            import os
            interval = float(os.getenv("CONTROL_LOOP_INTERVAL_SECONDS", "5"))
            control_loop_task = asyncio.create_task(
                run_control_loop(control_loop_stop_event,
                                 interval_seconds=interval)
            )
            logger.info(
                f"Mini-cloud control loop started (interval={interval}s)")
        except Exception as ctrl_err:
            logger.warning(
                f"Failed to start mini-cloud control loop: {ctrl_err}")

        # Start periodic backend health checks (PostgreSQL mode only).
        try:
            if db_manager.is_using_primary and db_manager.session_factory:
                hc_session = db_manager.session_factory()
                pool_manager = BackendPoolManager(hc_session)
                health_checker = HealthChecker(pool_manager)
                await health_checker.start_health_checks()
                logger.info("Backend pool health checker started")
        except Exception as hc_err:
            logger.warning(f"Health checker not started: {hc_err}")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        logger.warning("Attempting to use in-memory fallback")
        # Ensure we have at least in-memory database
        try:
            db_manager._initialize_fallback_database()
            logger.info("In-memory fallback initialized successfully")
        except Exception as fallback_error:
            logger.critical(
                f"Failed to initialize any database: {fallback_error}")
            raise

    yield

    # Cleanup on shutdown
    logger.info("Shutting down application")
    try:
        if health_checker:
            await health_checker.stop_health_checks()
        if hc_session:
            await hc_session.close()
        control_loop_stop_event.set()
        if control_loop_task:
            control_loop_task.cancel()
            try:
                await control_loop_task
            except asyncio.CancelledError:
                pass
        snapshot_info = snapshot_state()
        logger.info(f"Mini-cloud control-plane snapshot: {snapshot_info}")
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

# Register middlewares (order matters: Starlette's add_middleware uses insert(0, …)
# so the LAST middleware added becomes the OUTERMOST in the onion.  CORS must be
# added last so it wraps every other middleware and can always inject the
# Access-Control-Allow-* headers — even on error responses.)

register_request_logging(app)  # Request logging with header redaction
register_request_id_middleware(app)  # Request ID propagation for tracing
register_validation_middleware(
    app, max_body_size=10*1024*1024)  # Input validation
register_metrics_middleware(app)  # Metrics collection
register_rate_limit_middleware(
    app, global_limit=1000, global_window=60)  # Rate limiting
register_audit_middleware(app)  # Centralized audit logging (runs after auth)
register_authorization_middleware(app)  # Authorization

# CORS — added last so it is the outermost middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Accept",
                   "Accept-Language", "Content-Language", "X-API-Key"],
    max_age=600,
)

# Include routers

app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(auth_router.router)
app.include_router(apis_router)
app.include_router(keys_router)
app.include_router(connectors_router)
app.include_router(secrets_router)
app.include_router(authorizers_router)
app.include_router(admin_router)
app.include_router(audit_logs_router)
app.include_router(mini_cloud_router)

# Gateway proxy — data plane: /gw/{api_id}/{path}
# Must be registered AFTER management routers so /apis, /api/keys, etc. are not shadowed.
app.include_router(gateway_router)

# Metrics endpoint


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return metrics_endpoint()


@app.get("/metrics/summary", tags=["metrics"])
async def metrics_summary(db: AsyncSession = Depends(get_db)):
    """Aggregated request metrics for the last 7 days (Dashboard chart source)."""
    from app.metrics.storage import MetricsStorage
    storage = MetricsStorage(db)
    return await storage.get_metrics_summary()


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
            "using_sqlite": conn_info["is_using_sqlite"],
        }
    }


# lifespan handler replaces on_event startup to avoid deprecation warnings


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
