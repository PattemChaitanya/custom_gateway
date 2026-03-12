# Mini Cloud Platform — API Gateway

A **reference implementation of a cloud API gateway** built on a single node. It demonstrates production cloud engineering patterns: service discovery, job scheduling, signal-driven autoscaling, multi-algorithm rate limiting, three auth modes, and Fernet-encrypted secrets — all wired through a 9-step async proxy pipeline.

> "A cloud built on one machine can still teach the same lessons as a cloud built on ten thousand. The physics change, but the ideas remain gloriously the same."

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLIENT REQUEST                              │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     GATEWAY PROXY PIPELINE                           │
│                                                                      │
│  1. Resolve API ──► 2. Lifecycle Guard ──► 3. Target Resolution      │
│        │                   │                       │                 │
│        │            draft→503            mini-cloud registry         │
│        │            deprecated→410       backend pool LB             │
│        │                                deployment override          │
│        │                                static config                │
│        ▼                   ▼                       ▼                 │
│  4. Auth Policy ──► 5. Rate Limit ──► 6. Secret Injection            │
│        │                   │                       │                 │
│     API Key             Fixed Window        ${secret:name}           │
│     JWT/Bearer          Sliding Window      Fernet-encrypted         │
│     OAuth2              Token Bucket        from DB secrets          │
│     (RFC 7662)          (Redis-backed)                               │
│        ▼                   ▼                       ▼                 │
│  7. Schema Validation ──► 8. Proxy ──► 9. Tracing Headers            │
│        │                   │                       │                 │
│     JSON Draft 7       httpx async          X-Gateway-*              │
│     field-level        pooled client        X-Request-ID             │
│     422 errors         200 connections                               │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
    ┌─────────────┐   ┌─────────────┐  ┌────────────────┐
    │   Backend   │   │  Backend    │  │  Mini-Cloud    │
    │   Pool #1   │   │  Pool #2    │  │  ServiceReg.   │
    │  (weighted) │   │  (rr)       │  │  (TTL-based)   │
    └─────────────┘   └─────────────┘  └────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                      MINI-CLOUD CONTROL PLANE                        │
│                                                                      │
│   ServiceRegistry ──► ControlLoopScheduler ──► AutoscalerLoop        │
│   (TTL heartbeats)    (job queue + DLQ +      (queue_depth +         │
│   (3 LB strategies)    lease ownership +       latency_p95 signals + │
│                        exp-backoff retries)     cooldown + min/max)  │
│                                                                      │
│   PolicyConfig ──► hot-reload from disk (no restart)                 │
│   FailureInjection ──► stale-heartbeat / worker-crash /              │
│                         slow-downstream / burst-traffic              │
│   State Durability ──► snapshot() / restore() across restarts        │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                          OBSERVABILITY                               │
│                                                                      │
│  Prometheus metrics (/metrics)   DB-backed Metric rows               │
│  Structlog JSON logs             AuditLog per action                 │
│  X-Response-Time header          X-Request-ID tracing                │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start (Docker — recommended)

```bash
# Clone and start everything in one command
git clone https://github.com/PattemChaitanya/custom_gateway.git
cd custom_gateway
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API (FastAPI) | http://localhost:8000 |
| Interactive docs | http://localhost:8000/docs |
| Prometheus metrics | http://localhost:8000/metrics |

First login: `admin@example.com` / `changeme123`

---

## Manual Setup (development)

### Prerequisites
- Python 3.13+
- PostgreSQL 14+
- Redis 7+

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Set environment
cp .env.example .env             # edit DATABASE_URL, REDIS_URL, SECRET_KEY

# Run migrations and start
alembic upgrade head
uvicorn app.main:app --reload
```

