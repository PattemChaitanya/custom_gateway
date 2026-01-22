import time
from typing import Callable
from fastapi import FastAPI, Request
from app.logging_config import get_logger

logger = get_logger("http")


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable):
        start = time.time()
        # capture basic request metadata
        method = request.method
        path = request.url.path
        query = str(request.url.query)
        client = request.client.host if request.client else None

        # redact Authorization header if present
        headers = dict(request.headers)
        if "authorization" in headers:
            headers["authorization"] = "REDACTED"

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.time() - start) * 1000)
            logger.info(
                "http.request",
                method=method,
                path=path,
                query=query,
                client=client,
                status_code=500,
                duration_ms=duration_ms,
            )
            raise
        else:
            duration_ms = int((time.time() - start) * 1000)
            logger.info(
                "http.request",
                method=method,
                path=path,
                query=query,
                client=client,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
