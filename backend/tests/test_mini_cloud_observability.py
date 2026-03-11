"""Point 4: Observability baseline — verify RED metrics + request tracing headers.

Tests confirm:
- /metrics serves valid Prometheus text with expected metric families
- Successful routes increment gateway_route_requests_total{status="ok"}
- 503 (no healthy instance) increments gateway_route_errors_total{error_type="no_healthy_instance"}
- Policy 401 increments gateway_route_errors_total{error_type="policy_401"}
- gateway_route_duration_seconds is observed on every route call
- X-Request-ID header is present on every mini-cloud response
- X-Response-Time header is present on every response (from metrics middleware)
"""

import pytest
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _counter_value(metric_sample_name: str, **label_filters) -> float:
    """Read the current sample value for a named metric from the global registry.

    prometheus_client Counter samples are named ``<counter_name>_total``.
    This helper matches the *sample name* (not the metric family name).
    """
    for family in REGISTRY.collect():
        for sample in family.samples:
            if sample.name == metric_sample_name:
                if all(sample.labels.get(k) == v for k, v in label_filters.items()):
                    return sample.value
    return 0.0


def _histogram_count(metric_sample_name: str, **label_filters) -> float:
    """Return the _count sample for a histogram metric."""
    count_name = metric_sample_name + "_count"
    for family in REGISTRY.collect():
        for sample in family.samples:
            if sample.name == count_name:
                if all(sample.labels.get(k) == v for k, v in label_filters.items()):
                    return sample.value
    return 0.0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_endpoint_serves_prometheus_text():
    """GET /metrics must return 200 with all route metric families present."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        r = await ac.get("/metrics")

    assert r.status_code == 200
    body = r.text
    # Core route RED metric families must be present in the output.
    assert "gateway_route_requests_total" in body
    assert "gateway_route_errors_total" in body
    assert "gateway_route_duration_seconds" in body
    # HTTP-level metrics from the global middleware must also be present.
    assert "gateway_http_requests_total" in body


@pytest.mark.asyncio
async def test_successful_route_increments_route_counter():
    """A successful route call must increment gateway_route_requests_total{status='ok'}."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        await ac.post(
            "/mini-cloud/services/obs-svc/instances",
            json={"instance_id": "obs-1",
                  "url": "http://obs-1", "ttl_seconds": 300},
        )

        before = _counter_value(
            "gateway_route_requests_total",
            service="obs-svc", strategy="round_robin", status="ok",
        )

        r = await ac.post(
            "/mini-cloud/services/obs-svc/route",
            json={"path": "/", "strategy": "round_robin",
                  "client_id": "obs-client"},
        )
        assert r.status_code == 200, r.text

        after = _counter_value(
            "gateway_route_requests_total",
            service="obs-svc", strategy="round_robin", status="ok",
        )

    assert after - \
        before == 1.0, f"Expected counter to increase by 1, got {after - before}"


@pytest.mark.asyncio
async def test_failed_route_increments_error_counter():
    """A 503 (no healthy instance) must increment gateway_route_errors_total."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        # Do NOT register any instance → route will 503.

        before_err = _counter_value(
            "gateway_route_errors_total",
            service="empty-svc", error_type="no_healthy_instance",
        )
        before_route = _counter_value(
            "gateway_route_requests_total",
            service="empty-svc", strategy="round_robin", status="error",
        )

        r = await ac.post(
            "/mini-cloud/services/empty-svc/route",
            json={"path": "/", "strategy": "round_robin",
                  "client_id": "obs-client"},
        )
        assert r.status_code == 503, r.text

        after_err = _counter_value(
            "gateway_route_errors_total",
            service="empty-svc", error_type="no_healthy_instance",
        )
        after_route = _counter_value(
            "gateway_route_requests_total",
            service="empty-svc", strategy="round_robin", status="error",
        )

    assert after_err - before_err == 1.0
    assert after_route - before_route == 1.0


@pytest.mark.asyncio
async def test_auth_error_increments_route_error_counter():
    """A 401 from policy enforcement must increment gateway_route_errors_total{error_type='policy_401'}."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        await ac.post(
            "/mini-cloud/services/orders/instances",
            json={"instance_id": "obs-orders-1",
                  "url": "http://orders-1", "ttl_seconds": 300},
        )

        before = _counter_value(
            "gateway_route_errors_total",
            service="orders", error_type="policy_401",
        )

        # No auth token → 401 from JWT policy
        r = await ac.post(
            "/mini-cloud/services/orders/route",
            json={"path": "/orders/1", "client_id": "obs-auth-test"},
        )
        assert r.status_code == 401, r.text

        after = _counter_value(
            "gateway_route_errors_total",
            service="orders", error_type="policy_401",
        )

    assert after - before == 1.0


@pytest.mark.asyncio
async def test_route_duration_histogram_observed():
    """Every route call (success or error) must record an observation in the duration histogram."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        await ac.post(
            "/mini-cloud/services/dur-svc/instances",
            json={"instance_id": "dur-1",
                  "url": "http://dur-1", "ttl_seconds": 300},
        )

        before = _histogram_count(
            "gateway_route_duration_seconds",
            service="dur-svc", strategy="round_robin",
        )

        r = await ac.post(
            "/mini-cloud/services/dur-svc/route",
            json={"path": "/", "strategy": "round_robin",
                  "client_id": "dur-client"},
        )
        assert r.status_code == 200, r.text

        after = _histogram_count(
            "gateway_route_duration_seconds",
            service="dur-svc", strategy="round_robin",
        )

    assert after - before == 1.0


@pytest.mark.asyncio
async def test_route_response_carries_request_id():
    """Every route response must carry an X-Request-ID header."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        await ac.post(
            "/mini-cloud/services/hdr-svc/instances",
            json={"instance_id": "hdr-1",
                  "url": "http://hdr-1", "ttl_seconds": 300},
        )

        r = await ac.post(
            "/mini-cloud/services/hdr-svc/route",
            json={"path": "/", "client_id": "hdr-client"},
        )
        assert r.status_code == 200, r.text

    assert "x-request-id" in r.headers, "X-Request-ID header missing from route response"
    assert r.headers["x-request-id"]  # must be non-empty


@pytest.mark.asyncio
async def test_route_response_carries_x_response_time():
    """Every response must carry an X-Response-Time header set by the metrics middleware."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        await ac.post(
            "/mini-cloud/services/rt-svc/instances",
            json={"instance_id": "rt-1",
                  "url": "http://rt-1", "ttl_seconds": 300},
        )

        r = await ac.post(
            "/mini-cloud/services/rt-svc/route",
            json={"path": "/", "client_id": "rt-client"},
        )
        assert r.status_code == 200, r.text

    assert "x-response-time" in r.headers, "X-Response-Time header missing from route response"
    # Value should look like "42ms"
    assert r.headers["x-response-time"].endswith(
        "ms"), r.headers["x-response-time"]
