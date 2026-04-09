## Full Project Architecture — Gateway Management Platform

### 1. System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          GATEWAY MANAGEMENT PLATFORM                         │
│                                                                              │
│   An API gateway with management UI, supporting proxy routing, auth,         │
│   rate limiting, load balancing, secret management, RBAC, audit logging,     │
│   and a mini-cloud control plane with service discovery & autoscaling.       │
└──────────────────────────────────────────────────────────────────────────────┘
```

```
                        ┌─────────────────┐
                        │    Clients      │
                        │  (Browser/API)  │
                        └────────┬────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
    ┌────────────────────────┐      ┌────────────────────────────┐
    │     FRONTEND (SPA)     │      │    GATEWAY DATA PLANE      │
    │  React + MUI + Vite    │      │  /gw/{api_id}/{path}       │
    │  Management Dashboard  │      │  Proxy → Upstream Services │
    │  Port 80 (Nginx)       │      │                            │
    └───────────┬────────────┘      └─────────────┬──────────────┘
                │ /api/* proxy                    │
                ▼                                 │
    ┌─────────────────────────────────────────────┴──────────────┐
    │                  BACKEND (FastAPI)                         │
    │                  Port 8000 (Uvicorn)                       │
    │                                                            │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
    │  │ Auth     │ │ API CRUD │ │ Gateway  │ │ Control Plane│   │
    │  │ Module   │ │ Module   │ │ Proxy    │ │ (Mini-Cloud) │   │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘   │
    │       │             │            │              │          │
    │  ┌────┴─────────────┴────────────┴──────────────┴───────┐  │
    │  │              8-Layer Middleware Pipeline             │  │
    │  └──────────────────────┬───────────────────────────────┘  │
    └─────────────────────────┼──────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
    │ PostgreSQL  │  │    Redis     │  │  Upstream    │
    │ (Primary DB)│  │ (Rate Limit) │  │  Services    │
    │ Port 5432   │  │  Port 6379   │  │  (backends)  │
    └─────────────┘  └──────────────┘  └──────────────┘
```

---

### 2. Technology Stack & Decisions

#### Backend

| Choice | Technology | Why (over alternatives) |
|--------|-----------|------------------------|
| **Framework** | **FastAPI** (Python 3.13) | Async-native, auto OpenAPI docs, Pydantic validation, dependency injection. Over Django (too heavy, sync-first), Flask (no async, no DI), Express (JS ecosystem mismatch) |
| **ASGI Server** | **Uvicorn** | Fastest Python ASGI server (libuv event loop). Over Gunicorn (sync workers), Hypercorn (less mature) |
| **ORM** | **SQLAlchemy 2.0 async** | Mature, async-first with `asyncpg`, powerful relationship loading. Over Tortoise ORM (less mature), Django ORM (sync), raw SQL (unmaintainable) |
| **DB Driver** | **asyncpg** | Fastest PostgreSQL driver for Python (C-level, zero-copy). Over psycopg3 (slower async), aiopg (deprecated) |
| **HTTP Client** | **httpx** | Async, connection pooling, HTTP/2 support. Over aiohttp (harder API), requests (sync only) |
| **JWT** | **python-jose** | Compact, supports HS256/RS256, audited. Over PyJWT (fewer algorithms), authlib (heavier) |
| **Encryption** | **cryptography (Fernet)** | Authenticated symmetric encryption, NIST-backed. Over PyCryptodome (lower-level), nacl (less common) |
| **Rate Limiting** | **Redis + custom algorithms** | Distributed, atomic operations, TTL support. Over in-memory (not distributed), Nginx rate limiting (less flexible) |
| **Logging** | **structlog** | Structured JSON output, processor pipelines. Over stdlib logging (unstructured), loguru (less configurable) |
| **Metrics** | **prometheus-client** | Industry standard, Grafana-compatible. Over StatsD (requires aggregator), custom (reinventing wheel) |
| **Migrations** | **Alembic** | SQLAlchemy-native, async support, autogenerate. Over Django migrations (wrong ecosystem), Flyway (Java) |

#### Frontend

| Choice | Technology | Why (over alternatives) |
|--------|-----------|------------------------|
| **UI Library** | **React 18** | Component model, ecosystem, concurrent features. Over Vue (smaller ecosystem), Svelte (less mature), Angular (overengineered for this) |
| **Build Tool** | **Vite 7** | Instant HMR, ESM-native, fast builds. Over Webpack (slow, complex config), Parcel (less control), CRA (deprecated) |
| **UI Components** | **Material-UI (MUI) 5** | Complete design system, accessible, themeable. Over Ant Design (heavier), Chakra (less components), Tailwind (utility-only, no components) |
| **State** | **Zustand** | 1KB, no boilerplate, hook-based. Over Redux (verbose), MobX (complex), Context API (re-render problems at scale) |
| **HTTP Client** | **Axios** | Interceptors for auth refresh, request cancellation. Over fetch (no interceptors natively), ky (less ecosystem), SWR (data-fetching only) |
| **Styling** | **Emotion (CSS-in-JS)** | MUI's runtime engine, scoped styles, theme-aware. Over styled-components (different engine), Tailwind (class-based), CSS modules (no theme system) |
| **Testing** | **Jest + Testing Library + MSW** | Component testing + API mocking. Over Vitest (MUI compat issues), Cypress (E2E only), Playwright (E2E focus) |

#### Infrastructure

| Choice | Technology | Why |
|--------|-----------|-----|
| **Primary DB** | **PostgreSQL 16** | ACID, JSON support, rich indexing, production-proven. Over MySQL (weaker JSON, fewer features), MongoDB (no ACID by default) |
| **Cache/Queue** | **Redis 7** | Sub-millisecond ops, atomic counters, sorted sets for sliding windows. Over Memcached (no data structures), DynamoDB (cost, latency) |
| **Containerization** | **Docker + Compose** | Reproducible builds, service orchestration. Over K8s (overkill for single-node), Podman (less tooling) |
| **Reverse Proxy** | **Nginx** | Static asset serving, API proxying, gzip. Over Caddy (less battle-tested), Traefik (K8s-oriented) |
| **Cloud** | **AWS EC2 + RDS** | Managed Postgres, VPC isolation, SSH tunneling. Over Heroku (cost), Lambda (cold starts for gateway), ECS (complexity) |

---

### 3. Database Architecture (25 Models)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE SCHEMA                                    │
│                                                                              │
│  ┌─────────┐    ┌───────────┐    ┌──────────┐    ┌──────────────┐            │
│  │  User   │◄──►│ UserRole  │───►│   Role   │───►│ Permission   │            │
│  │         │    └───────────┘    │          │    │ (resource:   │            │
│  │ email   │                     │ name     │    │  action)     │            │
│  │ hash_pw │    ┌───────────┐    │ perms[]  │    └──────────────┘            │
│  │ is_super│◄───│RefreshTkn │    └──────────┘                                │
│  │ is_actv │    │ jti_hash  │                                                │
│  │ roles   │    │ revoked   │    ┌──────────────────────────────┐            │
│  └────┬────┘    └───────────┘    │           API                │            │
│       │                          │  name, version, base_url     │            │
│       │         ┌───────────┐    │  lifecycle: draft→active→    │            │
│       ├────────►│   OTP     │    │            deprecated        │            │
│       │         │ otp_hash  │    └──────┬───────────────────────┘            │
│       │         │ expires   │           │                                    │
│       │         │ attempts  │    ┌──────┴──────────────────────┐             │
│       │         └───────────┘    │                             │             │
│       │                     ┌────┴─────┐ ┌────────┐ ┌────────┐ │             │
│       │         ┌──────────►│AuthPolicy│ │RateLmt │ │ Schema │ │             │
│       │         │           │ type:    │ │ algo:  │ │ json   │ │             │
│       └─────────┤           │ apiKey/  │ │ fixed/ │ │ schema │ │             │
│                 │           │ jwt/     │ │ slide/ │ │ draft7 │ │             │
│  ┌──────────┐   │           │ oauth2/  │ │ token  │ └────────┘ │             │
│  │  APIKey  │───┘           │ open     │ └────────┘            │             │
│  │ key_hash │               └──────────┘                       │             │
│  │ scopes   │                                                  │             │
│  │ revoked  │   ┌─────────────┐  ┌──────────────┐              │             │
│  │ expires  │   │BackendPool  │  │APIDeployment │              │             │
│  │ env_id   │   │ algorithm:  │  │ env_id       │◄─────────────┘             │
│  └──────────┘   │ round-robin/│  │ status       │                            │
│                 │ least-conn/ │  │ target_url   │     ┌──────────────┐       │
│  ┌──────────┐   │ weighted    │  └──────────────┘     │ Environment  │       │
│  │  Secret  │   └──────┬──────┘                       │ name, slug   │       │
│  │ name     │          │          ┌──────────────┐    │ base_url     │       │
│  │ enc_val  │   ┌──────┴───────┐  │ LoadBalancer │    └──────────────┘       │
│  │ tags     │   │   Backend    │  │ pool_id      │                           │
│  └──────────┘   │ url, weight  │  │ strategy     │    ┌──────────────┐       │
│                 │ healthy      │  │ health_url   │    │  Connector   │       │
│  ┌──────────┐   └──────────────┘  └──────────────┘    │ type: pg/    │       │
│  │ AuditLog │                                         │ mongo/redis/ │       │
│  │ action   │   ┌──────────────┐  ┌──────────────┐    │ s3/kafka     │       │
│  │ user_id  │   │   Metric     │  │ModuleMetadata│    │ config{}     │       │
│  │ resource │   │ name, value  │  │ name, version│    └──────────────┘       │
│  │ metadata │   │ labels       │  │ description  │                           │
│  │ status   │   │ timestamp    │  │ enabled      │                           │
│  └──────────┘   └──────────────┘  └──────────────┘                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Database Resilience — 3-Tier Fallback:**

```
┌───────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  PostgreSQL       │────►│  SQLite (WAL)    │────►│  In-Memory       │
│  asyncpg          │fail │  aiosqlite       │fail │  SimpleNamespace │
│  pool: 5+10 ovf   │     │  10s timeout     │     │  dict-backed     │
│  pre_ping: true   │     │  persistent file │     │  test/dev only   │
│  recycle: 3600s   │     │                  │     │                  │
└───────────────────┘     └──────────────────┘     └──────────────────┘
```

---

### 4. Caching Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         CACHING LAYERS                                       │
│                                                                              │
│  Layer 1: BROWSER (Frontend)                                                 │
│  ┌────────────────────────────────────────────────────────────────┐          │
│  │  useQueryCache Hook (in-memory Map)                            │          │
│  │  • TTL: 2 minutes per cache key                                │          │
│  │  • invalidateCache(key) / invalidateCacheByPrefix(prefix)      │          │
│  │  • Cleared on page refresh                                     │          │
│  │  • Prevents duplicate API calls within TTL window              │          │
│  └────────────────────────────────────────────────────────────────┘          │
│                                                                              │
│  Layer 2: VITE BUILD (Static Assets)                                         │
│  ┌────────────────────────────────────────────────────────────────┐          │
│  │  Manual Chunk Splitting (vendor-react, vendor-mui,             │          │
│  │  vendor-utils, vendor-state) → long-term browser cache         │          │
│  │  Content-hashed filenames → cache bust on deploy only          │          │
│  └────────────────────────────────────────────────────────────────┘          │
│                                                                              │
│  Layer 3: REDIS (Backend - Distributed)                                      │
│  ┌────────────────────────────────────────────────────────────────┐          │
│  │  Rate Limiting Counters Only:                                  │          │
│  │  • Fixed Window: rate_limit:fixed:{key}:{window} (counter)     │          │
│  │  • Sliding Window: rate_limit:sliding:{key} (sorted set)       │          │
│  │  • Token Bucket: rate_limit:token:{key} (hash: tokens+ts)      │          │
│  │  • Max 20 connections, 0.5s timeout, singleton client          │          │
│  │  • TTL = window_seconds (auto-expire stale keys)               │          │
│  └────────────────────────────────────────────────────────────────┘          │
│                                                                              │
│  Layer 4: CONNECTION POOLS (Backend - Process)                               │
│  ┌────────────────────────────────────────────────────────────────┐          │
│  │  PostgreSQL: asyncpg pool (5 base + 10 overflow, pre_ping)     │          │
│  │  httpx: Persistent AsyncClient (200 max conn, 50 keepalive)    │          │
│  │  Redis: Singleton client (20 max connections)                  │          │
│  │  Connectors: Class-level cache (shared across requests)        │          │
│  └────────────────────────────────────────────────────────────────┘          │
│                                                                              │
│  Layer 5: IN-MEMORY (Backend - Process)                                      │
│  ┌────────────────────────────────────────────────────────────────┐          │
│  │  Control Plane State: Service registry, autoscaler,            │          │
│  │    job scheduler (saved to disk on shutdown, restored on start)│          │
│  │  Mini-Cloud Rate Limiter: _rate_window_cache dict (per-policy) │          │
│  │  Password Reset Tokens: _PASSWORD_RESET_TOKENS dict            │          │
│  │  OTP Fallback: In-memory dict when DB unavailable              │          │
│  └────────────────────────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**What's NOT cached (explicit by-design decisions):**
- DB query results — each request fetches fresh (consistency > performance)
- JWT tokens — stateless validation via signature (no lookup cache)
- User sessions — no server-side session store (JWT-based)
- API responses — no HTTP response caching layer (gateway is a pass-through proxy)

---

### 5. Middleware Pipeline (Request Flow)

```
                           Incoming HTTP Request
                                   │
                                   ▼
  ┌─────────── MIDDLEWARE ONION (outermost → innermost) ──────────────┐
  │                                                                   │
  │  ① CORS ────────────────────────────────────────────────────────  │
  │  │  Preflight OPTIONS handling                                    │
  │  │  Access-Control-Allow-* headers                                │
  │  ▼                                                                │
  │  ② AUTHORIZATION ───────────────────────────────────────────────  │
  │  │  Extract JWT from Authorization header or access_token cookie  │
  │  │  Best-effort decode → request.state.user                       │
  │  │  Silent fail (route deps enforce 401)                          │
  │  ▼                                                                │
  │  ③ AUDIT ───────────────────────────────────────────────────────  │
  │  │  Map (method, path) → semantic event (api:create, auth:login)  │
  │  │  Capture user_id, IP, user-agent, duration, status             │
  │  │  Async DB write via dedicated session                          │
  │  ▼                                                                │
  │  ④ RATE LIMITER ────────────────────────────────────────────────  │
  │  │  Skip: /health, /metrics, /docs, /openapi.json                 │
  │  │  Key: user:{id} > apikey:{prefix} > ip:{addr}                  │
  │  │  Redis check → 429 + Retry-After or add X-RateLimit-* headers  │
  │  │  Fail-open if Redis unavailable                                │
  │  ▼                                                                │
  │  ⑤ METRICS ─────────────────────────────────────────────────────  │
  │  │  Prometheus: counter, histogram (12 buckets), gauge            │
  │  │  X-Response-Time header                                        │
  │  ▼                                                                │
  │  ⑥ INPUT VALIDATION ────────────────────────────────────────────  │
  │  │  Body: 10MB limit, JSON depth ≤10, keys ≤1000, array ≤10000    │
  │  │  Threats: SQL injection, XSS, path traversal, CRLF patterns    │
  │  │  400 on violation                                              │
  │  ▼                                                                │
  │  ⑦ REQUEST ID ──────────────────────────────────────────────────  │
  │  │  Generate/propagate X-Request-ID (UUID)                        │
  │  ▼                                                                │
  │  ⑧ REQUEST LOGGING ────────────────────────────────────────────   │
  │  │  Structured JSON: method, path, status, duration               │
  │  │  Redacts Authorization header values                           │
  │  ▼                                                                │
  │  ┌──────────────────────────────────────────────────────────┐     │
  │  │                    ROUTE HANDLERS                        │     │
  │  └──────────────────────────────────────────────────────────┘     │
  └───────────────────────────────────────────────────────────────────┘
```

---

### 6. Gateway Proxy Pipeline (Data Plane)

```
  GET /gw/{api_id}/users/42?env=production
                    │
  ┌─────────────────┴──────────────────────────────────────────────┐
  │                                                                │
  │  Step 1: Resolve API (eager-load policies, pools, schemas)     │
  │  ────────────────────────────────────────────────────────────  │
  │  SELECT * FROM apis WHERE id = ? (with joinedload)             │
  │  404 if not found                                              │
  │                                                                │
  │  Step 2: Lifecycle Gate                                        │
  │  ────────────────────────────────────────────────────────────  │
  │  draft → 503 "API not published"                               │
  │  deprecated → 410 "API deprecated"                             │
  │  active → continue                                             │
  │                                                                │
  │  Step 3: Resolve Target URL                                    │
  │  ────────────────────────────────────────────────────────────  │
  │  Priority:                                                     │
  │    ① Mini-cloud service registry (in-memory discovery)         │
  │    ② BackendPool + LoadBalancer (round-robin/least-conn/wt)    │
  │    ③ Environment-specific target_url_override                  │
  │    ④ Static API.base_url                                       │
  │                                                                │
  │  Step 4: Enforce Auth Policy                                   │
  │  ────────────────────────────────────────────────────────────  │
  │  open    → pass-through                                        │
  │  apiKey  → X-API-Key header → SHA256 hash → DB lookup          │
  │  jwt     → Bearer token → decode → verify sig, exp, iss, aud   │
  │  oauth2  → POST introspection endpoint → check active=true     │
  │  Secrets resolved: ${secret:name} → Fernet decrypt             │
  │                                                                │
  │  Step 5: Per-API Rate Limit                                    │
  │  ────────────────────────────────────────────────────────────  │
  │  Key: gw:api:{id}:{key_type}                                   │
  │  Check DB-configured limits per algorithm                      │
  │  429 + Retry-After on exceed                                   │
  │                                                                │
  │  Step 6: Inject Connector Secrets                              │
  │  ────────────────────────────────────────────────────────────  │
  │  Replace ${secret:name} in headers/query params                │
  │  Fernet-decrypt from secrets table                             │
  │                                                                │
  │  Step 7: Schema Validation (POST/PUT/PATCH)                    │
  │  ────────────────────────────────────────────────────────────  │
  │  JSON Schema Draft 7 validation against API.schema             │
  │  422 on failure                                                │
  │                                                                │
  │  Step 8: Proxy to Upstream                                     │
  │  ────────────────────────────────────────────────────────────  │
  │  httpx.AsyncClient (persistent, pooled)                        │
  │    max_connections: 200                                        │
  │    max_keepalive:    50                                        │
  │    keepalive_expiry: 30s                                       │
  │    connect_timeout:   5s                                       │
  │    read_timeout:     30s                                       │
  │  Strip hop-by-hop headers (RFC 7230)                           │
  │  Forward: method, path, query, headers, body                   │
  │  502 on ConnectionError, 504 on Timeout                        │
  │                                                                │
  │  Step 9: Response                                              │
  │  ────────────────────────────────────────────────────────────  │
  │  Upstream status + body + headers                              │
  │  + X-Gateway-RequestId                                         │
  │  + X-Gateway-ApiId                                             │
  │  + X-Gateway-Latency-Ms                                        │
  │  + X-Gateway-Url-Source                                        │
  │  + X-RateLimit-Limit / Remaining / Reset                       │
  └────────────────────────────────────────────────────────────────┘
```

---

### 7. Authentication & Authorization Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION MECHANISMS                                 │
│                                                                              │
│  ┌─── Management Plane ───────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  Login → PBKDF2-SHA256 password verify → JWT (HS256)                   │  │
│  │          Access Token (24h) + Refresh Token (7d, HttpOnly cookie)      │  │
│  │          Refresh: old JTI revoked, new pair issued                     │  │
│  │          Max 5 active refresh tokens per user                          │  │
│  │                                                                        │  │
│  │  OTP (2FA) → 6-digit HMAC-SHA256 hashed code → 5 min TTL               │  │
│  │              Constant-time comparison, max 5 attempts                  │  │
│  │              60s resend cooldown                                       │  │
│  │                                                                        │  │
│  │  RBAC → Role → Permissions (resource:action)                           │  │
│  │         Superuser bypasses all checks                                  │  │
│  │         Checked via require_permission() / require_role() deps         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─── Data Plane (Per-API Policy) ────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  open    → No credentials needed                                       │  │
│  │  apiKey  → X-API-Key → SHA256 → constant-time DB match                 │  │
│  │            Supports: expiry, revocation, environment scoping           │  │
│  │  jwt     → Bearer → decode → verify (sig, exp, iss, aud)               │  │
│  │            Secret from: policy config | ${secret:ref} | JWT_SECRET     │  │
│  │  oauth2  → Token introspection (RFC 7662) → external IdP               │  │
│  │            client_id:client_secret via Basic Auth                      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─── Security Properties ────────────────────────────────────────────────┐  │
│  │  ✓ Constant-time comparisons (hmac.compare_digest) everywhere          │  │
│  │  ✓ Hashed storage: passwords (PBKDF2), JTI (HMAC-SHA256),              │  │
│  │    API keys (SHA256), OTP codes (HMAC-SHA256)                          │  │
│  │  ✓ Encrypted secrets: Fernet + PBKDF2 key derivation (100k iter)       │  │
│  │  ✓ HttpOnly + Secure + SameSite cookies for refresh tokens             │  │
│  │  ✓ Audit trail on every auth event                                     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 8. Control Plane (Mini-Cloud)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    MINI-CLOUD CONTROL PLANE                                  │
│                                                                              │
│  ┌─── Service Registry ───────────────────────┐                              │
│  │  In-memory dict: service → [instances]     │                              │
│  │  Each instance: url, weight, ttl, metadata │                              │
│  │  Auto-expire stale registrations           │                              │
│  │  API: register, deregister, list, discover │                              │
│  └──────────────────────┬─────────────────────┘                              │
│                         │                                                    │
│  ┌─── Routing Engine ───┴─────────────────────┐                              │
│  │  Strategies:                               │                              │
│  │    round-robin (sequential)                │                              │
│  │    weighted (proportional random)          │                              │
│  │    weighted-round-robin (interleaved)      │                              │
│  │  Policy-based rate limiting (sliding win)  │                              │
│  │  Route: POST /mini-cloud/services/{svc}/   │                              │
│  │         route { client_id, payload }       │                              │
│  └────────────────────────────────────────────┘                              │
│                                                                              │
│  ┌─── Autoscaler (HPA-like) ──────────────────┐                              │
│  │  Signals: queue_depth + latency            │                              │
│  │  Target: 10 items/replica, 500ms latency   │                              │
│  │  Cooldown: prevents thrashing              │                              │
│  │  Min/max replica constraints               │                              │
│  │  Decision: scale-up / scale-down / hold    │                              │
│  └────────────────────────────────────────────┘                              │
│                                                                              │
│  ┌─── Job Scheduler ──────────────────────────┐                              │
│  │  FIFO queue with worker lease model        │                              │
│  │  Lease timeout → auto-release              │                              │
│  │  Exponential backoff: 2^n (capped)         │                              │
│  │  Dead-letter queue for failed jobs         │                              │
│  └────────────────────────────────────────────┘                              │
│                                                                              │
│  State: Persisted to control_plane_state.json on shutdown                    │
│         Restored on startup                                                  │
│         Cleared via /mini-cloud/reset                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 9. Frontend Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React SPA)                                │
│                                                                             │
│  ┌─── Entry ──────────────────────────────────────────────────────────────┐ │
│  │  index.html → main.tsx → <App> → <BrowserRouter> → <ThemeProvider>     │ │
│  │    → <AppRoutes> (lazy-loaded pages with Suspense)                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─── Routing ─────────────────────────────────────────────────────────┐    │
│  │  Public:    /, /login, /register, /reset-password, /verify-otp      │    │
│  │  Protected: /dashboard, /apis, /apis/:id, /api-keys, /secrets,      │    │
│  │             /connectors, /environments, /audit-logs, /mini-cloud,   │    │
│  │             /users, /authorizers/*                                  │    │
│  │  Guard:     <ProtectedRoute> checks token + loads profile + roles   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─── State ───────────────────────────────────────────────────────────┐    │
│  │  Zustand Auth Store: accessToken, refreshToken, profile             │    │
│  │  Zustand Theme Store: light/dark mode (localStorage persisted)      │    │
│  │  useQueryCache: TTL-based in-memory Map (2 min)                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─── API Layer ───────────────────────────────────────────────────────┐    │
│  │  Axios with interceptors:                                           │    │
│  │    Request: inject Authorization: Bearer {token}                    │    │
│  │    Response 401: queue requests → refresh token → retry (max 3)     │    │
│  │    On refresh failure: clearAuth() → redirect /login                │    │
│  │                                                                     │    │
│  │  Services: auth, users, apis, apiKeys, secrets, connectors,         │    │
│  │            authorizers, auditLogs, miniCloud, metrics               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─── RBAC UI ─────────────────────────────────────────────────────────┐    │
│  │  usePermissions() hook: hasPermission, hasRole, isSuperuser         │    │
│  │  <PermissionGuard permission="api:create"> conditional rendering    │    │
│  │  Superuser: bypasses all frontend permission checks                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  Build: Vite → 4 manual chunks (react, mui, utils, state)                   │
│  Test:  Jest + Testing Library + MSW (API mocking)                          │
│  Serve: Nginx (static + /api/* reverse proxy to backend:8000)               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 10. Deployment Topology

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                    ┌──────────────────┐                                      │
│                    │  GitHub Actions  │                                      │
│                    │  (CI/CD)         │                                      │
│                    └────────┬─────────┘                                      │
│                             │ docker push → GHCR                             │
│                             │ SSH → deploy.sh                                │
│                             ▼                                                │
│              ┌───────────────────────────────────┐                           │
│              │    EC2 Instance (Ubuntu 22.04)    │                           │
│              │    Docker + Docker Compose        │                           │
│              │                                   │                           │
│              │  ┌───────────────────────────────┐│                           │
│              │  │  docker-compose.prod.yml      ││                           │
│              │  │                               ││                           │
│              │  │  ┌─────────┐  ┌────────────┐  ││                           │
│              │  │  │Frontend │  │  Backend   │  ││                           │
│              │  │  │(Nginx)  │──│  (Fast-    │  ││                           │
│              │  │  │ :80     │  │   API)     │  ││                           │
│              │  │  │         │  │  :8000     │  ││                           │
│              │  │  └─────────┘  └─────┬──────┘  ││                           │
│              │  │                     │         ││                           │
│              │  │        ┌────────────┼───────┐ ││                           │
│              │  │        ▼            ▼       │ ││                           │
│              │  │  ┌──────────┐ ┌──────────┐  │ ││                           │
│              │  │  │PostgreSQL│ │  Redis   │  │ ││                           │
│              │  │  │  :5432   │ │  :6379   │  │ ││                           │
│              │  │  │(internal)│ │(internal)│  │ ││                           │
│              │  │  └──────────┘ └──────────┘  │ ││                           │
│              │  │    Internal Bridge Network  │ ││                           │
│              │  │    (only :80 exposed)       │ ││                           │
│              │  └─────────────────────────────┘ ││                           │
│              └──────────────────────────────────┘│                           │
│                                                  │                           │
│ Alternate: SSH Tunnel to AWS RDS (private subnet)│                           │
│ Local Dev → EC2 Bastion → RDS (no public IP)     │                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 11. Observability Stack

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         OBSERVABILITY                                        │
│                                                                              │
│  ┌─── Metrics (Prometheus) ───────────────────────────────────────────────┐  │
│  │  Counters: gateway_requests_total{method, path, status}                │  │
│  │  Histogram: gateway_request_duration_seconds (12 buckets)              │  │
│  │  Gauge: gateway_active_connections                                     │  │
│  │  Endpoints: /metrics (raw), /metrics/summary (7-day JSON aggregate)    │  │
│  │  Percentiles: P50, P90, P95, P99 via SQL OFFSET calculation            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─── Audit Logging ─────────────────────────────────────────────────────┐   │
│  │  100+ semantic events (auth:login, api:create, gateway:proxy, etc.)   │   │
│  │  Fields: timestamp, user_id, action, resource_type, IP, user-agent,   │   │
│  │          status (success/failure), metadata JSON                      │   │
│  │  Async write via dedicated DB session (no transaction conflicts)      │   │
│  │  30-day retention (auto-cleanup script)                               │   │
│  │  Query API: /api/audit-logs with filters, stats, user activity        │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─── Structured Logging ─────────────────────────────────────────────────┐  │
│  │  structlog → JSON output with processor pipeline                       │  │
│  │  Request logging: method, path, status, duration (auth redacted)       │  │
│  │  Request ID: UUID propagated end-to-end (X-Request-ID header)          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─── Tracing Headers ───────────────────────────────────────────────────┐   │
│  │  X-Gateway-RequestId, X-Gateway-ApiId, X-Gateway-Latency-Ms           │   │
│  │  X-Gateway-Url-Source, X-Response-Time, X-RateLimit-*                 │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 12. Security Architecture

| Layer | Protection | Implementation |
|-------|-----------|----------------|
| **Transport** | HTTPS termination | Nginx / ALB (production) |
| **Input** | SQL injection, XSS, path traversal, CRLF | Validation middleware (regex pattern detection) |
| **Body** | Oversized payloads, deep nesting | 10MB limit, depth 10, keys 1000, array 10000 |
| **Auth** | Credential theft | PBKDF2 passwords, HMAC-SHA256 token/OTP hashing |
| **Timing** | Side-channel attacks | `hmac.compare_digest()` for all comparisons |
| **Tokens** | Token replay | JTI tracking, refresh rotation, max 5 sessions |
| **Secrets** | Credential exposure | Fernet encryption at rest, PBKDF2 key derivation |
| **API Keys** | Key theft | SHA256 hash storage, shown once, revocable, scoped |
| **RBAC** | Privilege escalation | Resource:action permissions, superuser bypass only |
| **Rate Limiting** | DDoS / abuse | Redis-backed distributed counters (fail-open) |
| **Network** | Internal service exposure | Docker internal bridge, only frontend port exposed |
| **Audit** | Compliance / forensics | Every mutation logged with full context |
| **Cookies** | XSS/CSRF | HttpOnly, Secure, SameSite=lax |

---

### 13. Key Architectural Patterns

| Pattern | Where | Benefit |
|---------|-------|---------|
| **3-tier DB fallback** | Database layer | Zero-downtime even if PostgreSQL unavailable |
| **Fail-open rate limiting** | Redis middleware | Availability over strictness |
| **Onion middleware** | FastAPI/Starlette | Clean separation of cross-cutting concerns |
| **Eager loading** | Gateway proxy | Single DB query loads API + policies + pools + schemas |
| **Secret references** | `${secret:name}` | Decrypt-on-use, never store plaintext in policy configs |
| **Token rotation** | Refresh flow | Old token revoked on each refresh (replay protection) |
| **Connection pooling** | asyncpg, httpx, Redis | Amortize connection cost across requests |
| **Manual chunk splitting** | Vite build | Optimal browser caching for vendor libraries |
| **Lazy loading** | React routes | Code-split every page, loaded on navigation |
| **Interceptor queue** | Axios 401 handler | Prevent thundering herd of refresh requests |
| **State persistence** | Control plane | Service registry survives process restart |
| **Audit isolation** | Dedicated DB session | Audit writes never conflict with request transactions | 

Completed: *Compile full architecture design* (5/5)

Above is the full project architecture covering the tech stack and rationale for every choice, 5-layer caching strategy, 25 database models, 8-layer middleware pipeline, 9-step gateway proxy pipeline, authentication/authorization design, mini-cloud control plane, frontend SPA architecture, deployment topology, observability stack, security posture, and key architectural patterns.



<!-- Store control plane in database
users by default have access to all environments, but we can add a new field to the user model to specify which environments they have access to. This way, we can easily manage user permissions and restrict access to certain environments if needed.
deploy to ec2 or record video of it. -->
