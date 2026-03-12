# File Structure

This document reflects the **actual layout** of the repository as built.

---

## Root

```
custom_gateway/
├── backend/              # FastAPI application
├── frontend/             # React + TypeScript SPA
├── docs/                 # Architecture and RBAC documentation
├── docker-compose.yml    # One-command local stack
└── README.md
```

---

## Backend (`backend/`)

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, router registration, lifespan hooks
│   ├── logging_config.py        # structlog + stdlib JSON logging
│   │
│   ├── api/                     # HTTP route handlers
│   │   ├── apis/                # API CRUD + sub-resources (deployments, auth-policies,
│   │   │                        #   rate-limits, schemas, backend-pools)
│   │   ├── auth/                # register, login, refresh, logout, OTP, /me
│   │   ├── mini_cloud.py        # ~40 control-plane endpoints (requires controlplane:read)
│   │   ├── keys/                # API key CRUD
│   │   ├── secrets.py           # Secret CRUD (Fernet-encrypted)
│   │   ├── connectors.py        # Connector CRUD + test-connection
│   │   ├── authorizers.py       # Role/permission management
│   │   ├── admin.py             # Admin user management
│   │   └── user.py              # User profile + permission listing
│   │
│   ├── gateway/                 # Proxy pipeline (data plane)
│   │   ├── router.py            # Catch-all /gw/{api_id}/{path} — 9-step pipeline
│   │   ├── pipeline.py          # enforce_auth, enforce_rate_limit, enforce_schema_validation
│   │   ├── proxy.py             # httpx pooled async proxy, hop-by-hop stripping
│   │   ├── resolver.py          # Target URL resolution (mini-cloud → LB pool → deployment → static)
│   │   └── secret_injector.py   # ${secret:name} placeholder resolution
│   │
│   ├── control_plane/           # Mini-cloud simulation
│   │   ├── discovery.py         # ServiceRegistry — TTL heartbeats, 3 routing strategies
│   │   ├── scheduler.py         # Job queue — UUID keys, leases, DLQ, backoff
│   │   ├── autoscaler.py        # Signal-driven autoscaler (queue_depth + latency_p95)
│   │   ├── runtime.py           # Module singletons, snapshot/restore, control loop tick
│   │   ├── policies.py          # JSON policy config — hot-reload without restart
│   │   ├── failure_injection.py # 4 chaos helpers (stale heartbeat, crash, slow, burst)
│   │   └── contracts.py         # Typed platform contract (guarantees + tradeoffs)
│   │
│   ├── authorizers/             # RBAC
│   │   ├── rbac.py              # RBACManager, require_permission(), require_role()
│   │   ├── middleware.py        # Register authorization middleware
│   │   └── init.py              # Seed default roles + permissions on startup
│   │
│   ├── rate_limiter/            # Production Redis-backed rate limiting
│   │   ├── algorithms.py        # FixedWindow, SlidingWindow, TokenBucket (async Redis)
│   │   ├── manager.py           # DB CRUD for RateLimit records
│   │   └── middleware.py        # FastAPI middleware registration
│   │
│   ├── rate_limiting/           # DEPRECATED — test-only in-memory strategies
│   │   └── strategies.py        # Synchronous shims for unit tests; do not use in app code
│   │
│   ├── load_balancer/           # Production load balancing
│   │   ├── algorithms.py        # RoundRobin, LeastConnections, Weighted
│   │   ├── pool.py              # BackendPoolManager (DB-backed)
│   │   └── health.py            # HealthChecker (httpx)
│   │
│   ├── load_balancing/          # DEPRECATED — test-only compatibility wrappers
│   │   └── algorithms.py        # Thin wrappers around load_balancer/ for legacy test imports
│   │
│   ├── security/
│   │   ├── encryption.py        # Fernet encrypt/decrypt, PBKDF2 key derivation
│   │   ├── secrets.py           # SecretsManager (store, rotate, decrypt)
│   │   └── api_keys.py          # Salted SHA-256 hashing, constant-time compare
│   │
│   ├── metrics/
│   │   ├── prometheus.py        # Prometheus counters/histograms
│   │   ├── middleware.py        # X-Response-Time header, request counting
│   │   └── storage.py           # MetricsStorage — DB-backed Metric rows, summary queries
│   │
│   ├── logging/
│   │   ├── audit.py             # AuditLogger — writes AuditLog rows per action
│   │   ├── db_handler.py        # Python logging.Handler → DB
│   │   └── cleanup.py           # Scheduled cleanup of old logs and metrics
│   │
│   ├── validation/
│   │   ├── validators.py        # Path param, query param, XSS, SQL injection detection
│   │   ├── sanitizers.py        # HTML/SQL/NoSQL sanitization
│   │   └── middleware.py        # Body size limit, JSON depth, header sanitization
│   │
│   ├── connectors/
│   │   ├── database.py          # AsyncPostgreSQL connector (asyncpg pool)
│   │   └── manager.py           # ConnectorManager CRUD + test_connection()
│   │
│   └── db/
│       ├── models.py            # 17 SQLAlchemy models
│       ├── connector.py         # 4-level connection fallback (PG → Secrets Manager → SQLite → memory)
│       └── progress_sql.py      # Migration state tracking
│
├── alembic/                     # 7 migration versions
├── config/
│   └── policies.v1.json         # Hot-reloadable gateway routing policies
├── data/
│   └── control_plane_state.json # Control-plane snapshot (written on shutdown)
├── tests/                       # 35 test files
├── scripts/                     # seed_rbac.py, generate_env.py, cleanup scripts
├── requirements.txt
├── alembic.ini
└── Dockerfile
```

---

## Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx / Register.tsx / ResetPassword.tsx / VerifyOtp.tsx
│   │   ├── Dashboard.tsx        # Stats cards + status distribution bar (live from /metrics/summary)
│   │   ├── Routes.tsx           # API list page
│   │   ├── APIDetail.tsx        # Tabbed: deployments, auth-policies, rate-limits, schemas, backend-pools
│   │   ├── CreateAPI.tsx        # Create / edit form
│   │   ├── APIKeys.tsx          # API key CRUD
│   │   ├── Secrets.tsx          # Secret CRUD + decrypt/rotate dialogs
│   │   ├── AuditLogs.tsx        # Filtered paginated audit log table
│   │   ├── Connectors.tsx       # Connector CRUD + test-connection
│   │   ├── Authorizers.tsx      # Role/permission management
│   │   ├── Environments.tsx     # Environment CRUD
│   │   └── MiniCloud.tsx        # Control-plane panel (registry, scheduler, autoscaler, policies, chaos)
│   │
│   ├── components/
│   │   ├── PageWrapper.tsx      # Consistent layout wrapper
│   │   ├── ProtectedRoute.tsx   # Redirects unauthenticated users
│   │   ├── PermissionGuard.tsx  # RBAC-conditional rendering
│   │   └── Skeletons.tsx        # TableSkeleton, StatCardsSkeleton
│   │
│   ├── services/                # Typed axios API clients
│   │   ├── api.ts               # Axios instance + auth interceptor
│   │   ├── apis.ts              # API CRUD + all sub-resources
│   │   ├── auth.ts              # login, register, logout, refresh, me
│   │   ├── apiKeys.ts           # list, generate, revoke
│   │   ├── auditLogs.ts         # list with filters, stats
│   │   ├── authorizers.ts       # CRUD
│   │   ├── connectors.ts        # list, create, update, delete, test
│   │   ├── metrics.ts           # getMetricsSummary()
│   │   ├── miniCloud.ts         # All ~40 control-plane endpoints
│   │   ├── secrets.ts           # list, create, rotate, view, delete
│   │   └── users.ts             # list, roles
│   │
│   └── hooks/
│       ├── useAuth.ts           # Zustand auth store
│       └── useQueryCache.ts     # Local fetch cache + refetch
│
├── Dockerfile                   # Multi-stage: Vite build → nginx serve
└── nginx.conf                   # SPA fallback + /api/ proxy to backend
```

