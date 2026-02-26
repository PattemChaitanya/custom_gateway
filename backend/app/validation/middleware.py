"""Validation middleware for automatic input validation."""

import json
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from app.logging_config import get_logger
from .validators import validate_json_structure, BodyValidator
from .sanitizers import sanitize_header_value

logger = get_logger("validation")


class ValidationMiddleware:
    """Middleware for automatic input validation and sanitization."""

    def __init__(
        self,
        app: FastAPI,
        max_body_size: int = 10 * 1024 * 1024,  # 10MB default
        max_json_depth: int = 10,
        validate_headers: bool = True,
    ):
        self.app = app
        self.max_body_size = max_body_size
        self.max_json_depth = max_json_depth
        self.validate_headers = validate_headers

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request through validation middleware."""
        try:
            # Validate headers
            if self.validate_headers:
                await self._validate_request_headers(request)

            # Validate body size for POST/PUT/PATCH
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)

            # Process request
            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=400,
                content={"error": "validation_error", "detail": str(e)}
            )

    async def _validate_request_headers(self, request: Request) -> None:
        """Validate request headers."""
        # Check Content-Length if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_body_size:
                    raise ValueError(
                        f"Request body size {size} exceeds maximum {self.max_body_size}")
            except ValueError as e:
                raise ValueError(f"Invalid Content-Length header: {e}")

        # Sanitize custom headers
        for key, value in request.headers.items():
            if key.lower().startswith('x-'):
                sanitized = sanitize_header_value(value)
                if sanitized != value:
                    logger.warning(f"Header {key} was sanitized")

    async def _validate_request_body(self, request: Request) -> None:
        """Validate request body.

        Uses Content-Length header for size validation to avoid reading
        the full body into memory twice (once here, once by FastAPI).
        Only reads the body when deep JSON structure validation is needed.
        """
        # Fast size check via Content-Length header (no body read required)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_body_size:
                    raise ValueError(
                        f"Request body size {size} exceeds maximum {self.max_body_size}"
                    )
            except ValueError:
                raise

        # Deep JSON structure validation requires reading the body.
        # Starlette caches the body after the first read, so downstream
        # handlers (FastAPI's body parsing) can still access it.
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            body = await request.body()
            # Also enforce size when Content-Length header was missing
            BodyValidator.validate_size(body, self.max_body_size)
            try:
                data = json.loads(body)
                validate_json_structure(data, self.max_json_depth)
            except json.JSONDecodeError:
                pass  # Let FastAPI handle JSON parsing errors
            except Exception as e:
                raise ValueError(f"Invalid JSON structure: {e}")


def register_validation_middleware(
    app: FastAPI,
    max_body_size: int = 10 * 1024 * 1024,
    max_json_depth: int = 10,
    validate_headers: bool = True,
) -> None:
    """Register validation middleware with FastAPI app."""

    # Create the middleware instance ONCE at registration time
    # instead of re-creating it on every incoming request.
    middleware = ValidationMiddleware(
        app,
        max_body_size=max_body_size,
        max_json_depth=max_json_depth,
        validate_headers=validate_headers,
    )

    @app.middleware("http")
    async def validation_middleware_handler(request: Request, call_next: Callable):
        return await middleware(request, call_next)

    logger.info("Validation middleware registered")
