# Gateway Management – Testing Guide

> **Audience**: Developers and QA engineers who want to understand, run, extend, or manually test the Gateway Management Platform.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Infrastructure Overview](#test-infrastructure-overview)
3. [Running Tests](#running-tests)
4. [pytest Markers & Filters](#pytest-markers--filters)
5. [Fixture Reference](#fixture-reference)
6. [Complete Test Catalogue](#complete-test-catalogue)
7. [Phase-by-Phase Test Reference](#phase-by-phase-test-reference)
   - [Phase 1 – Gateway Proxy Engine](#phase-1--gateway-proxy-engine)
   - [Phase 2 – API Deployment & Lifecycle](#phase-2--api-deployment--lifecycle)
   - [Phase 3 – Auth Policy Enforcement](#phase-3--auth-policy-enforcement)
   - [Phase 4 – Rate Limiting](#phase-4--rate-limiting)
   - [Phase 5 – RBAC Management Permissions](#phase-5--rbac-management-permissions)
   - [Phase 6 – Secret Injection](#phase-6--secret-injection)
   - [Phase 7 – Schema Validation](#phase-7--schema-validation)
   - [Phase 8 – Backend Pool Load Balancing](#phase-8--backend-pool-load-balancing)
   - [Phase 9 – Mini-Cloud Integration](#phase-9--mini-cloud-integration)
   - [Phase 10 – Sub-resource CRUD & Full Auth Flow](#phase-10--sub-resource-crud--full-auth-flow)
8. [Manual Testing with curl](#manual-testing-with-curl)
9. [Manual Testing with PowerShell (Windows)](#manual-testing-with-powershell-windows)
10. [Writing New Tests](#writing-new-tests)
11. [Test Files Reference](#test-files-reference)
12. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run only E2E gateway tests
pytest tests/test_e2e_gateway.py -v

# Run a single test by name
pytest tests/test_e2e_gateway.py::test_phase1_unknown_api_returns_404 -v
```

---

## Test Infrastructure Overview

### SQLite Test Database

Tests use a **fresh SQLite database** (`test_dev.db`) that is:

- Wiped and re-created on every test session via Alembic migrations (see `tests/conftest.py`)
- Never the same file as the production database
- Seeded with 4 base environments: **Production (id=1), Staging (id=2), Testing (id=3), Development (id=4)**

### HTTP Client

All E2E tests use `httpx.AsyncClient` with `ASGITransport(app=app)`. This means:

- **No real network port is opened** — the HTTP call goes directly into the FastAPI app in-process
- Every middleware, dependency, lifespan event, and route handler runs exactly as in production
- Tests are fast (no network latency)

### Authentication

Tests register a fresh user per session, log in, and reuse the `access_token` as a Bearer token in all management-plane requests.

```
POST /auth/register  → POST /auth/login  → headers={"Authorization": "Bearer <token>"}
```

> **Why a fresh user?** This prevents state from a previous test run interfering. The JWT secret is seeded from `.env` or a test default.

### Async / Event-Loop

Tests run under `pytest-asyncio` with `asyncio_mode = auto` (set in `pytest.ini`). Module-scoped fixtures share a single event loop for the whole module, which is more efficient than creating a new loop per test.

---

## Running Tests

### All Tests

```bash
pytest -v
```

### Only E2E Gateway Tests

```bash
pytest tests/test_e2e_gateway.py -v
```

### One Phase at a Time (using `-k`)

```bash
pytest tests/test_e2e_gateway.py -k "phase1" -v
pytest tests/test_e2e_gateway.py -k "phase3" -v
pytest tests/test_e2e_gateway.py -k "phase9" -v
```

### Existing Test Suites (not E2E)

| Command | What It Tests |
|---|---|
| `pytest tests/test_auth.py -v` | Register, login, refresh, logout |
| `pytest tests/test_api_integration.py -v` | API CRUD via HTTP |
| `pytest tests/test_api_keys.py -v` | API key management |
| `pytest tests/test_rate_limiting.py -v` | Rate limiter algorithm unit tests |
| `pytest tests/test_load_balancing.py -v` | Load balancer algorithm unit tests |
| `pytest tests/test_validation.py -v` | JSON Schema validation logic |
| `pytest tests/test_mini_cloud_*.py -v` | All mini-cloud subsystem tests |

### Coverage Report

```bash
pytest --cov=app --cov-report=html tests/
# Open htmlcov/index.html in your browser
```

---

## pytest Markers & Filters

Markers are declared in `pytest.ini` and can be applied to any test.

| Marker | Purpose | Run with |
|---|---|---|
| `asyncio` | Marks a test as async (applied automatically via `asyncio_mode=auto`) | `pytest -m asyncio` |
| `slow` | Long-running tests (network calls, large migrations) | `pytest -m slow` |
| `integration` | Tests that cross module boundaries | `pytest -m integration` |
| `unit` | Pure logic unit tests with no DB/network | `pytest -m unit` |
| `security` | Auth, RBAC, and injection-related tests | `pytest -m security` |

**Filter by keyword** (works across all test files):

```bash
# Run all Phase 4 tests
pytest -k "phase4" -v

# Run all tests that touch the gateway
pytest -k "gateway" -v

# Exclude slow tests
pytest -m "not slow" -v

# Run security-tagged tests only
pytest -m security -v
```

**Useful pytest flags**:

| Flag | Effect |
|---|---|
| `-v` | Verbose — print each test name and PASSED/FAILED |
| `-s` | Disable output capture — see print() and log output |
| `-x` | Stop after first failure |
| `--tb=short` | Shorter traceback on failure |
| `--lf` | Re-run only the tests that failed in the last run |
| `-q` | Quiet — only print summary |
| `--co` | Collect-only — list tests without running them |

---

## Fixture Reference

Fixtures are reusable setup/teardown helpers. They are defined in two places:

### `tests/conftest.py` (session-scoped, global)

| Fixture | Scope | What it does |
|---|---|---|
| `apply_migrations` | `session` (autouse) | Deletes `test_dev.db`, runs `alembic upgrade head`, sets `DATABASE_URL` env var |
| `event_loop` | `session` | Creates a single asyncio event loop shared across all async tests |
| `initialize_db_manager` | `session` | Calls `db_manager.initialize()` and `db_manager.shutdown()` around the session |

> `apply_migrations` is `autouse=True` — it runs automatically before any test, without you needing to list it.

### `tests/test_e2e_gateway.py` (module-scoped)

| Fixture | Scope | What it does |
|---|---|---|
| `client` | `module` | Creates `AsyncClient(ASGITransport(app))` — the in-process HTTP client |
| `admin_token` | `module` | Registers a unique user, logs in, returns the `access_token` string |
| `auth` | `module` | Returns `{"Authorization": "Bearer <admin_token>"}` for use as `headers=auth` |
| `api_id` | `module` | Creates a new API in `draft` status, returns its integer id |
| `deployed_api` | `module` | Deploys the `api_id` API to environment 1 (Production), returns the api id |

**How fixtures chain**:

```
apply_migrations (autouse, session)
     │
     └─► client (module)
              │
              ├─► admin_token (module)
              │        │
              │        └─► auth (module) ─────────────────────┐
              │                                               │
              └─► api_id (module, depends on client + auth) ──┤
                       │                                      │
                       └─► deployed_api (module) ─────────────┘
```

**Using fixtures in your own tests**:

```python
@pytest.mark.asyncio
async def test_my_feature(client, auth, deployed_api):
    # client   → AsyncClient, ready to make HTTP calls
    # auth     → {"Authorization": "Bearer <token>"}
    # deployed_api → integer API id of an ACTIVE API
    r = await client.get(f"/apis/{deployed_api}", headers=auth)
    assert r.status_code == 200
```

---

## Complete Test Catalogue

All 35 tests in `tests/test_e2e_gateway.py`:

| # | Test name | Phase | What it asserts |
|---|---|---|---|
| 1 | `test_rbac_unauthenticated_is_rejected` | 5 | `GET /apis/` without token → 401 or 403 |
| 2 | `test_rbac_authenticated_can_list_apis` | 5 | Bearer token → 200, returns a list |
| 3 | `test_phase2_draft_api_returns_503` | 2 | Draft API gateway call → 503 |
| 4 | `test_phase2_deployed_api_is_active` | 2 | Status after deploy is not `draft` |
| 5 | `test_phase2_deployment_list` | 2 | `GET /apis/{id}/deployments` → ≥ 1 entry |
| 6 | `test_phase1_gateway_exists` | 1 | Active API does not return 503 from gateway |
| 7 | `test_phase1_gateway_response_headers` | 1 | `x-gateway-latency-ms` and `x-gateway-url-source` in response |
| 8 | `test_phase1_unknown_api_returns_404` | 1 | `/gw/99999999/path` → 404 |
| 9 | `test_phase3_open_policy_passes` | 3 | `open` policy → gateway does not return 401 |
| 10 | `test_phase3_apikey_policy_blocks_without_key` | 3 | `apiKey` policy + no key → 401 or 403 |
| 11 | `test_phase3_jwt_policy_blocks_without_token` | 3 | `jwt` policy + no Bearer → 401 or 403 |
| 12 | `test_phase3_auth_policy_crud` | 3 | Full create/list/get/update/delete on auth-policies |
| 13 | `test_phase4_rate_limit_crud` | 4 | Full create/list/update/delete on rate-limits |
| 14 | `test_phase4_rate_limit_enforced` | 4 | limit=1 → 2nd request returns 429 |
| 15 | `test_phase6_secret_crud` | 6 | Full create/list/get/delete on `/api/secrets/` |
| 16 | `test_phase7_schema_crud` | 7 | Full create/list/get/update/delete on schemas |
| 17 | `test_phase7_schema_validation_rejects_invalid_body` | 7 | Invalid body → 422; valid body → not 422 |
| 18 | `test_phase8_backend_pool_crud` | 8 | Create pool, update algo, toggle backend health, delete |
| 19 | `test_phase9_register_instance` | 9 | Register mini-cloud instance → 200 with correct fields |
| 20 | `test_phase9_heartbeat` | 9 | Heartbeat endpoint → 200 |
| 21 | `test_phase9_route_request` | 9 | `POST /mini-cloud/services/{s}/route` → returns target URL |
| 22 | `test_phase9_resolve_endpoint` | 9 | `GET /mini-cloud/services/{s}/resolve` → returns instance |
| 23 | `test_phase9_link_and_unlink_api` | 9 | Link writes `service_name` to API config; unlink clears it |
| 24 | `test_phase9_gateway_selects_mini_cloud_url` | 9 | Linked API → `x-gateway-url-source: mini-cloud` |
| 25 | `test_phase9_scheduler_enqueue_and_ack` | 9 | Enqueue → lease → ack full job lifecycle |
| 26 | `test_phase9_autoscaler_scale_up` | 9 | High queue depth → `action: scale_up` |
| 27 | `test_phase9_autoscaler_scale_down` | 9 | Low load → `action: scale_down` or `none` |
| 28 | `test_phase9_control_loop_tick` | 9 | Control loop tick → `queue_depth` and `autoscaler` keys |
| 29 | `test_phase10_deployment_delete` | 10 | Create deployment → delete → 204 |
| 30 | `test_phase10_api_update_description` | 10 | `PUT /apis/{id}` updates `description` field |
| 31 | `test_phase10_deprecated_api_returns_410` | 10 | Deprecate API → gateway returns 410 |
| 32 | `test_phase10_full_auth_flow` | 10 | register → login → /auth/me → email matches |
| 33 | `test_phase10_refresh_token_flow` | 10 | Login → refresh → logout → revoked refresh fails |
| 34 | `test_misc_health_check` | misc | `GET /health` → 200 |
| 35 | `test_misc_mini_cloud_contract` | misc | `GET /mini-cloud/contract` → has `version` and `guarantees` |

---

## Phase-by-Phase Test Reference

All phases follow a common pattern:

```
Create API (POST /apis/) → draft status
  ↓
Deploy API (POST /apis/{id}/deployments) → active status
  ↓
Attach policy/schema/pool/rate-limit as needed
  ↓
Call gateway (GET/POST /gw/{api_id}/...)
  ↓
Assert expected HTTP status
```

---

### Phase 1 – Gateway Proxy Engine

**What it is**: The `/gw/{api_id}/{path}` endpoint routes every incoming request through a 9-step pipeline:

```
Step 1: Resolve API by ID        → 404 if unknown
Step 2: Check lifecycle          → 503 if draft, 410 if deprecated
Step 3: Determine target URL     → 400 if none configured
Step 4: Enforce auth policy      → 401/403 on failure
Step 5: Enforce rate limit       → 429 on exceed
Step 6: Inject connector secrets
Step 7: Validate request schema  → 422 on invalid body
Step 8: Proxy to upstream        → upstream response forwarded
Step 9: Return with tracing headers (x-gateway-latency-ms, x-gateway-url-source, x-gateway-env)
```

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase1_gateway_exists` | Active API does not return 503 |
| `test_phase1_gateway_response_headers` | `x-gateway-latency-ms` and `x-gateway-url-source` present |
| `test_phase1_unknown_api_returns_404` | Non-existent api_id returns 404 |

**Manual test**:

```bash
# Replace <api_id> with a real ID from POST /apis/
curl -i http://localhost:8000/gw/<api_id>/get
# Expected headers in response:
#   x-gateway-latency-ms: <number>
#   x-gateway-url-source: config|env-override|pool|mini-cloud
```

---

### Phase 2 – API Deployment & Lifecycle

**What it is**: APIs are created in `draft` status. They become `active` only after being deployed to an environment. They can be explicitly set to `deprecated`.

**Status transitions**:

```
draft  ──deploy──>  active  ──deprecate──>  deprecated
```

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase2_draft_api_returns_503` | Draft API returns 503 from gateway |
| `test_phase2_deployed_api_is_active` | After deployment, status != draft |
| `test_phase2_deployment_list` | Returns ≥ 1 deployment entry |
| `test_phase10_deprecated_api_returns_410` | Deprecated API returns 410 |

**Manual test**:

```bash
TOKEN="<your_token>"

# 1. Create API
API=$(curl -s -X POST http://localhost:8000/apis/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-api","version":"v1","config":{"target_url":"http://httpbin.org"}}')
API_ID=$(echo $API | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "API ID: $API_ID  Status: $(echo $API | python -c "import sys,json; print(json.load(sys.stdin)['status'])")"

# 2. Try gateway — should 503 (draft)
curl -i http://localhost:8000/gw/$API_ID/get

# 3. Deploy
curl -s -X POST http://localhost:8000/apis/$API_ID/deployments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"environment_id":1,"target_url_override":"http://httpbin.org","notes":"manual test"}'

# 4. Try gateway — should not 503 now
curl -i http://localhost:8000/gw/$API_ID/get

# 5. Deprecate
curl -s -X PATCH http://localhost:8000/apis/$API_ID/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"deprecated"}'

# 6. Try gateway — should 410
curl -i http://localhost:8000/gw/$API_ID/get
```

---

### Phase 3 – Auth Policy Enforcement

**What it is**: Each API can have one or more auth policies attached. The gateway evaluates them during Step 4.

**Policy Types**:

| Type | Behavior |
|---|---|
| `none` or `open` | Always passes. No credential required. |
| `apiKey` | Requires `X-API-Key` header (or custom header via `config.header_name`). Checks against DB-stored keys. |
| `jwt` / `bearer` | Requires `Authorization: Bearer <token>`. Validates locally. |
| `oauth2` | Introspects token against external OAuth2 server (requires `config.introspection_url`). |

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase3_open_policy_passes` | No credential → gateway does not return 401 |
| `test_phase3_apikey_policy_blocks_without_key` | Missing `X-API-Key` → 401 |
| `test_phase3_jwt_policy_blocks_without_token` | Missing Bearer → 401 |
| `test_phase3_auth_policy_crud` | Full CRUD: create/list/get/update/delete |

**Manual test – apiKey**:

```bash
TOKEN="<your_token>"
API_ID="<your_api_id>"

# 1. Attach apiKey policy
POLICY=$(curl -s -X POST http://localhost:8000/apis/$API_ID/auth-policies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"key-guard","type":"apiKey","config":{"header_name":"X-API-Key"}}')
POLICY_ID=$(echo $POLICY | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Request without key → 401
curl -i http://localhost:8000/gw/$API_ID/get

# 3. Create an API key 
KEY=$(curl -s -X POST http://localhost:8000/api/keys/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"test-key","scopes":["read"]}')
API_KEY=$(echo $KEY | python -c "import sys,json; print(json.load(sys.stdin)['key'])")

# 4. Request with key → 200 (or upstream error)
curl -i -H "X-API-Key: $API_KEY" http://localhost:8000/gw/$API_ID/get

# 5. Remove policy
curl -X DELETE http://localhost:8000/apis/$API_ID/auth-policies/$POLICY_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

### Phase 4 – Rate Limiting

**What it is**: Per-API rate limits are attached as sub-resources. The gateway enforces them in Step 5.

**Algorithms**:

| Algorithm | Behavior |
|---|---|
| `fixed_window` | Counts requests in discrete windows (e.g., 100/min resets every minute) |
| `sliding_window` | Counts requests over a rolling time window |
| `token_bucket` | Steady refill rate, allows short bursts |

**Key types**: `global` (all traffic combined), `per-ip` (per client IP), `per-key` (per API key)

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase4_rate_limit_crud` | Full CRUD: create/list/update/delete |
| `test_phase4_rate_limit_enforced` | Limit=1 → second request returns 429 |

**Manual test**:

```bash
TOKEN="<your_token>"
API_ID="<your_api_id>"

# Create tight rate limit (1 req per 60s)
curl -s -X POST http://localhost:8000/apis/$API_ID/rate-limits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"tight","algorithm":"fixed_window","limit":1,"window_seconds":60,"key_type":"global"}'

# First request → passes
curl -i http://localhost:8000/gw/$API_ID/get

# Second request → 429 Too Many Requests
curl -i http://localhost:8000/gw/$API_ID/get
```

---

### Phase 5 – RBAC Management Permissions

**What it is**: All management-plane endpoints (`/apis/*`, `/secrets/*`, `/keys/*`, etc.) require a valid JWT token. Permissions are checked with `require_permission()`.

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_rbac_unauthenticated_is_rejected` | `GET /apis/` without token → 401 or 403 |
| `test_rbac_authenticated_can_list_apis` | With valid token → 200 |

**Manual test**:

```bash
# Without token → 401/403
curl -i http://localhost:8000/apis/

# With token → 200
curl -i -H "Authorization: Bearer <token>" http://localhost:8000/apis/
```

---

### Phase 6 – Secret Injection

**What it is**: API configs can reference secrets as `${secret:my-secret-name}`. The gateway resolves and injects them in Step 6 before proxying.

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase6_secret_crud` | Full CRUD on `/api/secrets/` |

**Manual test**:

```bash
TOKEN="<your_token>"

# Create secret
SECRET=$(curl -s -X POST http://localhost:8000/api/secrets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"db-password","value":"hunter2","description":"test secret"}')

# List secrets
curl -s http://localhost:8000/api/secrets/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Delete secret
curl -X DELETE http://localhost:8000/api/secrets/db-password \
  -H "Authorization: Bearer $TOKEN"
```

---

### Phase 7 – Schema Validation

**What it is**: JSON Schemas attached to an API are enforced by the gateway on `POST`, `PUT`, and `PATCH` requests (Step 7). Invalid bodies are rejected with `422 Unprocessable Entity`.

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase7_schema_crud` | Full CRUD on `/apis/{id}/schemas` |
| `test_phase7_schema_validation_rejects_invalid_body` | Missing required field → 422; valid body → not 422 |

**Manual test**:

```bash
TOKEN="<your_token>"
API_ID="<your_api_id>"

# Attach schema
SCHEMA=$(curl -s -X POST http://localhost:8000/apis/$API_ID/schemas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "user-schema",
    "definition": {
      "type": "object",
      "properties": {"name": {"type": "string"}},
      "required": ["name"]
    }
  }')
SC_ID=$(echo $SCHEMA | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Invalid body (missing 'name') → 422
curl -i -X POST http://localhost:8000/gw/$API_ID/post \
  -H "Content-Type: application/json" \
  -d '{"age": 25}'

# Valid body → not 422
curl -i -X POST http://localhost:8000/gw/$API_ID/post \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'

# Remove schema
curl -X DELETE http://localhost:8000/apis/$API_ID/schemas/$SC_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

### Phase 8 – Backend Pool Load Balancing

**What it is**: APIs can have named backend pools with multiple servers. The gateway selects the next backend using the pool's algorithm (Step 3, URL priority chain).

**Algorithms**: `round_robin`, `least_connections`, `weighted`

**URL Priority Order** (first wins):
1. Mini-cloud service registry (Phase 9)
2. Backend pool (Phase 8)
3. Deployment environment override (`target_url_override`)
4. API config `target_url`

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase8_backend_pool_crud` | Create pool, list, get, update algorithm, toggle health, delete |

**Manual test**:

```bash
TOKEN="<your_token>"
API_ID="<your_api_id>"

# Create pool with 2 backends
POOL=$(curl -s -X POST http://localhost:8000/apis/$API_ID/backend-pools \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prod-pool",
    "algorithm": "round_robin",
    "backends": [
      {"url": "http://backend1.example.com", "weight": 1, "healthy": true},
      {"url": "http://backend2.example.com", "weight": 1, "healthy": true}
    ]
  }')
POOL_ID=$(echo $POOL | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Mark backend1 unhealthy
curl -s -X PATCH \
  "http://localhost:8000/apis/$API_ID/backend-pools/$POOL_ID/backends/http%3A%2F%2Fbackend1.example.com/health" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"healthy": false}'

# Gateway will now only use backend2
curl -i http://localhost:8000/gw/$API_ID/get
```

---

### Phase 9 – Mini-Cloud Integration

**What it is**: A built-in service discovery registry. Services register instances with a TTL. APIs can be linked to a service name, and the gateway will dynamically pick a live instance.

**Key endpoints**:

| Endpoint | Purpose |
|---|---|
| `POST /mini-cloud/services/{svc}/instances` | Register an instance |
| `POST /mini-cloud/services/{svc}/instances/{id}/heartbeat` | Refresh TTL |
| `GET  /mini-cloud/services/{svc}/resolve?strategy=round_robin` | Pick an instance |
| `POST /mini-cloud/services/{svc}/route` | Same as resolve but via POST |
| `POST /mini-cloud/services/{svc}/link-api/{api_id}` | Link gateway API to service |
| `DELETE /mini-cloud/services/{svc}/link-api/{api_id}` | Unlink |
| `POST /mini-cloud/scheduler/jobs` | Enqueue a job |
| `POST /mini-cloud/scheduler/jobs/lease` | Worker leases a job |
| `POST /mini-cloud/scheduler/jobs/{id}/ack` | Worker acknowledges |
| `POST /mini-cloud/autoscaler/evaluate` | Get scale recommendation |
| `POST /mini-cloud/control-loop/tick` | Run one control loop cycle |
| `GET  /mini-cloud/contract` | Platform SLO contract |

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase9_register_instance` | Instance registered successfully |
| `test_phase9_heartbeat` | TTL refreshed |
| `test_phase9_route_request` | Returns target URL |
| `test_phase9_resolve_endpoint` | Returns instance URL |
| `test_phase9_link_and_unlink_api` | config updated / cleared |
| `test_phase9_gateway_selects_mini_cloud_url` | `x-gateway-url-source: mini-cloud` |
| `test_phase9_scheduler_enqueue_and_ack` | Full job lifecycle |
| `test_phase9_autoscaler_scale_up` | High load → scale_up |
| `test_phase9_autoscaler_scale_down` | No load → scale_down/none |
| `test_phase9_control_loop_tick` | Queue depth + autoscaler keys present |

**Manual test**:

```bash
SVC="my-payment-service"
API_ID="<your_api_id>"
TOKEN="<your_token>"

# Register instance
curl -s -X POST http://localhost:8000/mini-cloud/services/$SVC/instances \
  -H "Content-Type: application/json" \
  -d '{"instance_id":"pay-1","url":"http://payment1:3000","ttl_seconds":60}'

# Resolve
curl -s "http://localhost:8000/mini-cloud/services/$SVC/resolve?strategy=round_robin"

# Link API
curl -s -X POST http://localhost:8000/mini-cloud/services/$SVC/link-api/$API_ID \
  -H "Content-Type: application/json" \
  -d '{"routing_strategy":"round_robin"}'

# Gateway now routes to mini-cloud
curl -i http://localhost:8000/gw/$API_ID/get
# x-gateway-url-source: mini-cloud

# Unlink
curl -X DELETE http://localhost:8000/mini-cloud/services/$SVC/link-api/$API_ID
```

---

### Phase 10 – Sub-resource CRUD & Full Auth Flow

**What it is**: Phase 10 validates the remaining CRUD paths and the full login-to-action flow end-to-end.

**Tests in E2E suite**:

| Test | Expected |
|---|---|
| `test_phase10_deployment_delete` | Create + delete deployment |
| `test_phase10_api_update_description` | PUT /apis/{id} updates description |
| `test_phase10_full_auth_flow` | register → login → /auth/me |
| `test_phase10_refresh_token_flow` | login → refresh → logout → revoked |

**Manual test – auth flow**:

```bash
# Register
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"SecretPass#1"}'

# Login
LOGIN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"SecretPass#1"}')
ACCESS=$(echo $LOGIN | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
REFRESH=$(echo $LOGIN | python -c "import sys,json; print(json.load(sys.stdin)['refresh_token'])")

# Get current user
curl -s http://localhost:8000/auth/me \
  -H "Authorization: Bearer $ACCESS"

# Refresh tokens
curl -s -X POST http://localhost:8000/auth/refresh-tokens \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"

# Logout (revokes refresh token)
curl -s -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"
```

---

## Manual Testing with curl

### Prerequisites

```bash
# Start the backend (in one terminal)
cd backend
uvicorn app.main:app --reload

# In another terminal, set your token
LOGIN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}')
TOKEN=$(echo $LOGIN | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Full Gateway E2E (manual)

```bash
# Step 1: Create API
API=$(curl -s -X POST http://localhost:8000/apis/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "demo-api",
    "version": "v1",
    "description": "demo",
    "config": {"target_url": "http://httpbin.org"}
  }')
API_ID=$(echo $API | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "API ID: $API_ID"

# Step 2: Verify draft blocks gateway
curl -o /dev/null -s -w "Status: %{http_code}\n" http://localhost:8000/gw/$API_ID/get
# Expected: 503

# Step 3: Deploy to environment 1 (Production)
curl -s -X POST http://localhost:8000/apis/$API_ID/deployments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"environment_id":1,"target_url_override":"http://httpbin.org"}'

# Step 4: Verify active → gateway proxies
curl -o /dev/null -s -w "Status: %{http_code}\n" http://localhost:8000/gw/$API_ID/get
# Expected: 200 from httpbin.org

# Step 5: Add apiKey policy
POLICY=$(curl -s -X POST http://localhost:8000/apis/$API_ID/auth-policies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"guard","type":"apiKey","config":{"header_name":"X-API-Key"}}')
POLICY_ID=$(echo $POLICY | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Step 6: Without key → 401
curl -o /dev/null -s -w "Status: %{http_code}\n" http://localhost:8000/gw/$API_ID/get
# Expected: 401

# Step 7: Remove policy, add rate limit 1/60s
curl -X DELETE http://localhost:8000/apis/$API_ID/auth-policies/$POLICY_ID \
  -H "Authorization: Bearer $TOKEN"

RL=$(curl -s -X POST http://localhost:8000/apis/$API_ID/rate-limits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"tight","algorithm":"fixed_window","limit":1,"window_seconds":60,"key_type":"global"}')
RL_ID=$(echo $RL | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Step 8: First request passes, second is 429
curl -o /dev/null -s -w "First:  %{http_code}\n" http://localhost:8000/gw/$API_ID/get
curl -o /dev/null -s -w "Second: %{http_code}\n" http://localhost:8000/gw/$API_ID/get

# Cleanup rate limit
curl -X DELETE http://localhost:8000/apis/$API_ID/rate-limits/$RL_ID \
  -H "Authorization: Bearer $TOKEN"

# Step 9: Add schema validation
curl -s -X POST http://localhost:8000/apis/$API_ID/schemas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "body-schema",
    "definition": {
      "type": "object",
      "properties": {"name": {"type": "string"}},
      "required": ["name"]
    }
  }'

# Invalid POST body → 422
curl -o /dev/null -s -w "Invalid: %{http_code}\n" -X POST http://localhost:8000/gw/$API_ID/post \
  -H "Content-Type: application/json" -d '{"age": 99}'

# Valid POST body → proxied
curl -o /dev/null -s -w "Valid:   %{http_code}\n" -X POST http://localhost:8000/gw/$API_ID/post \
  -H "Content-Type: application/json" -d '{"name": "Bob"}'
```

---

## Manual Testing with PowerShell (Windows)

> The curl commands in the previous section use bash syntax. Use these PowerShell equivalents when working on Windows.

### Set up token variable

```powershell
# Register (first time only)
$body = '{"email":"admin@example.com","password":"SecretPass#1"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/register `
  -Body $body -ContentType "application/json"

# Login and capture token
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login `
  -Body $body -ContentType "application/json"
$TOKEN = $login.access_token
$HEADERS = @{ Authorization = "Bearer $TOKEN" }
```

### Create an API

```powershell
$api = Invoke-RestMethod -Method Post -Uri http://localhost:8000/apis/ `
  -Headers $HEADERS `
  -Body '{"name":"demo-api","version":"v1","config":{"target_url":"http://httpbin.org"}}' `
  -ContentType "application/json"
$API_ID = $api.id
Write-Host "API ID: $API_ID  Status: $($api.status)"
```

### Test gateway (draft → 503, then deploy → active)

```powershell
# Draft → 503
try {
    Invoke-RestMethod -Uri "http://localhost:8000/gw/$API_ID/get"
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)"  # expect 503
}

# Deploy
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/apis/$API_ID/deployments" `
  -Headers $HEADERS `
  -Body "{`"environment_id`":1,`"target_url_override`":`"http://httpbin.org`"}" `
  -ContentType "application/json"

# Active → proxies (200 or 502 from upstream)
$gw = Invoke-WebRequest -Uri "http://localhost:8000/gw/$API_ID/get"
Write-Host "Status: $($gw.StatusCode)"
Write-Host "URL Source: $($gw.Headers['x-gateway-url-source'])"
```

### Add apiKey policy and test enforcement

```powershell
# Add policy
$policy = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/apis/$API_ID/auth-policies" `
  -Headers $HEADERS `
  -Body '{"name":"guard","type":"apiKey","config":{"header_name":"X-API-Key"}}' `
  -ContentType "application/json"
$POLICY_ID = $policy.id

# Without key → 401
try {
    Invoke-RestMethod -Uri "http://localhost:8000/gw/$API_ID/get"
} catch {
    Write-Host "No key: $($_.Exception.Response.StatusCode.value__)"  # expect 401
}

# Remove policy
Invoke-RestMethod -Method Delete `
  -Uri "http://localhost:8000/apis/$API_ID/auth-policies/$POLICY_ID" `
  -Headers $HEADERS
```

### Rate limit enforcement

```powershell
$rl = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/apis/$API_ID/rate-limits" `
  -Headers $HEADERS `
  -Body '{"name":"tight","algorithm":"fixed_window","limit":1,"window_seconds":60,"key_type":"global"}' `
  -ContentType "application/json"
$RL_ID = $rl.id

# First request — passes
$r1 = Invoke-WebRequest -Uri "http://localhost:8000/gw/$API_ID/get"
Write-Host "First: $($r1.StatusCode)"  # not 429

# Second request — 429
try {
    $r2 = Invoke-WebRequest -Uri "http://localhost:8000/gw/$API_ID/get"
    Write-Host "Second: $($r2.StatusCode)"
} catch {
    Write-Host "Second: $($_.Exception.Response.StatusCode.value__)"  # expect 429
}

# Cleanup
Invoke-RestMethod -Method Delete `
  -Uri "http://localhost:8000/apis/$API_ID/rate-limits/$RL_ID" `
  -Headers $HEADERS
```

### Schema validation

```powershell
$schema = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/apis/$API_ID/schemas" `
  -Headers $HEADERS `
  -Body '{
    "name": "body-schema",
    "definition": {
      "type": "object",
      "properties": {"name": {"type": "string"}},
      "required": ["name"]
    }
  }' `
  -ContentType "application/json"
$SC_ID = $schema.id

# Invalid body → 422
try {
    Invoke-RestMethod -Method Post -Uri "http://localhost:8000/gw/$API_ID/post" `
      -Body '{"age":99}' -ContentType "application/json"
} catch {
    Write-Host "Invalid: $($_.Exception.Response.StatusCode.value__)"  # expect 422
}

# Valid body → proxied
try {
    $res = Invoke-WebRequest -Method Post -Uri "http://localhost:8000/gw/$API_ID/post" `
      -Body '{"name":"Bob"}' -ContentType "application/json"
    Write-Host "Valid: $($res.StatusCode)"  # not 422
} catch {
    Write-Host "Valid (upstream error): $($_.Exception.Response.StatusCode.value__)"
}
```

### Mini-cloud link

```powershell
$SVC = "my-service"

# Register instance
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/mini-cloud/services/$SVC/instances" `
  -Body '{"instance_id":"svc-1","url":"http://httpbin.org","ttl_seconds":120}' `
  -ContentType "application/json"

# Link API
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/mini-cloud/services/$SVC/link-api/$API_ID" `
  -Body '{"routing_strategy":"round_robin"}' -ContentType "application/json"

# Gateway uses mini-cloud source
$gw = Invoke-WebRequest -Uri "http://localhost:8000/gw/$API_ID/get"
Write-Host "URL Source: $($gw.Headers['x-gateway-url-source'])"  # mini-cloud

# Unlink
Invoke-RestMethod -Method Delete `
  -Uri "http://localhost:8000/mini-cloud/services/$SVC/link-api/$API_ID"
```

---

## Writing New Tests

### Anatomy of an E2E test

```python
import pytest
from httpx import ASGITransport, AsyncClient

# 1. Tests are async functions
@pytest.mark.asyncio
async def test_my_feature(client, auth, deployed_api):
    # 2. Use the shared client fixture for HTTP calls
    r = await client.post(
        f"/apis/{deployed_api}/auth-policies",
        json={"name": "my-policy", "type": "open", "config": {}},
        headers=auth,          # 3. Always pass auth headers for management endpoints
    )
    # 4. Assert on status code first, then response body
    assert r.status_code == 201, r.text
    assert r.json()["type"] == "open"
```

### Adding a test for a new gateway behavior

```python
@pytest.mark.asyncio
async def test_gateway_custom_header_forwarded(client, auth, deployed_api):
    """Gateway must forward X-Custom-Header to upstream."""
    r = await client.get(
        f"/gw/{deployed_api}/headers",
        headers={"X-Custom-Header": "hello"},
    )
    # httpbin.org/headers echoes request headers back
    assert r.status_code == 200
    forwarded = r.json().get("headers", {})
    assert forwarded.get("X-Custom-Header") == "hello"
```

### Adding a test for a new management endpoint

```python
@pytest.mark.asyncio
async def test_my_new_endpoint_crud(client, auth, deployed_api):
    """Full CRUD on /apis/{id}/my-new-resource."""
    # CREATE
    r = await client.post(
        f"/apis/{deployed_api}/my-new-resource",
        json={"name": "test", "value": 42},
        headers=auth,
    )
    assert r.status_code == 201, r.text
    resource_id = r.json()["id"]

    # READ
    r = await client.get(f"/apis/{deployed_api}/my-new-resource/{resource_id}", headers=auth)
    assert r.status_code == 200
    assert r.json()["value"] == 42

    # UPDATE
    r = await client.put(
        f"/apis/{deployed_api}/my-new-resource/{resource_id}",
        json={"value": 99},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["value"] == 99

    # DELETE
    r = await client.delete(f"/apis/{deployed_api}/my-new-resource/{resource_id}", headers=auth)
    assert r.status_code == 204

    # CONFIRM GONE
    r = await client.get(f"/apis/{deployed_api}/my-new-resource/{resource_id}", headers=auth)
    assert r.status_code == 404
```

### Adding a module-scoped fixture

Use `module` scope when the setup is expensive and can be safely shared across tests in the same file:

```python
import pytest_asyncio

@pytest_asyncio.fixture(scope="module")
async def special_api(client, auth):
    """Create an API with a specific config for a group of tests."""
    r = await client.post("/apis/", json={
        "name": "special-api",
        "version": "v2",
        "config": {"target_url": "http://my-backend.internal"},
    }, headers=auth)
    assert r.status_code == 201
    api_id = r.json()["id"]
    yield api_id
    # Cleanup: delete the API after all tests in this module finish
    await client.delete(f"/apis/{api_id}", headers=auth)
```

### Test isolation checklist

Before submitting a new test, verify:

- [ ] Does not depend on test execution order (use module-scoped fixtures for shared state)
- [ ] Cleans up resources it creates (delete policies, schemas, pools in a cleanup block)
- [ ] Uses a unique name (add `uuid.uuid4().hex[:6]` suffix if needed to avoid conflicts)
- [ ] Asserts `r.status_code == <expected>, r.text` so failures are informative
- [ ] Uses `async def` and the `client` fixture, not raw `TestClient`

### Environment variable reference for tests

The following environment variables affect test behaviour:

| Variable | Default in tests | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///test_dev.db` | Set by `conftest.py`; overrides production DB |
| `SECRET_KEY` | Value from `.env` or a fallback | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

Set any of these in a `.env` file in the `backend/` directory, or export them before running pytest:

```bash
# bash
export SECRET_KEY="test-secret-key-change-in-production"
pytest tests/test_e2e_gateway.py -v

# PowerShell
$env:SECRET_KEY = "test-secret-key-change-in-production"
pytest tests/test_e2e_gateway.py -v
```

---

## Test Files Reference

| File | Phase | Description |
|---|---|---|
| `tests/test_e2e_gateway.py` | 1–10 | **New** — full pipeline E2E tests |
| `tests/test_auth.py` | Auth | Register, login, refresh, logout, /me |
| `tests/test_api_integration.py` | API CRUD | Create/read/update/delete APIs via HTTP |
| `tests/test_api_keys.py` | Keys | API key management (create/revoke/rotate) |
| `tests/test_rate_limiting.py` | Phase 4 | Fixed window, sliding window, token bucket algorithms |
| `tests/test_load_balancing.py` | Phase 8 | Round robin, least connections, weighted algorithms |
| `tests/test_validation.py` | Phase 7 | JSON Schema validation logic |
| `tests/test_authorization.py` | Phase 5 | RBAC role/permission checks |
| `tests/test_audit_logging.py` | Logging | Admin audit trail |
| `tests/test_connectors.py` | Connectors | External connector CRUD |
| `tests/test_control_plane_persistence.py` | Control | State persistence |
| `tests/test_metrics.py` | Observability | Metrics collection |
| `tests/test_mini_cloud_*.py` | Phase 9 | All mini-cloud subsystem tests |

---

## Troubleshooting

### `pytest: error: unrecognized arguments` or import errors

```bash
# Make sure you're in the backend directory and the venv is active
cd backend
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

### `RuntimeError: no running event loop`

This is caused by mixing sync and async code. Ensure:
- All test functions that use `await` are marked `async def`
- `asyncio_mode = auto` is in `pytest.ini` (it is, by default)

### `DATABASE_URL not set` / `no such table`

The `conftest.py` sets `DATABASE_URL` before the app is imported. If tests fail with DB errors, ensure you are not importing `app.main` before conftest runs:
```python
# BAD — import at top of test file before conftest sets env var:
from app.main import app

# GOOD — import inside a fixture, or let conftest.py handle it
```

### `AssertionError: Expected 201, got 422` on API create

Check that `config` is a dict, not a string:
```json
// WRONG
"config": "{\"target_url\": \"...\"}"
// CORRECT
"config": {"target_url": "..."}
```

### `401 Unauthorized` on management endpoints in tests

The `auth_headers` fixture registers a user but that user may not have admin role depending on your RBAC seed. Run:
```bash
cd backend
python scripts/seed_rbac.py
```

### Gateway returns `400 Bad Request` with "No target URL"

Deploy the API first, or set `target_url_override` in the deployment:
```bash
curl -X POST .../apis/$API_ID/deployments \
  -d '{"environment_id":1,"target_url_override":"http://httpbin.org"}'
```

### Rate limit test is flaky (429 comes too early or too late)

Rate limiter state is global in-process. If tests run in a different order, the counter for `global` key may already be non-zero. Use a unique API per test (or a unique rate limit name with `global` scope reset on each module).

### Mini-cloud tests fail with `404 Not Found` on `/mini-cloud/*`

Ensure `app.main` mounts the mini-cloud router. Check:
```python
# In app/main.py
app.include_router(mini_cloud_router, prefix="/mini-cloud")
```

### `x-gateway-url-source` header missing

This header is set by the gateway router **after** Step 3 (URL resolution). If it's missing:
- The request may have been rejected at Step 1/2 (before the header is set)
- Or the gateway router code path for that step doesn't set it yet
