"""Secret injection for the gateway pipeline.

Resolves ``${secret:<name>}`` placeholders in connector configurations and
returns the resolved values so the gateway can inject them as upstream headers.

Placeholder syntax (case-insensitive secret name):
    ${secret:my_secret_name}

Typical connector ``config`` shape that benefits from injection::

    {
        "headers": {
            "Authorization": "Bearer ${secret:upstream_api_token}",
            "X-Client-ID":   "${secret:client_id}"
        },
        "target_url": "https://api.example.com/${secret:tenant_slug}/v1"
    }

The injector resolves placeholders by:
1. Scanning the connector configs attached to the API.
2. For every unique secret name found, fetching & decrypting the secret once
   (N secrets → N DB queries, cached in a local dict for the request).
3. Returning:
   - ``resolved_headers`` — a dict ready to merge into the upstream request headers.
   - ``resolved_target_url`` — a string (or ``None``) when the first connector's
     ``target_url`` key contains a placeholder.

Security notes:
- Decrypted secret values are held **only in memory** for the duration of the
  request; they are never logged.
- Placeholder names are validated against a strict pattern to prevent injection.
"""

import re
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger

logger = get_logger("gateway.secret_injector")

# Pattern: ${secret:<name>}  — name must be alphanumeric + _ + - only.
_PLACEHOLDER_RE = re.compile(r"\$\{secret:([a-zA-Z0-9_\-]+)\}", re.IGNORECASE)


def _find_secret_names(value: Any) -> set[str]:
    """Recursively walk *value* (str / dict / list) and collect all secret names."""
    names: set[str] = set()
    if isinstance(value, str):
        names.update(m.group(1) for m in _PLACEHOLDER_RE.finditer(value))
    elif isinstance(value, dict):
        for v in value.values():
            names.update(_find_secret_names(v))
    elif isinstance(value, list):
        for item in value:
            names.update(_find_secret_names(item))
    return names


def _substitute(value: Any, secrets: Dict[str, str]) -> Any:
    """Recursively replace ``${secret:<name>}`` with the resolved secret value."""
    if isinstance(value, str):
        def _replace(m: re.Match) -> str:
            name = m.group(1)
            resolved = secrets.get(name)
            if resolved is None:
                # Leave the placeholder intact and warn — do NOT raise so the
                # pipeline can still forward the request (upstream decides what
                # to do with an unresolved header value).
                logger.warning(
                    "Secret '%s' not found — placeholder left unresolved", name
                )
                return m.group(0)
            return resolved
        return _PLACEHOLDER_RE.sub(_replace, value)
    elif isinstance(value, dict):
        return {k: _substitute(v, secrets) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute(item, secrets) for item in value]
    return value


async def _load_secrets(names: set[str], db: AsyncSession) -> Dict[str, str]:
    """Fetch and decrypt secrets from the database. Returns name → plaintext dict."""
    if not names:
        return {}

    from app.security.secrets import SecretsManager
    mgr = SecretsManager(db)
    result: Dict[str, str] = {}

    for name in names:
        try:
            secret = await mgr.get_secret(name, decrypt=True)
            if secret is not None:
                # SecretsManager returns an object with `.value` being the
                # decrypted text when decrypt=True.
                plaintext = getattr(secret, "value", None)
                if plaintext and plaintext != "***ENCRYPTED***":
                    result[name] = plaintext
        except Exception as exc:
            logger.error(
                "Failed to load secret '%s' for injection: %s", name, exc
            )

    return result


async def inject_connector_secrets(
    api,
    db: AsyncSession,
) -> Tuple[Dict[str, str], Optional[str]]:
    """Resolve secret placeholders in the first HTTP connector attached to *api*.

    Returns a tuple of:
    - ``extra_headers`` — dict of header-name → resolved value, ready to merge
      into the upstream request.
    - ``override_url``  — resolved ``target_url`` string (or ``None``) from the
      connector config if one was specified.

    If the API has no connectors, or none of the connector configs contain
    secret placeholders, both values are empty / None.
    """
    if not api.connectors:
        return {}, None

    # Use the first connector (matching the gateway pipeline's single-config model)
    connector = api.connectors[0]
    config: Dict[str, Any] = connector.config or {}

    # --- Collect all secret names used in this connector's config -----------
    all_names = _find_secret_names(config)
    if not all_names:
        # Fast path — no placeholders at all
        resolved_headers: Dict[str, str] = {}
        resolved_url: Optional[str] = None
        # Still expose plain (non-secret) headers from config
        raw_headers = config.get("headers", {})
        if isinstance(raw_headers, dict):
            resolved_headers = {k: str(v) for k, v in raw_headers.items()}
        raw_url = config.get("target_url")
        if isinstance(raw_url, str):
            resolved_url = raw_url
        return resolved_headers, resolved_url

    # --- Load secrets from DB (single pass) ----------------------------------
    secrets = await _load_secrets(all_names, db)

    # --- Substitute placeholders in the headers sub-dict --------------------
    raw_headers = config.get("headers", {})
    resolved_headers = {}
    if isinstance(raw_headers, dict):
        resolved_raw = _substitute(raw_headers, secrets)
        resolved_headers = {k: str(v) for k, v in resolved_raw.items()}

    # --- Substitute in target_url if present --------------------------------
    resolved_url: Optional[str] = None
    raw_url = config.get("target_url")
    if isinstance(raw_url, str):
        resolved_url = _substitute(raw_url, secrets)

    if resolved_headers:
        logger.debug(
            "Injecting %d connector header(s) for API %s (connector=%s)",
            len(resolved_headers),
            api.id,
            connector.name,
        )

    return resolved_headers, resolved_url
