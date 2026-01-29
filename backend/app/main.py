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
from app.db.connector import init_engine_from_aws_env, init_db

# structured logging
configure_logging(level="INFO")
logger = get_logger("gateway")
logger.info("Server starting")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: initialize DB from AWS env vars (optional) and create tables.

    Falls back silently if AWS env vars are not present.
    """
    try:
        init_engine_from_aws_env()
        # If AWS env vars are present, reinitialize engine from them before creating tables
        await init_db()
        logger.info("Database initialized from AWS env vars (lifespan)")
    except RuntimeError as e:
        logger.info("Skipping AWS engine init (lifespan): %s", str(e))
        # Even when AWS env vars are missing, ensure local DB tables exist (create_all)
        try:
            await init_db()
            logger.info("Database initialized (lifespan) via metadata.create_all")
        except Exception as ee:
            logger.warning("Failed to initialize DB in lifespan: %s", str(ee))

    yield


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
    allow_headers=["Authorization", "Content-Type", "Accept", "Accept-Language", "Content-Language"],
    max_age=600,
)

# register request logging middleware (redacts Authorization header)
register_request_logging(app)

app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(auth_router.router)
app.include_router(apis_router)


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


# lifespan handler replaces on_event startup to avoid deprecation warnings


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
