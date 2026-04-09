Explore authentication flow design

Here's the complete authentication flow design for the gateway:

---

## Authentication Flow Design

### Identity Resolution (Middleware Layer)

```
                         Incoming Request
                               │
                               ▼
              ┌────────────────────────────────┐
              │   Auth Enrichment Middleware   │
              │   (best-effort, silent fail)   │
              ├────────────────────────────────┤
              │                                │
              │  Check Authorization header?   │
              │    ├─ YES → decode JWT payload │
              │    └─ NO  → check cookie?      │
              │              ├─ YES → decode   │
              │              └─ NO  → anonymous│
              │                                │
              │  Store in request.state.user   │
              │  (user_id, roles, is_superuser)│
              └────────────────┬───────────────┘
                               ▼
                     Route-level enforcement
                   (deps raise 401/403 if needed)
```

---

### 1. Registration Flow

```
POST /auth/register
    { email, password }
         │
         ▼
┌──────────────────────────────────┐
│  Validate email uniqueness       │
│  Hash password (PBKDF2-SHA256)   │
└────────────────┬─────────────────┘
                 ▼
         ┌───────────────┐
         │ First user?   │
         ├───── YES ─────┤
         │  role = admin │
         │  is_superuser │
         │  = True       │
         ├───── NO ──────┤
         │  role = viewer│
         │  is_superuser │
         │  = False      │
         └───────┬───────┘
                 ▼
┌──────────────────────────────────┐
│  INSERT User                     │
│  INSERT UserRole (admin/viewer)  │
│  Sync User.roles string field    │
└────────────────┬─────────────────┘
                 ▼
           201 Created
```

---

### 2. Login Flow (JWT + Refresh Token)

```
POST /auth/login
    { email, password }
         │
         ▼
┌──────────────────────────────────────┐
│  Lookup user by email                │
│  Verify password (PBKDF2-SHA256)     │
│  Check is_active                     │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│        Generate Access Token         │
│  ┌─────────────────────────────┐     │
│  │ Header: { alg: HS256 }      │     │
│  │ Payload:                    │     │
│  │   sub: email                │     │
│  │   user_id: uuid             │     │
│  │   roles: [admin, editor]    │     │
│  │   is_superuser: true/false  │     │
│  │   jti: unique_id            │     │
│  │   iat: now                  │     │
│  │   exp: now + 24h            │     │
│  │ Sign with JWT_SECRET        │     │
│  └─────────────────────────────┘     │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│        Generate Refresh Token        │
│  ┌─────────────────────────────┐     │
│  │ Same claims as access token │     │
│  │ exp: now + 7 days           │     │
│  │ jti: new unique_id          │     │
│  └─────────────────────────────┘     │
│                                      │
│  Hash JTI:                           │
│    HMAC-SHA256(jti, REFRESH_SALT)    │
│                                      │
│  Store in refresh_tokens table:      │
│    { token_hash, user_id,            │
│      expires_at, revoked=false }     │
│                                      │
│  Enforce max 5 active tokens/user    │
│    → revoke oldest if exceeded       │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│           Response                   │
│  Body: { access_token, token_type }  │
│  Cookie: refresh_token               │
│    HttpOnly, Secure*, SameSite=lax   │
└──────────────────────────────────────┘
```

---

### 3. Token Refresh Flow

```
POST /auth/refresh
    Cookie: refresh_token=<jwt>
    (or body: { refresh_token })
         │
         ▼
┌──────────────────────────────────────┐
│  Decode refresh JWT                  │
│  Extract JTI                         │
│  Hash: HMAC-SHA256(jti, SALT)        │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│  Query refresh_tokens table          │
│  WHERE token_hash = hashed_jti       │
│                                      │
│  Check:                              │
│    ✓ exists in DB                    │
│    ✓ revoked = false                 │
│    ✓ expires_at > now                │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│  Revoke old refresh token            │
│    SET revoked = true                │
│                                      │
│  Issue new access + refresh pair     │
│  Store new refresh JTI hash in DB    │
│  Set new refresh_token cookie        │
└────────────────┬─────────────────────┘
                 ▼
        { access_token, token_type }
```

---

### 4. Logout Flow

```
POST /auth/logout
    Cookie: refresh_token=<jwt>
         │
         ▼
┌──────────────────────────────────────┐
│  Decode refresh JWT                  │
│  Hash JTI → lookup in DB             │
│  SET revoked = true                  │
│  Clear refresh_token cookie          │
└──────────────────────────────────────┘
         │
         ▼
    200 OK (access token expires naturally)
```

---

### 5. OTP / Email Verification Flow

```
POST /auth/send-otp                POST /auth/verify-otp
    { email, transport }               { email, code }
         │                                  │
         ▼                                  ▼
┌────────────────────┐       ┌──────────────────────────────┐
│ Check resend       │       │ Hash code:                   │
│ cooldown (60s)     │       │   HMAC-SHA256(code, OTP_SALT)│
│                    │       │                              │
│ Generate 6-digit   │       │ Query OTP table:             │
│ code (secrets.     │       │   WHERE email & otp_hash     │
│ randbelow)         │       │                              │
│                    │       │ Check:                       │
│ Hash: HMAC-SHA256  │       │   ✓ not expired (5 min)      │
│ (code, OTP_SALT)   │       │   ✓ not consumed             │
│                    │       │   ✓ attempts < 5             │
│ Store in OTP table:│       │                              │
│   email, otp_hash, │       │ Constant-time compare        │
│   expires_at,      │       │ (hmac.compare_digest)        │
│   attempts=0,      │       │                              │
│   consumed=false   │       │ Success → consumed=true      │
└────────────────────┘       │ Failure → attempts++         │
                             │ Max attempts → auto-consume  │
                             └──────────────────────────────┘
```

