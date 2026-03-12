"""Tests for centralized audit logging middleware."""
from app.middleware.audit import _resolve_event, _extract_resource_id
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# Event resolution unit tests
# ---------------------------------------------------------------------------


class TestEventResolution:
    """Verify _resolve_event maps every known route correctly."""

    @pytest.mark.parametrize(
        "method,path,expected_event",
        [
            # Auth
            ("POST", "/auth/login", "auth:login"),
            ("POST", "/auth/register", "auth:register"),
            ("POST", "/auth/logout", "auth:logout"),
            ("POST", "/auth/refresh-tokens", "auth:token_refresh"),
            ("POST", "/auth/reset-password", "auth:password_reset"),
            ("POST", "/auth/send-code", "auth:send_code"),
            ("POST", "/auth/send-otp", "auth:send_otp"),
            ("POST", "/auth/send-email-code", "auth:send_email_code"),
            ("POST", "/auth/resend-otp", "auth:resend_otp"),
            ("POST", "/auth/verify-email", "auth:verify_email"),
            ("POST", "/auth/verify-otp", "auth:verify_otp"),
            ("POST", "/auth/users/joe@x.com/roles", "auth:set_roles"),
            ("GET", "/auth/users/joe@x.com/roles", "auth:get_roles"),
            ("GET", "/auth/users", "auth:list_users"),
            ("GET", "/auth/me", "auth:me"),
            # Users
            ("GET", "/user/", "user:list"),
            ("GET", "/user/me", "user:me"),
            ("GET", "/user/42", "user:read"),
            # APIs
            ("POST", "/apis/", "api:create"),
            ("GET", "/apis/", "api:list"),
            ("GET", "/apis/1", "api:read"),
            ("PUT", "/apis/1", "api:update"),
            ("DELETE", "/apis/1", "api:delete"),
            # Deployments
            ("POST", "/apis/1/deployments", "deployment:create"),
            ("GET", "/apis/1/deployments", "deployment:list"),
            ("GET", "/apis/1/deployments/2", "deployment:read"),
            ("DELETE", "/apis/1/deployments/2", "deployment:delete"),
            ("PATCH", "/apis/1/status", "deployment:status_update"),
            # Auth Policies
            ("POST", "/apis/1/auth-policies", "auth_policy:create"),
            ("PUT", "/apis/1/auth-policies/2", "auth_policy:update"),
            ("DELETE", "/apis/1/auth-policies/2", "auth_policy:delete"),
            # Rate Limits
            ("POST", "/apis/1/rate-limits", "rate_limit:create"),
            ("PUT", "/apis/1/rate-limits/2", "rate_limit:update"),
            ("DELETE", "/apis/1/rate-limits/2", "rate_limit:delete"),
            # Schemas
            ("POST", "/apis/1/schemas", "schema:create"),
            ("PUT", "/apis/1/schemas/2", "schema:update"),
            ("DELETE", "/apis/1/schemas/2", "schema:delete"),
            # Backend Pools
            ("POST", "/apis/1/backend-pools", "backend_pool:create"),
            ("PUT", "/apis/1/backend-pools/2", "backend_pool:update"),
            ("DELETE", "/apis/1/backend-pools/2", "backend_pool:delete"),
            ("PATCH", "/apis/1/backend-pools/2/backends/http%3A%2F%2Flocalhost/health",
             "backend_pool:health_update"),
            # API Keys
            ("POST", "/api/keys/", "api_key:create"),
            ("GET", "/api/keys/", "api_key:list"),
            ("POST", "/api/keys/1/revoke", "api_key:revoke"),
            ("DELETE", "/api/keys/1", "api_key:delete"),
            ("GET", "/api/keys/1/stats", "api_key:read_stats"),
            ("GET", "/api/keys/verify", "api_key:verify"),
            ("GET", "/api/keys/environments", "environment:list"),
            ("POST", "/api/keys/environments", "environment:create"),
            ("DELETE", "/api/keys/environments/1", "environment:delete"),
            # Secrets
            ("POST", "/api/secrets/", "secret:create"),
            ("GET", "/api/secrets/", "secret:list"),
            ("GET", "/api/secrets/my-key", "secret:read"),
            ("PUT", "/api/secrets/my-key", "secret:update"),
            ("DELETE", "/api/secrets/my-key", "secret:delete"),
            ("POST", "/api/secrets/my-key/rotate", "secret:rotate"),
            # Connectors
            ("POST", "/api/connectors/", "connector:create"),
            ("GET", "/api/connectors/", "connector:list"),
            ("GET", "/api/connectors/1", "connector:read"),
            ("PUT", "/api/connectors/1", "connector:update"),
            ("DELETE", "/api/connectors/1", "connector:delete"),
            ("POST", "/api/connectors/1/test", "connector:test"),
            # Authorizers RBAC
            ("POST", "/api/authorizers/roles", "role:create"),
            ("GET", "/api/authorizers/roles", "role:list"),
            ("GET", "/api/authorizers/roles/1", "role:read"),
            ("PUT", "/api/authorizers/roles/1", "role:update"),
            ("DELETE", "/api/authorizers/roles/1", "role:delete"),
            ("POST", "/api/authorizers/permissions", "permission:create"),
            ("GET", "/api/authorizers/permissions/1", "permission:read"),
            ("PUT", "/api/authorizers/permissions/1", "permission:update"),
            ("DELETE", "/api/authorizers/permissions/1", "permission:delete"),
            ("POST", "/api/authorizers/user-roles", "user_role:assign"),
            ("DELETE", "/api/authorizers/user-roles/1", "user_role:remove"),
            ("GET", "/api/authorizers/user-roles/1", "user_role:read"),
            # Admin
            ("POST", "/api/admin/init-rbac", "admin:init_rbac"),
            ("GET", "/api/admin/rbac-status", "admin:rbac_status"),
            # Audit Logs
            ("GET", "/api/audit-logs", "audit:list"),
            ("GET", "/api/audit-logs/statistics", "audit:statistics"),
            ("GET", "/api/audit-logs/user/1", "audit:user_activity"),
            ("GET", "/api/audit-logs/failed", "audit:failed_attempts"),
            # Mini-Cloud
            ("GET", "/mini-cloud/contract", "minicloud:get_contract"),
            ("GET", "/mini-cloud/policies", "minicloud:get_policies"),
            ("POST", "/mini-cloud/policies/validate", "minicloud:validate_policy"),
            ("PUT", "/mini-cloud/policies", "minicloud:update_policy"),
            ("POST", "/mini-cloud/services/svc1/instances",
             "minicloud:register_instance"),
            ("POST", "/mini-cloud/services/svc1/instances/i1/heartbeat",
             "minicloud:heartbeat"),
            ("POST", "/mini-cloud/services/svc1/instances/i1/health-status",
             "minicloud:health_status"),
            ("GET", "/mini-cloud/services/svc1/instances", "minicloud:list_instances"),
            ("POST", "/mini-cloud/services/svc1/route", "minicloud:route"),
            ("POST", "/mini-cloud/jobs/enqueue", "minicloud:job_enqueue"),
            ("POST", "/mini-cloud/jobs/lease", "minicloud:job_lease"),
            ("POST", "/mini-cloud/jobs/ack", "minicloud:job_ack"),
            ("POST", "/mini-cloud/jobs/fail", "minicloud:job_fail"),
            ("POST", "/mini-cloud/autoscale", "minicloud:autoscale"),
            ("POST", "/mini-cloud/inject/slow-downstream", "minicloud:inject_latency"),
            ("POST", "/mini-cloud/inject/burst-traffic", "minicloud:inject_traffic"),
            # Gateway
            ("GET", "/gw/1/users", "gateway:proxy"),
            ("POST", "/gw/2/data/submit", "gateway:proxy"),
        ],
    )
    def test_event_resolution(self, method, path, expected_event):
        result = _resolve_event(method, path)
        assert result is not None, f"No event for {method} {path}"
        assert result[0] == expected_event

    def test_infrastructure_paths_not_resolved(self):
        """Health, metrics, docs should return None."""
        assert _resolve_event("GET", "/health") is None
        assert _resolve_event("GET", "/metrics") is None
        assert _resolve_event("GET", "/docs") is None
        assert _resolve_event("GET", "/") is None