---

## Test Layout (`backend/tests/`)

| Category | Files | What is tested |
|---|---|---|
| Gateway e2e | `test_e2e_gateway.py` | Full 10-phase pipeline via in-process ASGI client |
| Mini-cloud | `test_mini_cloud_*.py` (14 files) | Registry TTL, scheduler DLQ, autoscaler signals, chaos invariants, SLO simulation, state durability |
| Auth | `test_auth.py`, `test_auth_expiry.py`, `test_mobile_otp.py`, `test_refresh_pruning.py` | Register/login/OTP/token expiry |
| RBAC | `test_authorization.py` | Role/permission assignment and enforcement |
| Rate limiting | `test_rate_limiting.py` | Algorithm correctness (FixedWindow, SlidingWindow, TokenBucket) |
| Load balancing | `test_load_balancing.py` | RoundRobin, LeastConnections, Weighted selection |
| Security | `test_api_keys.py`, `test_secrets.py` | Hashing, encryption, CRUD |
| Observability | `test_audit_logging.py`, `test_metrics.py` | DB persistence |
| Integration | `test_api_crud.py`, `test_api_integration.py`, `test_connectors.py` | HTTP CRUD routes |

---

## 📁 Root Structure

```bash
monorepo/
│── backend/              # Python backend (monolithic core)
│── frontend/             # React/Next.js frontend
│── docs/                 # Documentation (architecture, ADRs, API contracts)
│── scripts/              # Automation scripts (setup, CI/CD helpers)
│── tests/                # Centralized integration/e2e tests
│── configs/              # Configurations shared across backend & frontend
│── .github/              # GitHub workflows & actions (CI/CD)
│── .gitignore
│── requirements.txt      # Backend Python dependencies
│── package.json          # Frontend dependencies (if standalone React/Next.js)
│── README.md             # Project overview
│── FILE_STRUCTURE.md     # This document
```

