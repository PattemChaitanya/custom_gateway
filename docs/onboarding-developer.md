# Developer Onboarding

This guide gets a new developer running the **Mini Cloud Platform / API Gateway** locally in under 10 minutes.

For the full file layout see [file-structure.md](file-structure.md).

---

## Prerequisites

- Python 3.13+
- Node.js 20+
- Docker + Docker Compose (recommended)
- PostgreSQL 16 (optional — SQLite fallback works for dev)
- Redis 7 (optional — rate limiting is fail-open when Redis is unavailable)

---

## Option A — Docker (fastest)

```bash
git clone https://github.com/PattemChaitanya/custom_gateway.git
cd custom_gateway
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Prometheus metrics | http://localhost:8000/metrics |

First login: `admin@example.com` / `changeme123`

---

## Option B — Manual Setup

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment — copy the example and fill in values
cp .env.example .env               # set DATABASE_URL, REDIS_URL, SECRET_KEY

# Generate a Fernet encryption key (copy into .env as ENCRYPTION_KEY)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Run database migrations
alembic upgrade head

# Seed default RBAC roles and permissions
python scripts/seed_rbac.py

# Start the development server
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api/` requests to the backend.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | No | `postgresql+asyncpg://user:pw@host/db` — falls back to SQLite if unset |
| `REDIS_URL` | No | `redis://localhost:6379/0` — rate limiting fails open without Redis |
| `SECRET_KEY` | Yes | Long random string used for JWT signing and key derivation |
| `ENCRYPTION_KEY` | No | Fernet key — derived from SECRET_KEY + ENCRYPTION_SALT if blank |
| `ENCRYPTION_SALT` | No | Salt for PBKDF2 key derivation (default: `gateway-salt`) |
| `FIRST_SUPERUSER_EMAIL` | No | Auto-created admin email on first run |
| `FIRST_SUPERUSER_PASSWORD` | No | Auto-created admin password on first run |

---

## Running Tests

```bash
cd backend

# Full test suite — uses SQLite, no Redis or Postgres required
pytest tests/ -v

# Only the 10-phase end-to-end gateway test
pytest tests/test_e2e_gateway.py -v

# Only the mini-cloud control-plane suite (14 files)
pytest tests/test_mini_cloud_*.py -v

# With coverage report
pytest tests/ --cov=app --cov-report=term-missing
```

Frontend tests:

```bash
cd frontend
npm run test:ci
```

---

## Project Layout Quick Reference

```
backend/app/
├── gateway/          ← proxy pipeline (data plane)
├── control_plane/    ← mini-cloud: registry, scheduler, autoscaler
├── api/              ← REST endpoints
├── authorizers/      ← RBAC: require_permission() dependency
├── rate_limiter/     ← Redis-backed rate limiting
├── load_balancer/    ← LB algorithms + BackendPoolManager
├── security/         ← Fernet encryption, API key hashing
├── metrics/          ← Prometheus + DB-backed MetricsStorage
├── logging/          ← AuditLogger, structlog
├── validation/       ← Input sanitization middleware
└── db/               ← 17 SQLAlchemy models, 4-level fallback
```

See [file-structure.md](file-structure.md) for the full annotated tree.

---

## Key Concepts

**9-step gateway pipeline** (`gateway/router.py` → `pipeline.py`):
1. Resolve API record
2. Lifecycle guard (draft → 503, deprecated → 410)
3. Target resolution (mini-cloud registry → backend pool → deployment → static config)
4. Auth enforcement (API key / JWT / OAuth2)
5. Rate limit enforcement (Redis-backed)
6. Secret injection (`${secret:name}` in connector configs)
7. JSON Schema validation
8. Async proxy (httpx)
9. Tracing headers (`X-Gateway-*`, `X-Request-ID`)

**Mini-cloud control plane** (`control_plane/`):
- `ServiceRegistry` — TTL-based heartbeats, three routing strategies
- `ControlLoopScheduler` — job queue with DLQ and lease ownership
- `AutoscalerLoop` — scale decisions from queue depth + latency signals
- State durability — snapshot to disk, restore on startup
- `GET /mini-cloud/contract` — typed platform guarantees doc

**RBAC** (`authorizers/rbac.py`):
- `require_permission("resource:action")` — FastAPI `Depends()` used on every protected route
- Default roles: `admin`, `developer`, `editor`, `viewer`
- Mini-cloud endpoints require `controlplane:read` (admin role has this by default)
- Superusers bypass all RBAC checks

---

## 🚀 Developer Onboarding

### 1. Prerequisites
