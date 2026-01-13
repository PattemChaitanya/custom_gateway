from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
import os
import logging
from app.api import user

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("streaming_backend")
# logger = logging.getLogger(__name__)

logger.info("Server starting...")

app = FastAPI(
    title="Gateway Management API",
    description="API for managing gateways and devices",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)

app.include_router(user.router, prefix="/user", tags=["user"])


@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to the Gateway Management API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
