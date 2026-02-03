"""Sanitization utilities for user input."""

import re
import html
import json
from typing import Any, Dict, Optional
import unicodedata


def sanitize_html(text: str) -> str:
    """Sanitize HTML content to prevent XSS attacks."""
    if not text:
        return text
    
    # Remove potentially dangerous patterns BEFORE escaping
    dangerous_patterns = [
        (r'<script[^>]*>.*?</script>', ''),
        (r'javascript:', ''),
        (r'on\w+\s*=\s*["\']?[^"\'>\s]*["\']?', ''),  # Event handlers
        (r'<iframe[^>]*>.*?</iframe>', ''),
        (r'<object[^>]*>.*?</object>', ''),
        (r'<embed[^>]*>', ''),
        (r'<applet[^>]*>.*?</applet>', ''),
        (r'alert\s*\(.*?\)', ''),  # Remove alert() calls
    ]
    
    for pattern, replacement in dangerous_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.DOTALL)
    
    # Escape HTML entities
    text = html.escape(text)
    
    return text


def sanitize_sql(text: str) -> str:
    """Sanitize input to prevent SQL injection."""
    if not text:
        return text
    
    # Remove SQL comments
    text = re.sub(r'--.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    
    # Remove dangerous SQL keywords
    dangerous_patterns = [
        (r'\bOR\b', ''),  # Remove OR
        (r'\bAND\b', ''),  # Remove AND
        (r'\bUNION\b', ''),  # Remove UNION
        (r'\bSELECT\b', ''),  # Remove SELECT
        (r'\bDROP\b', ''),  # Remove DROP
        (r'\bDELETE\b', ''),  # Remove DELETE
        (r'\bINSERT\b', ''),  # Remove INSERT
        (r'\bUPDATE\b', ''),  # Remove UPDATE
        (r'\bTRUNCATE\b', ''),  # Remove TRUNCATE
        (r'\bEXEC(UTE)?\b', ''),  # Remove EXEC/EXECUTE
        (r"'", ''),  # Remove single quotes
        (r';', ''),  # Remove semicolons
    ]
    
    for pattern, replacement in dangerous_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text


def sanitize_nosql(text: str) -> str:
    """Sanitize input to prevent NoSQL injection."""
    if not text:
        return text
    
    # Remove MongoDB operators
    dangerous_patterns = [
        r'\$where',
        r'\$regex',
        r'\$ne',
        r'\$gt',
        r'\$gte',
        r'\$lt',
        r'\$lte',
        r'\$in',
        r'\$nin',
        r'\$and',
        r'\$or',
        r'\$not',
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text


def sanitize_string(
    text: str,
    max_length: Optional[int] = None,
    allow_unicode: bool = True,
    strip_whitespace: bool = True
) -> str:
    """General string sanitization."""
    if not text:
        return text
    
    # Strip whitespace
    if strip_whitespace:
        text = text.strip()
    
    # Normalize unicode
    if allow_unicode:
        text = unicodedata.normalize('NFKC', text)
    else:
        # Remove non-ASCII characters
        text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Remove control characters except common ones (tab, newline, carriage return)
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\t\n\r')
    
    # Truncate to max length
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def sanitize_json(data: Any, max_depth: int = 10, current_depth: int = 0) -> Any:
    """Recursively sanitize JSON data."""
    if current_depth > max_depth:
        return None
    
    if isinstance(data, str):
        return sanitize_string(data, max_length=10000)
    elif isinstance(data, dict):
        return {
            sanitize_string(str(k), max_length=100): sanitize_json(v, max_depth, current_depth + 1)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_json(item, max_depth, current_depth + 1) for item in data[:1000]]  # Limit array size
    else:
        return data


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal."""
    if not filename:
        return filename
    
    # Remove directory separators
    filename = filename.replace('/', '').replace('\\', '').replace('..', '')
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Keep only safe characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename


def sanitize_url(url: str) -> str:
    """Sanitize URL to prevent injection attacks."""
    if not url:
        return url
    
    # Remove dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
    url_lower = url.lower()
    
    for protocol in dangerous_protocols:
        if url_lower.startswith(protocol):
            return ''
    
    # Only allow http, https, and relative URLs
    if not (url.startswith('http://') or url.startswith('https://') or url.startswith('/')):
        return ''
    
    return url


def sanitize_api_key(key: str) -> str:
    """Sanitize API key format."""
    if not key:
        return key
    
    # Remove whitespace
    key = key.strip()
    
    # Ensure only alphanumeric and allowed special characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', key):
        return ''
    
    # Enforce length limits
    if len(key) < 16 or len(key) > 256:
        return ''
    
    return key


def sanitize_header_value(value: str) -> str:
    """Sanitize HTTP header value to prevent header injection."""
    if not value:
        return value
    
    # Remove newlines and carriage returns
    value = value.replace('\r', '').replace('\n', '')
    
    # Limit length
    if len(value) > 8000:
        value = value[:8000]
    
    return value
