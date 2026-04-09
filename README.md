# FlowGate — Self-Hosted API Gateway Management Platform

Each tenant account gets an isolated Docker gateway instance with a 48-hour TTL.
The control plane manages provisioning, routing, auth policies, rate limits, secrets,
audit logs, and live metrics.

> "A cloud built on one machine can still teach the same lessons as a cloud built on ten thousand."

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FlowGate Platform                            │
│                                                                      │
│  ┌────────────┐   HTTP/REST    ┌─────────────────────────────────┐  │
│  │  React UI  │ ─────────────▶│        Control Plane            │  │
│  │  :5173     │               │       FastAPI  :8000             │  │
│  └────────────┘               │                                  │  │
│                               │  /apis  /api-keys  /secrets      │  │
│  ┌────────────┐               │  /audit-logs  /metrics           │  │
│  │  API       │               │  /gw/{slug}/{api_id}/{path}      │  │
│  │  Consumer  │               │                                  │  │
│  └──────┬─────┘               │  ┌──────────┐  ┌─────────────┐  │  │
│         │                     │  │PostgreSQL│  │    Redis    │  │  │
│         │                     │  │  :5432   │  │    :6379    │  │  │
│         │                     │  └──────────┘  └─────────────┘  │  │
│         │                     │  ┌──────────────────────────┐   │  │
│         │                     │  │  Docker SDK              │   │  │
│         │                     │  │  (/var/run/docker.sock)  │   │  │
│         │                     └──┴──────────┬───────────────┘   │  │
│         │                                   │ provision / reap   │  │
│         │              flowgate_net         ▼                    │  │
│         │    ┌─────────────────────────────────────────────┐    │  │
│         └───▶│  gateway-{account_id}  (Node.js :5xxx)      │    │  │
│  X-API-Key  │  sanitize → apiKey → rateLimit → proxy       │    │  │
│             │  L1 Map → L2 SQLite  │  48h self-destruct     │    │  │
│             └─────────────────────────────────────────────┘    │  │
└──────────────────────────────────────────────────────────────────────┘

Control plane 9-step proxy pipeline (Python gateway):
  1. Resolve API        4. Auth (apiKey/JWT/OAuth2)   7. Schema validation
  2. Lifecycle guard    5. Per-key rate limit (Redis)  8. Upstream proxy
  3. Target resolution  6. Secret injection            9. Tracing headers

Tiered storage — Python: L1 dict → L2 aiosqlite → L3 PostgreSQL
Tiered storage — Node:   L1 Map  → L2 better-sqlite3
```

---

## Quick Start (Docker Compose)

**Prerequisites:** Docker 24+, Docker Compose v2

```bash
# 1. Build the gateway-runtime image (required before first `up`)
docker compose build gateway-runtime

# 2. Start the full stack
docker compose up -d

# 3. Run database migrations
docker compose exec backend python -m alembic -c alembic.ini upgrade head
```

| Service       | URL                         |
|---------------|-----------------------------|
| Frontend      | http://localhost:5173       |
| Backend       | http://localhost:8000       |
| API Docs      | http://localhost:8000/docs  |
| Prometheus    | http://localhost:8000/metrics |
| PostgreSQL    | localhost:5432              |
| Redis         | localhost:6379              |

Default superuser: `admin@example.com` / `changeme123`

---

## Manual Setup (development)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # edit SECRET_KEY at minimum
python -m alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend (separate terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

```bash
# Gateway runtime — build once; instances are spawned by the backend automatically
cd gateway-runtime
npm install && npm run build
# The backend provisions containers via Docker SDK — no need to run manually
```

### Environment Variables

Copy `backend/.env.example` → `backend/.env`. Minimum required:

| Variable             | Description                              |
|----------------------|------------------------------------------|
| `SECRET_KEY`         | JWT signing + encryption key derivation  |
| `REFRESH_TOKEN_SALT` | Refresh token HMAC salt                  |
| `JWT_SECRET`         | Secret for gateway-issued JWT policies   |
| `DATABASE_URL`       | Postgres (prod) or SQLite (dev)          |

See [backend/.env.example](backend/.env.example) for the full reference with all optional vars.

---

## API Reference — curl Examples

All management endpoints require `Authorization: Bearer <token>`.
Gateway proxy endpoints require `X-API-Key`.

### Auth

```bash
# Register
curl -s -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"Secret123!"}' | jq

# Login — capture token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"Secret123!"}' \
  | jq -r '.access_token')

# Refresh
curl -s -X POST http://localhost:8000/auth/refresh \
  -H "Authorization: Bearer $TOKEN" | jq