---

### 6. API Key Authentication

```
┌──────────────────────────────────────────────────────────┐
│                    API Key Lifecycle                     │
│                                                          │
│  Creation:                                               │
│    gw_<29 hex chars> ← secrets.token_bytes()             │
│    Store: SHA256(key) or salt:SHA256(salt+key)           │
│    Return plain key to user ONCE                         │
│                                                          │
│  Validation (at gateway proxy time):                     │
│    Extract from X-API-Key header                         │
│    Hash incoming key → compare with DB (constant-time)   │
│    Check: not revoked, not expired                       │
│    Optional: environment scope enforcement               │
│                                                          │
│  Revocation:                                             │
│    SET revoked = true (soft delete)                      │
└──────────────────────────────────────────────────────────┘
```

---

### 7. Per-API Auth Policy (Gateway Proxy)

When a request hits `/gw/{api_id}/{path}`, the gateway enforces the API's configured auth policy:

```
              Request → /gw/{api_id}/...
                        │
                        ▼
               ┌─────────────────┐
               │ Load AuthPolicy │
               │ for this API    │
               └────────┬────────┘
                        │
        ┌───────────────┼───────────────┬──────────────────┐
        ▼               ▼               ▼                  ▼
   ┌─────────┐   ┌───────────┐   ┌──────────┐      ┌──────────┐
   │  open   │   │  apiKey   │   │   jwt    │      │  oauth2  │
   │         │   │           │   │          │      │          │
   │ Pass-   │   │ X-API-Key │   │ Bearer   │      │ Token    │
   │ through │   │ header    │   │ header   │      │ intro-   │
   │         │   │           │   │          │      │ spection │
   │         │   │ SHA256    │   │ Decode + │      │          │
   │         │   │ hash +    │   │ verify   │      │ POST to  │
   │         │   │ constant- │   │ signature│      │ external │
   │         │   │ time      │   │          │      │ endpoint │
   │         │   │ compare   │   │ Check    │      │          │
   │         │   │           │   │ exp,     │      │ client_id│
   │         │   │ Check:    │   │ issuer,  │      │ + secret │
   │         │   │ revoked,  │   │ audience │      │ via Basic│
   │         │   │ expired,  │   │          │      │ Auth     │
   │         │   │ env scope │   │ Secret   │      │          │
   │         │   │           │   │ from:    │      │ Expects: │
   │         │   │           │   │ policy   │      │ {active: │
   │         │   │           │   │ config   │      │  true}   │
   │         │   │           │   │ or env   │      │          │
   └────┬────┘   └─────┬─────┘   └────┬─────┘      └────┬─────┘
        │              │              │                   │
        └──────────────┴──────┬───────┴───────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  401 Unauthorized  │  ← on failure
                    │  or CONTINUE       │  ← on success
                    └───────────────────┘

  Secret references (${secret:name}) resolved at runtime
  via Fernet-decrypted secrets table
```

---

### 8. RBAC Model

```
┌────────┐       ┌───────────┐       ┌────────────┐
│  User  │──1:N──│ UserRole  │──N:1──│   Role     │
│        │       │           │       │            │
│ id     │       │ user_id   │       │ id         │
│ email  │       │ role_id   │       │ name       │
│ is_    │       │ assigned_ │       │ description│
│ super- │       │ at        │       │ permissions│
│ user   │       └───────────┘       │ (JSON list)│
└────────┘                           └─────┬──────┘
                                           │
                                    ┌──────┴──────┐
                                    │ Permission  │
                                    │             │
                                    │ name        │
                                    │ resource    │  e.g. "api"
                                    │ action      │  e.g. "create"
                                    └─────────────┘

  Permission format: resource:action
  Examples: api:create, api:read, key:update, secret:delete

  Default roles:
    admin  → all permissions
    editor → create, read, update
    viewer → read only

  Superuser (is_superuser=true) → bypasses ALL RBAC checks
```

**Endpoint protection via FastAPI dependencies:**

```python
@router.post("/apis", dependencies=[Depends(require_permission("api:create"))])
async def create_api(...): ...
```

---

### Security Summary

| Aspect | Implementation |
|--------|---------------|
| **Password storage** | PBKDF2-SHA256 (passlib) |
| **JWT signing** | HS256 with env secret |
| **Refresh token storage** | HMAC-SHA256 hashed JTI in DB |
| **API key storage** | SHA256 hash (with optional salt) |
| **OTP storage** | HMAC-SHA256 hashed codes |
| **Secret storage** | Fernet symmetric encryption |
| **Timing attacks** | `hmac.compare_digest()` throughout |
| **Token rotation** | Old refresh token revoked on each refresh |
| **Max active sessions** | 5 refresh tokens per user (oldest revoked) |
| **Cookie security** | HttpOnly, Secure (configurable), SameSite=lax |
| **Audit trail** | Every auth action logged with IP, user-agent, status |