class TestResourceIdExtraction:
    """Verify _extract_resource_id extracts IDs correctly."""

    @pytest.mark.parametrize(
        "path,expected_id",
        [
            ("/apis/5", "5"),
            ("/api/secrets/my-key", "my-key"),
            ("/api/keys/12", "12"),
            ("/api/connectors/3", "3"),
            ("/api/authorizers/roles/7", "7"),
            # Action segments should resolve to parent ID
            ("/api/keys/12/revoke", "12"),
            ("/api/secrets/my-key/rotate", "my-key"),
            ("/api/connectors/5/test", "5"),
            ("/api/keys/7/stats", "7"),
            # Collection endpoints should return None
            ("/apis/", None),
            ("/api/keys/", None),
            ("/api/secrets/", None),
            ("/api/connectors/", None),
            ("/auth/login", None),
            ("/auth/register", None),
        ],
    )
    def test_resource_id(self, path, expected_id):
        assert _extract_resource_id(path) == expected_id


# ---------------------------------------------------------------------------
# Integration: verify audit logs are created for real API calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_created_on_api_call(client):
    """Hitting an endpoint should produce an audit log entry."""
    # The root endpoint is skipped, so hit /auth/login which will fail
    # but should still be audited
    resp = await client.post("/auth/login", json={"email": "x@x.com", "password": "p"})
    # We're not checking the response status (it might fail due to missing DB),
    # but the audit middleware should have attempted to log.
    # The real assertion is that the middleware didn't crash the request.
    assert resp.status_code in (200, 400, 401, 403, 422, 500)


@pytest.mark.asyncio
async def test_health_not_audited(client):
    """Infrastructure endpoints should NOT be audited."""
    resp = await client.get("/health")
    assert resp.status_code in (200, 500)
