"""Versioned external policy configuration loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RoutePolicy(BaseModel):
    path_prefix: str
    service: str
    strategy: str = "round_robin"
    auth_policy: str
    rate_limit_policy: str


class AuthPolicyConfig(BaseModel):
    name: str
    mode: str
    scopes: List[str] = Field(default_factory=list)


class RateLimitPolicyConfig(BaseModel):
    name: str
    limit: int
    window_seconds: int


class PolicyConfig(BaseModel):
    version: str
    routes: List[RoutePolicy] = Field(default_factory=list)
    auth: Dict[str, AuthPolicyConfig] = Field(default_factory=dict)
    rate_limits: Dict[str, RateLimitPolicyConfig] = Field(default_factory=dict)


def match_route_policy(config: PolicyConfig, service: str, path: str) -> Optional[RoutePolicy]:
    candidates = [r for r in config.routes if r.service ==
                  service and path.startswith(r.path_prefix)]
    if not candidates:
        return None
    # Longest prefix wins to support nested route policies.
    return sorted(candidates, key=lambda r: len(r.path_prefix), reverse=True)[0]


def _default_config_path() -> Path:
    # backend/app/control_plane/policies.py -> backend/config/policies.v1.json
    return Path(__file__).resolve().parents[2] / "config" / "policies.v1.json"


def load_policy_config(path: str | None = None) -> PolicyConfig:
    target = Path(path) if path else _default_config_path()
    with target.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return PolicyConfig.model_validate(payload)


def validate_policy_config(config: PolicyConfig) -> List[str]:
    """Return a list of cross-reference validation errors.

    Checks that every ``auth_policy`` and ``rate_limit_policy`` name
    referenced in a route actually exists in the corresponding lookup
    tables.  An empty list means the config is internally consistent.
    """
    errors: List[str] = []
    for route in config.routes:
        if route.auth_policy not in config.auth:
            errors.append(
                f"route '{route.service}{route.path_prefix}': "
                f"auth_policy '{route.auth_policy}' not defined in auth table"
            )
        if route.rate_limit_policy not in config.rate_limits:
            errors.append(
                f"route '{route.service}{route.path_prefix}': "
                f"rate_limit_policy '{route.rate_limit_policy}' not defined in rate_limits table"
            )
    return errors


def write_policy_config(config: PolicyConfig, path: str | None = None) -> Path:
    """Atomically write *config* to disk and return the target path.

    Writes to a temporary sibling file first then renames to ensure no
    partial write is ever visible to concurrent readers.
    """
    target = Path(path) if path else _default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)
    tmp.replace(target)
    return target