```bash
# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## 📂 Project Structure

```bash
Gateway management/
├── backend/                     # Python FastAPI backend
│   ├── app/
│   │   ├── api/                 # API endpoints
│   │   │   ├── keys/           # API key management
│   │   │   └── ...
│   │   ├── authorizers/        # RBAC/ABAC authorization
│   │   ├── connectors/         # Database/Queue/Storage connectors
│   │   ├── load_balancer/      # Load balancing algorithms
│   │   ├── logging/            # Audit logging
│   │   ├── metrics/            # Prometheus metrics
│   │   ├── rate_limiter/       # Rate limiting
│   │   ├── security/           # API keys, secrets, encryption
│   │   ├── validation/         # Input validation & sanitization
│   │   └── db/                 # Database models
│   ├── alembic/                # 7 migration versions
│   ├── tests/                  # 35 test files — real algorithmic assertions
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/             # Dashboard, APIs, APIDetail, MiniCloud, Secrets, AuditLogs ...
│   │   ├── services/          # Typed API clients for every backend endpoint
│   │   ├── components/        # ProtectedRoute, PermissionGuard, Skeletons
│   │   └── hooks/             # useAuth (Zustand), useQueryCache
│   ├── Dockerfile
│   └── nginx.conf
│
├── docs/                      # RBAC guide, database architecture, platform contract
├── docker-compose.yml         # One-command local stack
└── README.md
```

---

## Key Engineering Decisions

| Decision | Choice | Reason |
|---|---|---|
| Rate limiter backend | Redis async | Distributed; in-memory strategies kept for unit tests only |
| Auth enforcement | `Depends(require_permission())` | Compile-time route guard, not runtime string matching |
| Secret storage | Fernet + PBKDF2-HMAC-SHA256 (100k iterations) | AES-128 with deterministic key expansion from env vars |
| API key hashing | Salted SHA-256 + `hmac.compare_digest` | Constant-time comparison prevents timing attacks |
| Control-plane state | JSON snapshot/restore on disk | Survives restarts without a dedicated state store |
| DB fallback | PostgreSQL → SQLite → in-memory | Tests and dev need zero infrastructure |
| Proxy client | `httpx.AsyncClient` pooled (200 conn) | Non-blocking, RFC 7230 hop-by-hop header stripping |

---

## Stack

**Backend:** FastAPI 0.109 · SQLAlchemy 2.0 async · asyncpg · Redis 7 · httpx · python-jose · cryptography · prometheus-client · Pydantic 2 · Alembic · structlog

**Frontend:** React 18 · TypeScript · Vite · Material-UI · Zustand · Axios

**Infrastructure:** PostgreSQL 16 · Redis 7 · Docker Compose · nginx

---

## Running Tests

```bash
cd backend
pytest tests/ -v                     # full suite (SQLite, no Redis required)
pytest tests/test_e2e_gateway.py     # 10-phase end-to-end pipeline test
pytest tests/test_mini_cloud_*.py    # control plane suite (14 files)
```

---

## Documentation

- [docs/mini-cloud-platform-contract.md](docs/mini-cloud-platform-contract.md) — platform guarantees, tradeoffs, SLOs
- [docs/rbac-authorization-guide.md](docs/rbac-authorization-guide.md) — RBAC roles, permissions, setup
- [docs/database-architecture-diagram.md](docs/database-architecture-diagram.md) — connection priority chain

* **Python 3.10+** installed
* **Node.js 18+** installed
* **Docker & Docker Compose** installed
* **PostgreSQL** (local or containerized)

### 2. Clone the Repository

```bash
git clone <repo-url>
cd repo-root
```

### 3. Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Run backend locally:

```bash
python src/main.py
```

### 4. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will run on `http://localhost:5173` (or defined port).

### 5. Run with Docker Compose

```bash
docker-compose up --build
```

This spins up backend, frontend, and database containers.

### 6. Testing

* Backend tests: `pytest backend/tests`
* Frontend tests: `npm run test`
* Load testing: `locust -f tests/load_test.py`

### 7. CI/CD

* PR triggers GitHub Actions: lint, test, build
* Merges auto-deploy to **staging**
* Manual approval deploys to **production**

### 8. Useful Commands

* `scripts/setup.sh` → initial setup
* `scripts/start-dev.sh` → run backend + frontend together
* `scripts/lint.sh` → run linting across repo

---

✅ This setup ensures backend + frontend live inside one monorepo with **clear boundaries, shared tooling, and smooth onboarding**.
