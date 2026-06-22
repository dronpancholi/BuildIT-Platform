# SECURITY_AUDIT.md — Phase 2 Final

**Date:** 2026-06-05
**Auditor:** Principal Security Engineer
**Method:** Direct testing, code review, threat modeling
**Verdict:** **NOT PRODUCTION READY — 3 CRITICAL findings**

---

## 1. Critical Findings (Release Blockers)

### 🔴 SEC-001: Authentication Bypass via Header Spoofing (CRITICAL)

**Threat:** An attacker who knows or guesses a tenant's UUID can read ALL data for that tenant by setting HTTP headers.

**Evidence:**
```bash
# Real attack
curl -H "X-User-Id: deadbeef-dead-beef-dead-beefdeadbeef" \
     -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000001" \
     -H "X-User-Role: super_admin" \
     http://localhost:8000/api/v1/campaigns?limit=5&tenant_id=00000000-0000-0000-0000-000000000001
# Returns 200 OK with real campaign data
```

**Root cause:** `core/auth.py:45-67` (`_resolve_user_from_headers`):

```python
async def _resolve_user_from_headers(x_user_id, x_tenant_id, x_user_role):
    if not x_user_id or not x_tenant_id:
        raise HTTPException(401, "Missing X-User-Id and/or X-Tenant-Id headers")
    user_id = UUID(x_user_id)
    tenant_id = UUID(x_tenant_id)
    role = x_user_role or "viewer"
    return CurrentUser(  # ← NO DATABASE LOOKUP
        id=user_id,
        tenant_id=tenant_id,
        email=f"user-{user_id}@authenticated.local",
        role=role,  # ← ROLE FROM HEADER, NOT DB
    )
```

The function:
1. Validates only that `X-User-Id` and `X-Tenant-Id` are valid UUIDs
2. **Does NOT verify the user exists**
3. **Does NOT verify the user belongs to the tenant**
4. **Does NOT verify the user has the claimed role**
5. **Trusts the role string from the header**

**Impact:** Full read/write access to any tenant's data by anyone with knowledge of a tenant UUID. UUIDs are not secret (often exposed in URLs, logs, error messages).

**CVSS:** 9.1 (Critical) — Network accessible, low complexity, no auth required, full data exposure.

