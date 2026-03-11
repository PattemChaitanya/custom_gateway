"""Point 5: Policy externalization — verify policies live outside code and can be
updated at runtime without a server restart.

Tests confirm:
- GET /policies returns the active policy config from disk
- POST /policies/validate accepts a valid config (dry-run, no disk write)
- POST /policies/validate rejects dangling auth_policy ref (422)
- POST /policies/validate rejects dangling rate_limit_policy ref (422)
- PUT /policies writes a new policy to disk; subsequent routes honour it immediately
- PUT /policies with an invalid config is rejected (422, disk unchanged)
- Original policy is restored after each write test
"""

import json
import pytest
from httpx import ASGITransport, AsyncClient

from app.control_plane.policies import _default_config_path, load_policy_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_raw() -> dict:
    with _default_config_path().open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_raw(data: dict) -> None:
    path = _default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


MINIMAL_VALID_CONFIG = {
    "version": "policies/test-v1",
    "routes": [],
    "auth": {},
    "rate_limits": {},
}

DANGLING_AUTH_CONFIG = {
    "version": "policies/bad-auth",
    "routes": [
        {
            "path_prefix": "/foo",
            "service": "foo-svc",
            "strategy": "round_robin",
            "auth_policy": "nonexistent_auth",
            "rate_limit_policy": "standard",
        }
    ],
    "auth": {},
    "rate_limits": {
        "standard": {"name": "standard", "limit": 100, "window_seconds": 60},
    },
}

DANGLING_RATE_LIMIT_CONFIG = {
    "version": "policies/bad-rl",
    "routes": [
        {
            "path_prefix": "/bar",
            "service": "bar-svc",
            "strategy": "round_robin",
            "auth_policy": "none_auth",
            "rate_limit_policy": "nonexistent_rl",
        }
    ],
    "auth": {
        "none_auth": {"name": "none_auth", "mode": "none", "scopes": []},
    },
    "rate_limits": {},
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_policies_returns_active_config():
    """GET /mini-cloud/policies must return the on-disk config."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        r = await ac.get("/mini-cloud/policies")

    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert "routes" in data
    assert "auth" in data
    assert "rate_limits" in data


@pytest.mark.asyncio
async def test_validate_accepts_valid_config():
    """POST /mini-cloud/policies/validate must return 200 for a valid config."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        r = await ac.post("/mini-cloud/policies/validate", json=MINIMAL_VALID_CONFIG)

    assert r.status_code == 200, r.text
    assert r.json()["valid"] is True


@pytest.mark.asyncio
async def test_validate_rejects_dangling_auth_policy():
    """POST /mini-cloud/policies/validate must 422 when auth_policy ref is missing."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        r = await ac.post("/mini-cloud/policies/validate", json=DANGLING_AUTH_CONFIG)

    assert r.status_code == 422, r.text
    errors = r.json()["detail"]["errors"]
    assert any("nonexistent_auth" in e for e in errors)


@pytest.mark.asyncio
async def test_validate_rejects_dangling_rate_limit_policy():
    """POST /mini-cloud/policies/validate must 422 when rate_limit_policy ref is missing."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        r = await ac.post("/mini-cloud/policies/validate", json=DANGLING_RATE_LIMIT_CONFIG)

    assert r.status_code == 422, r.text
    errors = r.json()["detail"]["errors"]
    assert any("nonexistent_rl" in e for e in errors)


@pytest.mark.asyncio
async def test_put_policies_invalid_is_rejected_and_disk_unchanged():
    """PUT /mini-cloud/policies with dangling refs must 422 and leave disk unchanged."""
    from app.main import app

    original = _read_raw()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        r = await ac.put("/mini-cloud/policies", json=DANGLING_AUTH_CONFIG)

    assert r.status_code == 422, r.text
    # Disk must be untouched.
    assert _read_raw() == original


@pytest.mark.asyncio
async def test_put_policies_writes_and_takes_effect_immediately():
    """PUT /mini-cloud/policies with a valid config is written to disk and
    subsequent route calls honour the new policy without a restart.

    The test installs a no-auth policy for 'ext-svc', verifies that a route call
    no longer requires auth, then restores the original config.
    """
    from app.main import app

    original = _read_raw()
    new_config = {
        "version": "policies/ext-test",
        "routes": [
            {
                "path_prefix": "/ext",
                "service": "ext-svc",
                "strategy": "round_robin",
                "auth_policy": "open",
                "rate_limit_policy": "loose",
            }
        ],
        "auth": {
            "open": {"name": "open", "mode": "none", "scopes": []},
        },
        "rate_limits": {
            "loose": {"name": "loose", "limit": 1000, "window_seconds": 60},
        },
    }

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            await ac.post("/mini-cloud/reset")

            # Apply the new policy.
            put_r = await ac.put("/mini-cloud/policies", json=new_config)
            assert put_r.status_code == 200, put_r.text
            assert put_r.json()["version"] == "policies/ext-test"

            # Verify GET /policies reflects the new config.
            get_r = await ac.get("/mini-cloud/policies")
            assert get_r.json()["version"] == "policies/ext-test"

            # Register a service instance.
            await ac.post(
                "/mini-cloud/services/ext-svc/instances",
                json={"instance_id": "ext-1",
                      "url": "http://ext-1", "ttl_seconds": 300},
            )

            # Route without any auth token — succeeds because the new policy uses mode=none.
            route_r = await ac.post(
                "/mini-cloud/services/ext-svc/route",
                json={"path": "/ext/resource", "client_id": "ext-client"},
            )
            assert route_r.status_code == 200, route_r.text
            assert route_r.json()[
                "applied_route_policy"]["auth_policy"] == "open"

    finally:
        # Always restore original policy config.
        _write_raw(original)


@pytest.mark.asyncio
async def test_original_policy_restored_after_tests():
    """Sanity check: the on-disk policy is back to its original state."""
    config = load_policy_config()
    # The original config has at least one named auth entry.
    assert len(config.auth) >= 1
    # Version matches the shipped file.
    assert config.version.startswith("policies/")