---

## 🐍 Backend Structure (Python Monolith)

```bash
backend/
│── app/                  # Core application code
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── api/              # REST endpoints / Controllers
│   ├── services/         # Business logic layer
│   ├── models/           # Database models / ORM
│   ├── schemas/          # Pydantic/Marshmallow schemas (validation)
│   ├── repositories/     # Data access layer (DB queries)
│   ├── utils/            # Helper functions
│   └── middlewares/      # Request/response middlewares
│
│── config/               # Environment configs (dev, prod, test)
│   ├── settings.py
│   └── logging.py
│
│── migrations/           # DB migration scripts
│── tests/                # Unit tests (backend-specific)
│── requirements/         # Split dependency files (base, dev, prod)
│── Dockerfile            # Backend Docker config
```

### ✅ Notes:

* **`api/`** → Handles routing, maps HTTP requests to services.
* **`services/`** → Business logic, independent of DB.
* **`repositories/`** → DB operations, keeps persistence separate.
* **`schemas/`** → Ensures request/response validation.
* **`middlewares/`** → For auth, logging, request validation.

---

## ⚛️ Frontend Structure (React/Next.js)

```bash
frontend/
│── public/               # Static assets (images, fonts, icons)
│── src/
│   ├── components/       # Reusable UI components
│   ├── pages/            # Page-level components (Next.js: routing)
│   ├── layouts/          # Page layouts
│   ├── hooks/            # Custom React hooks
│   ├── contexts/         # Global state/context API
│   ├── services/         # API calls (fetch/Axios)
│   ├── utils/            # Utility functions
│   ├── styles/           # CSS/SCSS/Tailwind files
│   └── tests/            # Unit tests (Jest/RTL)
│
│── next.config.js        # Next.js config (if using Next.js)
│── vite.config.js        # Vite config (if using Vite)
│── package.json
│── tsconfig.json         # TypeScript config (if applicable)
```

### ✅ Notes:

* **`components/`** → Shared building blocks (buttons, inputs, modals).
* **`pages/`** → Each file becomes a route (Next.js) or router mapping (CRA/Vite).
* **`services/`** → Keeps API logic separated from UI.
* **`contexts/`** → For global state management.
* **`layouts/`** → Defines global layouts (header/footer/sidebar).

---

## 🧪 Centralized Tests

```bash
tests/
│── e2e/                  # End-to-end tests (Cypress/Playwright)
│── integration/          # Tests that span backend & frontend
│── performance/          # Load/performance testing scripts
```

---

## ⚙️ Configurations

```bash
configs/
│── nginx/                # Reverse proxy configs
│── docker/               # Docker Compose, multi-stage builds
│── env/                  # .env.example files for environments
│── monitoring/           # Grafana/Prometheus configs
```

---

## 🚀 Deployment

* **Backend** → Deployed as a containerized Python app (Docker + Gunicorn + Nginx).
* **Frontend** → Built & deployed as static files (served via Nginx/CDN).
* **CI/CD** → GitHub Actions pipeline inside `.github/workflows`.

---

## 🔑 Key Takeaways

* Single repo (**monorepo**) → Easier coordination between frontend & backend.
* **Clear separation** inside backend (api, services, repos, models).
* **Frontend isolated** but still part of repo.
* **Shared configs & docs** at root for collaboration.
* **Centralized testing** ensures backend + frontend integration stability.