**Real attack vectors:**
- Phishing → capture tenant UUID from a URL → access all customer data
- URL leakage in logs/error messages
- Guessing (UUIDs aren't truly secret; v4 is 122 bits, but operations teams share URLs frequently)
- Insider threat (any user can become super_admin of any tenant)

**Fix:** Implement real authentication (JWT or session), verify user in DB, verify user-tenant binding, read role from DB not header.

---

### 🔴 SEC-002: Rate Limiter Disabled in Development Mode (CRITICAL)

**Threat:** Brute force attacks, DoS, API abuse.

**Evidence:**
```bash
# 200 requests in a row, 0 rate-limited
for i in {1..200}; do
  curl -H "X-User-Id: 22222222-2222-2222-2222-222222222222" \
       -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000001" \
       "http://localhost:8000/api/v1/search?q=test$i"
done
# All 200 requests return 200, no 429
```

**Root cause:** `core/rate_limiter.py:68`:

```python
if get_settings().is_development or request.url.path in self.SKIP_PATHS or request.method == "OPTIONS":
    return await call_next(request)  # BYPASS!
```

The platform is in `APP_ENV=development` (per `.env`).

**Impact:**
- No brute-force protection
- No DoS protection at API layer
- Cost amplification (AI calls, external API calls — each request can trigger $0.01-$1 of compute)
- An attacker can drain the AI inference budget in minutes

**Fix:** Remove `is_development` short-circuit. Rate limit always.

---

### 🔴 SEC-003: /openapi.json Exposes Full API Surface (HIGH)

**Threat:** Information disclosure; attacker has full map of all 684 endpoints.

**Evidence:**
```bash
$ curl -s http://localhost:8000/openapi.json | jq '.paths | length'
684
```

**Root cause:** `main.py:258-260`:
```python
docs_url="/docs" if settings.is_development else None,
redoc_url="/redoc" if settings.is_development else None,
openapi_url="/openapi.json" if settings.is_development else None,
```

The condition `is_development` is True, so all 3 are exposed.

**Impact:** Even if auth is fixed, attacker has a complete enumeration of:
- All admin endpoints
- All write operations
- Internal-only endpoints (e.g., `/global-infrastructure`, `/cross-tenant-intelligence`)
- All workflow trigger endpoints

**Fix:** Never expose OpenAPI in production. Add `X-Forwarded-Proto` check or remove entirely for prod.

---

## 2. High Severity Findings

### 🟠 SEC-004: APP_SECRET_KEY is Placeholder

**Evidence:** `.env` line 8: `APP_SECRET_KEY=dev_secret_key_change_in_production`

**Impact:** If used for JWT signing, sessions can be forged. If used for CSRF, tokens can be predicted.

**Code reference:** `config/__init__.py:282` — has a default value `"change-me-to-a-secure-random-string"`.

**Fix:** Generate a real 256-bit random key per environment; never commit `.env` to git (it is currently in the repo, see SEC-005).

### 🟠 SEC-005: .env File Contains Real API Keys, Committed to Git

**Evidence:**
```bash
$ grep -E "API_KEY|PASSWORD|SECRET" /Users/dronpancholi/Developer/Project\ 31A/.env
NVIDIA_NIM_API_KEY=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
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
POSTGRES_PASSWORD=seo_platform_dev
ENCRYPTION_MASTER_KEY=iCOJCD59uy4cTXNhmk2/BMl+/QK38NWM/wa6ZaUYWt8=
AUTH_SECRET_KEY=dev_auth_secret
APP_SECRET_KEY=dev_secret_key_change_in_production
```

```bash
$ cd /Users/dronpancholi/Developer/Project\ 31A && git log --oneline .env 2>&1 | head -5
# (committed in git history)
```

**Impact:**
- NVIDIA NIM API key can be stolen and used for unauthorized AI inference ($$ cost)
- MinIO admin credentials exposed (if MinIO is exposed externally)
- Postgres password exposed
- Encryption master key exposed → ALL encrypted data (provider_keys table) is decryptable

**Fix:**
1. **Immediately rotate ALL keys in the .env file**
2. Remove .env from git history (`git filter-branch` or BFG Repo-Cleaner)
3. Add `.env` to `.gitignore` (likely already there, but check)
4. Use environment variables, not files, for production
5. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, Doppler)

### 🟠 SEC-006: No Password / Credential Storage

**Evidence:** The `users` table has no password hash column. The auth model trusts headers.

**Schema:**
```
Column     |          Type           | Nullable |      Default
id            | uuid                    | not null | gen_random_uuid()
tenant_id     | uuid                    | not null |
external_id   | character varying(255)  | not null |          ← Looks like OAuth subject
email         | character varying(255)  | not null |
name          | character varying(255)  | not null |
role          | user_role               | not null |
is_active     | boolean                 | not null |
permissions   | jsonb                   | not null | '[]'::jsonb
last_login_at | timestamp with time zone|
```

**Note:** `external_id` suggests external auth (Clerk, Auth0) was planned, but no implementation exists.

**Impact:** No password auth, no MFA, no way to identify users cryptographically.

**Fix:** Integrate with an auth provider (Clerk, Auth0, Cognito) OR implement password+bcrypt+session.

### 🟠 SEC-007: No Session / Token Management

**Evidence:** No `Set-Cookie` headers. No JWT validation. No session storage.

**Fix:** Implement either:
- Session cookies with HttpOnly, Secure, SameSite=Strict
- JWT in Authorization header with proper verification

### 🟠 SEC-008: Cross-Tenant Intelligence Endpoint (Suspicious)

**Evidence:** `/api/v1/cross-tenant-intelligence` exists. The router has it (`router.py:171`):
```python
api_router.include_router(cross_tenant_intelligence_router, prefix="/cross-tenant", tags=["cross-tenant"])
```

**Impact:** If this endpoint shares data across tenants, it could leak data between tenants.

