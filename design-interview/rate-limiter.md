Let me explore the rate limiting code in the project first. 

Explore rate limiting codebase

Here's the full system design of the rate limiting feature in this gateway management project:

---

## System Design: Rate Limiting

### High-Level Architecture

The project implements a **multi-layered rate limiting system** with three tiers:

```
┌──────────────────────────────────────────────────────────────────────┐
│                         HTTP Request                                 │
└──────────────────────────┬───────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Layer 1: Global Middleware Rate Limiting                │
│              (Redis-backed, per-user/key/IP)                         │
│              1000 req / 60s default                                  │
│                                                                      │
│   Key resolution priority:                                           │
│     1. user:{user_id}       (authenticated user)                     │
│     2. apikey:{prefix}      (X-API-Key header)                       │
│     3. ip:{client_ip}       (fallback)                               │
│                                                                      │
│   Skips: /health, /metrics, /docs, /openapi.json                     │
└──────────────────────────┬───────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Layer 2: Per-API Rate Limits (DB-configured)            │
│              CRUD via /apis/{api_id}/rate-limits                     │
│              key_type: global | per-ip | per-key                     │
└──────────────────────────┬───────────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Layer 3: Policy-Based Rate Limiting (Mini-Cloud)        │
│              In-memory sliding window per client_id                  │
│              JSON policy files (hot-reloadable)                      │
└──────────────────────────┬───────────────────────────────────────────┘
                           ▼
                 Response + Headers
          X-RateLimit-Limit / Remaining / Reset
```

---

### Components

#### 1. Rate Limiting Algorithms (algorithms.py)

Three pluggable algorithms, all Redis-backed:

| Algorithm | Storage | Key Pattern | Behavior |
|-----------|---------|-------------|----------|
| **Fixed Window** | Redis counter | `rate_limit:fixed:{key}:{window}` | Counter resets at fixed intervals |
| **Sliding Window** | Redis sorted set | `rate_limit:sliding:{key}` | Timestamp log, removes expired entries |
| **Token Bucket** | Redis hash | `rate_limit:token:{key}` | Tokens refill at `limit / window_seconds` per second |

All algorithms return `(allowed: bool, info: dict)` with `limit`, `remaining`, `reset` (unix timestamp), and optional `error`.

**Fail-open design**: If Redis is unavailable, requests are allowed (with an error field logged).

#### 2. Middleware (middleware.py)

Registered in the middleware chain in main.py:

```
CORS → Audit Logging → Rate Limiting → Metrics → Input Validation → Request ID → Request Logging
                        ▲
                   enforced here
```

- Resolves the rate limit key by identity priority (user > API key > IP)
- Injects `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers
- Returns **HTTP 429** with `Retry-After` header when exceeded

#### 3. Manager (manager.py)

`RateLimitManager` provides CRUD operations for persisted rate limit configurations:

```
create_rate_limit()  →  INSERT rate_limits
get_rate_limits_for_api()  →  SELECT WHERE api_id = ?
get_rate_limit()  →  SELECT by id
update_rate_limit()  →  UPDATE
delete_rate_limit()  →  DELETE
```

#### 4. Database Model

```
┌──────────────────────────────┐       ┌──────────────────────────┐
│          APIs                │       │       RateLimit          │
├──────────────────────────────┤       ├──────────────────────────┤
│ id (PK)                      │◄──────│ api_id (FK, CASCADE)     │
│ name                         │  1:N  │ id (PK)                  │
│ ...                          │       │ name (indexed)           │
│ rate_limits ──────────────── │       │ key_type                 │
└──────────────────────────────┘       │   global|per-ip|per-key  │
                                       │ algorithm                │
                                       │   fixed_window|          │
                                       │   sliding_window|        │
                                       │   token_bucket           │
                                       │ limit (1–1,000,000)      │
                                       │ window_seconds (1–86400) │
                                       │ created_at               │
                                       │ updated_at               │
                                       └──────────────────────────┘
```

#### 5. REST API (rate_limit_router.py)

Mounted at `/apis/{api_id}/rate-limits`, RBAC-protected:

| Method | Endpoint | Permission | Status |
|--------|----------|------------|--------|
| `POST` | `/apis/{api_id}/rate-limits` | `api:update` | 201 |
| `GET` | `/apis/{api_id}/rate-limits` | `api:read` | 200 |
| `GET` | `/apis/{api_id}/rate-limits/{rl_id}` | `api:read` | 200 |
| `PUT` | `/apis/{api_id}/rate-limits/{rl_id}` | `api:update` | 200 |
| `DELETE` | `/apis/{api_id}/rate-limits/{rl_id}` | `api:update` | 204 |

Request schema: `name` (1-100 chars), `key_type`, `algorithm`, `limit` (1–1M), `window_seconds` (1–86400)

#### 6. Mini-Cloud Policy Rate Limiting (mini_cloud.py)

In-memory sliding window for service routing policies:

```
Policy JSON → rate_limit_policy: "my_policy"
                    ↓
PolicyConfig.rate_limits["my_policy"] → {limit: N, window_seconds: W}
                    ↓
_rate_window_cache["{policy}:{client_id}"] → [timestamps...]
                    ↓
len(events) >= limit ? → 429 "policy rate limit exceeded"
```

Enforced at `/mini-cloud/services/{service}/route`, per `client_id`. Cache cleared on `/mini-cloud/reset`.

---

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Redis-backed counters** | Distributed, atomic operations, TTL support for auto-expiry |
| **Fail-open** | Availability over strictness — if Redis is down, don't block traffic |
| **Multi-key resolution** (user > apikey > IP) | Accurate attribution; IP-based is least precise fallback |
| **Algorithm as DB column** | Admins can switch strategies per-API without code changes |
| **Compatibility shim** (rate_limiting) | Backward-compatible re-exports for older tests and legacy code |
| **In-memory policy limiter** | Mini-cloud policies need lightweight, per-process enforcement without Redis dependency |

### Data Flow Summary

```
Request → Middleware extracts key → Redis check (algorithm-specific)
  ├── Allowed → add X-RateLimit-* headers → continue to handler
  └── Denied  → 429 + Retry-After header → response returned

Admin → POST /apis/{id}/rate-limits → DB insert → affects per-API enforcement
Policy → JSON config reload → in-memory cache update → Mini-Cloud enforcement
```