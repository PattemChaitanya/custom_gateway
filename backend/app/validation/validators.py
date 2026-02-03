"""Validators for input validation."""

import re
import json
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field, validator, field_validator
from fastapi import HTTPException, status


# Custom exception for validation errors
class ValidationError(Exception):
    """Custom validation error exception."""
    pass


# Regex patterns for validation
ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
SQL_INJECTION_PATTERNS = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)", re.IGNORECASE),
    re.compile(r"(--|\;|\|{2}|\/\*|\*\/)", re.IGNORECASE),
    re.compile(r"(\bOR\b|\bAND\b).*(\=|LIKE)", re.IGNORECASE),
]
XSS_PATTERNS = [
    re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),  # event handlers
]


def validate_path_param(value: str, param_name: str, max_length: int = 100, pattern: Optional[re.Pattern] = None) -> str:
    """Validate path parameter."""
    if not value:
        raise ValidationError(f"Path parameter '{param_name}' is empty")
    
    # Check for path traversal
    if '../' in value or '.\\' in value:
        raise ValidationError(f"Path parameter '{param_name}' contains invalid characters")
    
    if len(value) > max_length:
        raise ValidationError(f"Path parameter '{param_name}' is too long")
    
    # Check for SQL injection attempts
    for sql_pattern in SQL_INJECTION_PATTERNS:
        if sql_pattern.search(value):
            raise ValidationError(f"Path parameter '{param_name}' contains SQL injection attempt")
    
    # Apply custom pattern if provided
    if pattern and not pattern.match(value):
        raise ValidationError(f"Path parameter '{param_name}' format is invalid")
    
    return value


def validate_query_param(
    value: Any, 
    param_name: str, 
    param_type: Optional[str] = None,
    allowed_values: Optional[List[str]] = None,
    max_length: int = 200
) -> Any:
    """Validate query parameter."""
    if value is None:
        return value
    
    str_value = str(value)
    
    if len(str_value) > max_length:
        raise ValidationError(f"Query parameter '{param_name}' exceeds maximum length of {max_length}")
    
    # Type validation
    if param_type == "integer":
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Query parameter '{param_name}' must be an integer")
    
    elif param_type == "boolean":
        if str_value.lower() in ['true', '1', 'yes']:
            return True
        elif str_value.lower() in ['false', '0', 'no']:
            return False
        else:
            raise ValidationError(f"Query parameter '{param_name}' must be a boolean")
    
    elif param_type == "email":
        if not EMAIL_PATTERN.match(str_value):
            raise ValidationError(f"Query parameter '{param_name}' must be a valid email")
    
    # Check for XSS attempts
    for xss_pattern in XSS_PATTERNS:
        if xss_pattern.search(str_value):
            raise ValidationError(f"Query parameter '{param_name}' contains invalid content")
    
    # Check allowed values
    if allowed_values and str_value not in allowed_values:
        raise ValidationError(f"Query parameter '{param_name}' must be one of: {', '.join(allowed_values)}")
    
    return value


def validate_header(value: str, header_name: str, max_length: int = 1000) -> str:
    """Validate HTTP header."""
    if not value:
        return value
    
    if len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Header '{header_name}' exceeds maximum length of {max_length}"
        )
    
    # Check for header injection
    if '\r' in value or '\n' in value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Header '{header_name}' contains invalid characters"
        )
    
    return value


class PathParamValidator(BaseModel):
    """Path parameter validator."""
    id: int = Field(..., gt=0, description="ID must be positive")
    
    class Config:
        str_strip_whitespace = True


class QueryParamValidator(BaseModel):
    """Query parameter validator."""
    page: int = Field(default=1, ge=1, le=10000, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, max_length=50)
    order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")
    search: Optional[str] = Field(default=None, max_length=200)
    
    class Config:
        str_strip_whitespace = True


class HeaderValidator(BaseModel):
    """HTTP header validator."""
    content_type: Optional[str] = Field(default=None, alias="Content-Type", max_length=100)
    authorization: Optional[str] = Field(default=None, alias="Authorization", max_length=2000)
    x_api_key: Optional[str] = Field(default=None, alias="X-API-Key", max_length=256)
    user_agent: Optional[str] = Field(default=None, alias="User-Agent", max_length=500)
    
    class Config:
        populate_by_name = True


class BodyValidator(BaseModel):
    """Request body size validator."""
    max_size_bytes: int = Field(default=1024 * 1024, description="Maximum body size in bytes (default 1MB)")
    
    @classmethod
    def validate_size(cls, body: bytes, max_size: int = 1024 * 1024) -> None:
        """Validate request body size."""
        if len(body) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request body exceeds maximum size of {max_size} bytes"
            )


def validate_json_structure(data: Dict[str, Any], max_depth: int = 10, current_depth: int = 0) -> None:
    """Validate JSON structure to prevent deeply nested payloads."""
    if current_depth > max_depth:
        raise ValidationError(f"JSON structure is too deep")
    
    if isinstance(data, dict):
        if len(data) > 1000:
            raise ValidationError("JSON object has too many keys (max 1000)")
        for value in data.values():
            if isinstance(value, (dict, list)):
                validate_json_structure(value, max_depth, current_depth + 1)
    elif isinstance(data, list):
        if len(data) > 10000:
            raise ValidationError("JSON array has too many elements (max 10000)")
        for item in data:
            if isinstance(item, (dict, list)):
                validate_json_structure(item, max_depth, current_depth + 1)


def validate_email(email: str) -> str:
    """Validate email format."""
    if not EMAIL_PATTERN.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    return email.lower()


def validate_uuid(uuid_str: str) -> str:
    """Validate UUID format."""
    if not UUID_PATTERN.match(uuid_str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )
    return uuid_str.lower()


def validate_body_size(body: Any, max_size_mb: float = 1.0, max_depth: int = 10) -> None:
    """Validate request body size and structure."""
    # Convert body to JSON string to check size
    if isinstance(body, dict) or isinstance(body, list):
        body_str = json.dumps(body)
        body_bytes = len(body_str.encode('utf-8'))
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        
        if body_bytes > max_size_bytes:
            raise ValidationError(f"Request body is too large")
        
        # Check depth
        validate_json_structure(body, max_depth)
    elif isinstance(body, bytes):
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        if len(body) > max_size_bytes:
            raise ValidationError(f"Request body is too large")
    elif isinstance(body, str):
        body_bytes = len(body.encode('utf-8'))
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        if body_bytes > max_size_bytes:
            raise ValidationError(f"Request body is too large")