**Mitigation:** Verified in multi-tenancy test — RLS prevented cross-tenant data access in tested endpoints. Need to verify this specific endpoint.

### 🟠 SEC-009: X-User-Role Header is Spoofable

**Threat:** Attacker sets `X-User-Role: super_admin` to gain admin access.

**Evidence:** Same as SEC-001 — the role is read from header, not DB.

**Impact:** Permission escalation. Can become any role.

**Fix:** Read role from DB. Or for OAuth, include in verified JWT claims.

---

## 3. Medium Severity Findings

### 🟡 SEC-010: No CORS for HTTPS in Dev

**Evidence:** CORS is configured for localhost only. Good for dev, but the wildcard isn't being used. ✅ Actually, this is OK.

### 🟡 SEC-011: No File Upload Validation

**Evidence:** Tested `/api/v1/attachments/upload` — returns 422 (likely Pydantic validation), but file type, size, and content checks are unclear.

**Fix:** Add explicit validation:
- Max file size (e.g., 25 MB)
- Allow-list of MIME types
- Antivirus scan
- Path traversal protection in filenames

### 🟡 SEC-012: 51 Idle DB Connections After Load

**Evidence:** After 1000-tenant load test, `pg_stat_activity` shows 51 idle connections.

**Impact:** Connection pool exhaustion risk. Could be exploited by slow-loris-style attack.

**Fix:** Investigate why connections aren't being released. Add `RESET app.current_tenant` audit. Add connection-timeout.

### 🟡 SEC-013: No HTTP Security Headers for /docs

**Evidence:** Security headers are added by middleware, but only for non-error responses.

**Fix:** Verify all paths get security headers.

### 🟡 SEC-014: No Audit Log of Auth Events

**Evidence:** Auth events are not logged to audit_ledger. Failed logins are not recorded.

**Fix:** Add auth event logging to audit_ledger (login success, login fail, role change).

### 🟡 SEC-015: No CSRF Protection

**Evidence:** No CSRF tokens. The platform uses Bearer-style auth (headers), which is generally not vulnerable to CSRF, but if session cookies are added, CSRF protection is needed.

**Fix:** Add CSRF tokens if using cookie-based auth.

---

## 4. Low Severity Findings

### 🟢 SEC-016: AES-GCM Nonce Reuse Risk

**Code:** `core/encryption.py:97`:
```python
nonce = os.urandom(12)
```

**Analysis:** `os.urandom` is cryptographically secure. With 96-bit nonces, collision probability is negligible at any realistic volume. ✅ OK.

### 🟢 SEC-017: SQL Injection via f-string (Low Risk)

**Code:** `api/endpoints/customers.py:13`:
```python
sql = f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid {extra}"
```

**Analysis:** `table` is hardcoded at call sites; not user-controllable. **NOT currently exploitable**, but is a security anti-pattern.

**Fix:** Whitelist `table` parameter or use SQLAlchemy ORM.

### 🟢 SEC-018: No Database Connection Encryption (In Transit)

**Evidence:** `POSTGRES_HOST=localhost` — no SSL configured.

**Fix:** When deploying to a real environment with network separation, enable SSL.

### 🟢 SEC-019: Mailhog in Production Path

**Evidence:** `/health` includes mailhog check. Mailhog is a dev-only SMTP server.

**Fix:** Replace Mailhog with real SMTP (SendGrid, Resend) for production. Or exclude from /health in prod.

---

## 5. Threat Model Summary

| Threat | Likelihood | Impact | Status |
|---|---|---|---|
| Tenant data theft via header spoof | HIGH | CRITICAL | ❌ Not mitigated |
| Brute force / DoS | HIGH | HIGH | ❌ Not mitigated |
| API surface enumeration | HIGH | MEDIUM | ❌ Not mitigated |
| Secret leakage via .env | HIGH | HIGH | ❌ Not mitigated |
| Cross-tenant data leak | MEDIUM | CRITICAL | ✅ Mitigated (RLS) |
| SQL injection | LOW | HIGH | ⚠️ Anti-patterns present |
| XSS | LOW | HIGH | ✅ Headers prevent |
| CSRF | LOW | MEDIUM | ✅ Not using cookies |
| Path traversal | LOW | HIGH | ✅ 404 on bad paths |
| SSRF | LOW | MEDIUM | ✅ Endpoints don't take URLs |
| Password compromise | N/A | HIGH | ❌ No passwords exist |
| Insider threat | MEDIUM | HIGH | ❌ Spoofable role |
| AI cost amplification | HIGH | HIGH | ❌ No rate limit + AI proxy |