# Logout
curl -s -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

### Accounts & Gateway Provisioning

```bash
# Create account — automatically provisions a Docker gateway instance (48h TTL)
curl -s -X POST http://localhost:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme Corp","slug":"acme","plan":"pro"}' | jq
# Response: { "gateway_url": "http://localhost:5001", "api_key": "flwk_...", "expires_at": "..." }

# Get instance status + countdown
curl -s http://localhost:8000/api/instances/1 \
  -H "Authorization: Bearer $TOKEN" | jq
# Response: { "status": "running", "gateway_url": "...", "expires_in_seconds": 172341 }

# List all accounts (superuser only)
curl -s http://localhost:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN" | jq
```

### APIs (management)

```bash
# Create API
curl -s -X POST http://localhost:8000/apis/ \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "User Service",
    "version": "v1",
    "config": { "target_url": "http://upstream:3000" }
  }' | jq

# List APIs
curl -s http://localhost:8000/apis/ \
  -H "Authorization: Bearer $TOKEN" | jq

# Get API
curl -s http://localhost:8000/apis/1 \
  -H "Authorization: Bearer $TOKEN" | jq

# Update API
curl -s -X PUT http://localhost:8000/apis/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"User Service","version":"v2"}' | jq

# Delete API
curl -s -X DELETE http://localhost:8000/apis/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Gateway Routes (per-account data-plane routing)

```bash
# Create route
curl -s -X POST http://localhost:8000/api/gateway-routes \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "account_id": 1,
    "path": "/users",
    "method": "GET",
    "target_url": "http://upstream:3000/users",
    "auth_required": true
  }' | jq

# List routes for account
curl -s "http://localhost:8000/api/gateway-routes?account_id=1" \
  -H "Authorization: Bearer $TOKEN" | jq

# Toggle active/inactive
curl -s -X PATCH http://localhost:8000/api/gateway-routes/1/toggle \
  -H "Authorization: Bearer $TOKEN" | jq

# Delete route
curl -s -X DELETE http://localhost:8000/api/gateway-routes/1 \
  -H "Authorization: Bearer $TOKEN"
```

### API Keys

```bash
# Generate key (rate_limit_rpm stored in metadata)
curl -s -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"label":"prod-key","rate_limit_rpm":200}' | jq
# Returns raw key once — store it securely

# List keys (values masked)
curl -s http://localhost:8000/api/keys \
  -H "Authorization: Bearer $TOKEN" | jq

# Revoke key
curl -s -X DELETE http://localhost:8000/api/keys/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Secrets

```bash
# Create encrypted secret
curl -s -X POST http://localhost:8000/secrets \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"stripe-key","value":"sk_live_..."}' | jq

# List secrets (values masked as ***)
curl -s http://localhost:8000/secrets \
  -H "Authorization: Bearer $TOKEN" | jq

# Delete secret
curl -s -X DELETE http://localhost:8000/secrets/stripe-key \
  -H "Authorization: Bearer $TOKEN"
```

### Gateway Proxy (data plane)

```bash
# Account-scoped route (preferred — tenant isolation enforced)
curl -s http://localhost:8000/gw/acme/7/users \
  -H 'X-API-Key: flwk_your_api_key_here'

# With environment override
curl -s "http://localhost:8000/gw/acme/7/orders?env=staging" \
  -H 'X-API-Key: flwk_your_api_key_here'

# With version enforcement
curl -s "http://localhost:8000/gw/acme/7/users?version=v2" \
  -H 'X-API-Key: flwk_your_api_key_here'

# POST with body (triggers JSON Schema validation if configured)
curl -s -X POST http://localhost:8000/gw/acme/7/users \
  -H 'X-API-Key: flwk_your_api_key_here' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alice","email":"alice@example.com"}'

# Legacy unscoped route (backward compat)
curl -s http://localhost:8000/gw/7/users \
  -H 'X-API-Key: flwk_your_api_key_here'
```

Response always includes gateway tracing headers:
```
X-Gateway-Latency-Ms: 12
X-Gateway-Url-Source: static        # mini-cloud | pool | static
X-Gateway-Account: acme
X-Gateway-Api-Version: v1
```

### Metrics & Request Logs

