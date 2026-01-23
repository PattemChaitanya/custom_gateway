from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.api import user
from app.api.auth import auth_router
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
        await init_db()
        logger.info("Database initialized from AWS env vars (lifespan)")
    except RuntimeError as e:
        logger.info("Skipping AWS DB init (lifespan): %s", str(e))

    yield


app = FastAPI(
    title="Gateway Management API",
    description="API for managing gateways and devices",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)

# register request logging middleware (redacts Authorization header)
register_request_logging(app)

app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(auth_router.router)

# Note: DB schema creation is managed via Alembic migrations.

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to the Gateway Management API"}


# lifespan handler replaces on_event startup to avoid deprecation warnings


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