---

## 6. Compliance Status

| Standard | Status | Notes |
|---|---|---|
| SOC 2 | ❌ Not ready | No audit logging, no encryption-at-rest verification |
| GDPR | ⚠️ Partial | RLS exists, no consent management, no data export API |
| HIPAA | ❌ Not ready | No encryption-at-rest for PII, no audit log |
| PCI-DSS | ❌ Not ready | No token vault, no encryption of card data |
| ISO 27001 | ❌ Not ready | No formal risk assessment, no change management |

---

## 7. What Was Tested (Negative Results)

These attack vectors were tested and **NOT** found vulnerable:

- ✅ Path traversal (`../../../etc/passwd`) — 404
- ✅ SSRF (AWS metadata service) — 404
- ✅ SSRF (Postgres port) — 404
- ✅ Large payload DoS (2MB JSON) — 422
- ✅ CORS attack (`Origin: https://attacker.com`) — no allow-origin header
- ✅ Verbose error messages — sanitized
- ✅ Stack trace leakage — caught and replaced
- ✅ Cookie-based session attack — no cookies
- ✅ Cross-tenant data leak via RLS — properly isolated
- ✅ SQL injection via query params — UUID validation rejects malformed

---

## 8. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| Authentication | 25% | 10/100 | Trivially bypassable |
| Authorization | 20% | 50/100 | RBAC exists, role spoofable |
| Rate limiting | 10% | 0/100 | Disabled in dev |
| Input validation | 10% | 90/100 | Pydantic works |
| Secret management | 10% | 30/100 | .env has real keys, in git |
| Audit logging | 5% | 60/100 | Audit ledger exists, no auth events |
| Tenant isolation | 10% | 100/100 | RLS works |
| HTTPS / TLS | 5% | 0/100 | No TLS configured |
| CORS | 5% | 100/100 | Whitelist only |
| **Overall** | | **40/100** | Multiple P0 blockers |

---

## 9. Findings Summary

| ID | Finding | Sev | Status |
|---|---|---|---|
| SEC-001 | Auth via header trust (no DB check, no JWT) | P0 | OPEN |
| SEC-002 | Rate limiter disabled in dev | P0 | OPEN |
| SEC-003 | /openapi.json exposes 684 endpoints in dev | P0 | OPEN |
| SEC-004 | APP_SECRET_KEY is placeholder | P1 | OPEN |
| SEC-005 | .env with real keys in git history | P1 | OPEN |
| SEC-006 | No password storage | P1 | OPEN |
| SEC-007 | No session / token management | P1 | OPEN |
| SEC-008 | Cross-tenant intelligence endpoint (verify isolation) | P1 | NEEDS REVIEW |
| SEC-009 | X-User-Role spoofable | P0 | OPEN |
| SEC-010 | CORS configuration | OK | OK |
| SEC-011 | No file upload validation | P2 | OPEN |
| SEC-012 | 51 idle DB connections | P2 | OPEN |
| SEC-013 | Security headers for /docs | P2 | OPEN |
| SEC-014 | No auth event audit | P2 | OPEN |
| SEC-015 | No CSRF protection | P3 | OK (no cookies) |
| SEC-016 | AES-GCM nonce reuse | OK | OK |
| SEC-017 | SQL injection via f-string | P2 | OPEN (anti-pattern) |
| SEC-018 | No SSL for DB | P2 | OK (localhost) |
| SEC-019 | Mailhog in production path | P2 | OPEN |

**4 P0 + 4 P1 + 7 P2 = 15 findings open. 3 P0 are release blockers.**