```bash
# Request log summary — hourly buckets + status breakdown + slowest routes
curl -s "http://localhost:8000/api/request-logs/summary?hours=24" \
  -H "Authorization: Bearer $TOKEN" | jq

# Raw request logs (paginated)
curl -s "http://localhost:8000/api/request-logs?hours=6&limit=100" \
  -H "Authorization: Bearer $TOKEN" | jq

# Prometheus scrape endpoint
curl -s http://localhost:8000/metrics

# Dashboard aggregate (7-day)
curl -s http://localhost:8000/metrics/summary \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Audit Logs

```bash
# List with filters
curl -s "http://localhost:8000/api/audit-logs?action=LOGIN_SUCCESS&limit=50" \
  -H "Authorization: Bearer $TOKEN" | jq

# Statistics (total events, breakdown by type/user)
curl -s http://localhost:8000/api/audit-logs/statistics \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Health

```bash
curl -s http://localhost:8000/health | jq
# { "status": "healthy", "database": { "type": "postgresql", "status": "ok" }, "circuit_breakers": {} }
```

---

## Running Tests

```bash
cd backend
pytest -q                                      # full suite (SQLite, no Redis needed)
pytest --cov=app --cov-report=term-missing -q  # with coverage
pytest -m unit -q                              # unit tests only
pytest -m integration -q                       # integration tests only
pytest tests/test_e2e_gateway.py               # 10-phase end-to-end pipeline
```

---

## Project Structure

```
.
├── backend/                    FastAPI control plane
│   ├── app/
│   │   ├── api/                REST endpoints (apis, keys, secrets, accounts, instances…)
│   │   ├── gateway/            Proxy pipeline, instance manager, expiry scheduler
│   │   ├── rate_limiter/       Fixed window / sliding window / token bucket (Redis)
│   │   ├── storage/            Tiered store — L1 dict → L2 aiosqlite → L3 Postgres
│   │   ├── security/           API key hashing (salted SHA-256) + Fernet encryption
│   │   └── db/                 SQLAlchemy async models + connector
│   ├── alembic/versions/       Migrations 0001–0011
│   ├── tests/                  35+ test files
│   └── .env.example            Full env-var reference
│
├── frontend/                   React 18 + TypeScript + MUI
│   └── src/
│       ├── pages/              Dashboard, APIs, Metrics, AuditLogs, Accounts…
│       ├── services/           Typed Axios clients for every endpoint
│       └── hooks/              useAuth (Zustand), useQueryCache, usePermissions
│
├── gateway-runtime/            Per-account Node.js/Express isolated gateway
│   └── src/
│       ├── middleware/         sanitize → auth → rateLimit → validate → proxy
│       ├── storage/            L1 Map + L2 better-sqlite3 tiered store
│       └── logger/             Request log buffer → POST /internal/logs (5s flush)
│
├── docker-compose.yml          Dev stack (build-based, hot-reload volumes)
├── docker-compose.prod.yml     Production stack (image-based, no bind mounts)
└── README.md
```

---

## Key Engineering Decisions

| Decision | Choice | Reason |
|---|---|---|
| Per-account isolation | Docker container per account | True process isolation; no shared memory or port space |
| Instance TTL | 48h self-destruct in Node.js | `setTimeout` fires `gracefulShutdown("TTL_EXPIRED")`; APScheduler reaps stragglers |
| Rate limiter backend | Redis sorted-set sliding window | `ratelimit:{account_id}:{sha256(key)}` — exact per-key rpm from `APIKey.metadata_json` |
| Secret storage | Fernet + PBKDF2-HMAC-SHA256 | AES-128 with deterministic key expansion from env vars; `${secret:name}` refs in policies |
| API key hashing | Salted SHA-256 + `hmac.compare_digest` | Constant-time comparison prevents timing attacks |
| Tiered storage | L1→L2→L3 waterfall reads + write-through | Hot-path reads skip DB; survives Redis/Postgres outages gracefully |
| Route reload | `asyncio.create_task(trigger_reload(...))` | Non-blocking; CRUD responses never delayed by gateway network calls |
| Proxy client | `httpx.AsyncClient` pooled (200 conn) | Non-blocking; RFC 7230 hop-by-hop header stripping |
| DB fallback | PostgreSQL → SQLite → in-memory | Tests and dev need zero infrastructure |

---

## Stack

**Backend:** FastAPI · SQLAlchemy 2.0 async · asyncpg · aiosqlite · Redis · httpx · python-jose · cryptography · APScheduler · prometheus-client · Pydantic v2 · Alembic · structlog · Docker SDK

**Frontend:** React 18 · TypeScript · Vite · Material-UI v5 · Recharts · Zustand · Axios

**Gateway Runtime:** Node.js 22 · Express · TypeScript · ioredis · better-sqlite3 · ajv · http-proxy-middleware

**Infrastructure:** PostgreSQL 16 · Redis 7 · Docker Compose · nginx
