Explore full request pipeline

Here's the complete request pipeline design for the gateway:

---

## Request Pipeline

### Middleware Chain (outermost → innermost)

Due to Starlette's LIFO registration model, the **last registered middleware executes first**. The pipeline a request traverses:

```
                            ┌─────────────┐
                            │   Client    │
                            └──────┬──────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  1. CORS Middleware                                                  │
│     • Handles preflight OPTIONS                                      │
│     • Injects Access-Control-Allow-* headers                         │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  2. Authorization Middleware                                         │
│     • Extracts JWT from Authorization header or access_token cookie  │
│     • Validates token signature + expiry                             │
│     • Attaches user context (user_id, roles) to request.state        │
│     • API Key path: validates X-API-Key (SHA256 lookup + expiry)     │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  3. Audit Middleware                                                 │
│     • Maps endpoint → semantic event (e.g. POST /apis → api:create)  │
│     • Captures: user_id, IP, user-agent, duration, status            │
│     • Async DB write (separate session, non-blocking)                │
│     • ~100+ mapped event types across all resources                  │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  4. Rate Limiter Middleware                                          │
│     • Skips: /health, /metrics, /docs, /openapi.json                 │
│     • Key resolution: user:{id} > apikey:{prefix} > ip:{addr}        │
│     • Redis check (Fixed Window / Sliding Window / Token Bucket)     │
│     • 429 + Retry-After on exceed                                    │
│     • Fail-open if Redis unavailable                                 │
│     • Adds X-RateLimit-Limit / Remaining / Reset headers             │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  5. Metrics Middleware                                               │
│     • Increments request counter (method, path, status)              │
│     • Records latency histogram                                      │
│     • Tracks active connections gauge                                │
│     • Feeds /metrics (Prometheus) and /metrics/summary (JSON)        │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  6. Input Validation Middleware                                      │
│     • Body size limit (10 MB via Content-Length)                     │
│     • JSON depth limit (max 10 levels)                               │
│     • Object keys limit (max 1,000) / Array elements (max 10,000)    │
│     • Threat detection: SQL injection, XSS, path traversal, CRLF     │
│     • 400 on violation                                               │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  7. Request ID Middleware                                            │
│     • Generates UUID if no X-Request-ID header present               │
│     • Propagates through to upstream + response headers              │
│     • Enables distributed tracing                                    │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  8. Request Logging Middleware                                       │
│     • Logs method, path, status, duration                            │
│     • Redacts Authorization header values                            │
│     • Captures request/response metadata                             │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
                        ┌──────────────┐
                        │  Router      │
                        └──────┬───────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                     ▼
   Management APIs       Data Plane           Infrastructure
   /auth/*               /gw/{api_id}/*       /health
   /apis/*                                    /metrics
   /api/keys/*                                /metrics/summary
   /api/secrets/*
   /api/connectors/*
   /api/authorizers/*
   /api/admin/*
   /api/audit-logs/*
```

---

### Gateway Proxy Pipeline (`/gw/{api_id}/{path}`)

When a request hits the data plane, it passes through an **additional per-request pipeline** inside the gateway handler:

```
GET /gw/abc123/users/42
         │
         ▼
┌─────────────────────────────┐
│ 1. Resolve API              │  Lookup API by id → 404 if not found
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ 2. Lifecycle Check          │  draft → 503 "API not published"
│                             │  deprecated → 410 "API deprecated"
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ 3. Resolve Target URL       │  Priority:
│                             │    mini-cloud service instance
│                             │    > load-balanced pool
│                             │    > env override
│                             │    > static base_url
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ 4. Enforce Auth Policy      │  Policy type per API:
│                             │    apiKey → validate X-API-Key
│                             │    jwt → validate Bearer token
│                             │    oauth2 → RFC 7662 introspection
│                             │    open → no auth required
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ 5. Per-API Rate Limit       │  Key: gw:api:{id}:{key_type}
│                             │  Checks DB-configured limits
│                             │  429 + Retry-After on exceed
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ 6. Inject Connector Secrets │  Replaces ${secret:name} placeholders
│                             │  in headers/query params with
│                             │  Fernet-decrypted values
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ 7. Schema Validation        │  POST/PUT/PATCH only
│                             │  JSON Schema Draft 7
│                             │  422 on validation failure
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ 8. Proxy to Upstream        │  Shared httpx.AsyncClient
│                             │  Strip hop-by-hop headers
│                             │  Forward method, path, query,
│                             │  headers, body
│                             │  502 on connection error
│                             │  504 on timeout
└────────────┬────────────────┘
             ▼
┌─────────────────────────────┐
│ 9. Response                 │  Upstream status + body
│                             │  + X-Gateway-RequestId
│                             │  + X-Gateway-ApiId
│                             │  + X-RateLimit-* headers
└─────────────────────────────┘
```

---

### Load Balancing (within step 3)

```
┌──────────────────────────────────────────┐
│         Load Balancer Selection          │
│                                          │
│  Algorithm (configurable per pool):      │
│    • round-robin   → sequential cycling  │
│    • least-conn    → fewest active reqs  │
│    • weighted      → proportional dist   │
│                                          │
│  Health Checks:                          │
│    • Periodic async GET /health          │
│    • Default: every 30 seconds           │
│    • Auto-marks unhealthy backends       │
│    • Only healthy backends considered    │
└──────────────────────────────────────────┘
```

---

### Error Response Map

| Code | Condition | Source |
|------|-----------|--------|
| **400** | Malicious input / validation failure | Validation Middleware |
| **401** | Missing or invalid credentials | Auth Middleware / Gateway Auth |
| **403** | Insufficient RBAC permissions | Authorization |
| **404** | API not found | Gateway Resolver |
| **410** | API deprecated | Lifecycle Check |
| **422** | JSON Schema violation | Schema Validation |
| **429** | Rate limit exceeded | Rate Limiter (global or per-API) |
| **502** | Upstream connection error | Proxy |
| **503** | API in draft state | Lifecycle Check |
| **504** | Upstream timeout | Proxy |

---

### Key Architectural Patterns

- **Async-first**: All I/O (database, HTTP proxy, logging) is async
- **Fail-open rate limiting**: Redis errors don't block requests — availability over strictness
- **Connection pooling**: Shared `httpx.AsyncClient` reused across proxy requests
- **Audit isolation**: Dedicated DB session prevents transaction conflicts with request handling
- **Secret injection**: `${secret:name}` placeholders decrypted at proxy time (Fernet symmetric encryption)
- **Three-tier URL resolution**: Mini-cloud > Load-balanced pool > Env override > Static config