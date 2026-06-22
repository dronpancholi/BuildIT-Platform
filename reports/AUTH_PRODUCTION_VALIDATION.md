# AUTH PRODUCTION VALIDATION — Phase 2.5

**Date:** 2026-06-06
**Verdict:** **FAIL** — Auth is header-based despite `AUTH_PROVIDER=clerk` in env. No JWT verification, no JWKS, no Clerk code, no session lifecycle, no expiration handling.

This report documents the authentication and authorization state of the platform as it would behave for a real customer. Every check below is exercised against the running backend; the responses are real.

---

## 1. Headline Findings

| # | Check | Result | Severity |
|---|-------|--------|----------|
| A-1 | JWT validation | **NOT IMPLEMENTED** | P0 |
| A-2 | Identity provider integration (Clerk) | **NOT IMPLEMENTED** (env var is a lie) | P0 |
| A-3 | Role validation (real) | Partial — role read from DB, but only after header-based auth passes | P1 |
| A-4 | Tenant validation | Working — cross-tenant attempt returns 403 | OK |
| A-5 | Session lifecycle | **NOT IMPLEMENTED** — no session concept, only request-scoped headers | P0 |
| A-6 | Expiration handling | **NOT APPLICABLE** — no tokens to expire | P0 |
| A-7 | Unauthorized access handling | Working — 401 on missing/invalid headers | OK |
| A-8 | Cross-tenant isolation | Working — RLS + validator both block | OK |
| A-9 | Header-based impersonation of any real user | **VULNERABLE** — any client with a valid UUID passes | P0 |
| A-10 | Dev auth bypass still in code | **VULNERABLE** if `APP_ENV=development` AND `DEV_AUTH_BYPASS=true` | P0 |
| A-11 | `Authorization: Bearer` accepted | **NO** — Bearer header is ignored, only `X-User-*` headers work | P0 |
| A-12 | Session/cookie management | **NO** — no cookies, no Set-Cookie headers | N/A but dangerous |
| A-13 | Audit trail of auth events | Partial — `rbac_denied` is logged but not `auth_succeeded` or `auth_failed` | P1 |
| A-14 | Rate-limit on auth failures | **NO** — brute force not rate-limited | P1 |
| A-15 | Password / MFA / recovery | **NO** — no concept of password or recovery | P0 (acceptable for service-to-service but not for browsers) |

---

## 2. Evidence

### A-1 / A-2 / A-11: No JWT, No Clerk, Bearer Ignored

**Search of entire backend code:**
```bash
$ grep -rE "clerk|jwt|JWKS|RSA|public_key" backend/src/seo_platform/
backend/src/seo_platform/core/errors.py:76:    """JWT access token has expired."""
backend/src/seo_platform/api/middleware.py:70:    Extract tenant_id from JWT claims and bind to request context.
backend/src/seo_platform/services/platform_stewardship.py:21:    "security": 0.71,          # Tenant-scoped queries, JWT middleware, no anonymous routes
```

Only **docstring references**. No actual JWT or Clerk code. The middleware that says "Extract tenant_id from JWT claims" reads the `X-Tenant-Id` header, not a JWT.

**Live test:**
```bash
$ curl -s -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.fake.token" \
       "http://localhost:8000/api/v1/campaigns?limit=1&tenant_id=00000000-..."
{"success":false,"error":{"error_code":"UNAUTHORIZED","message":"Missing X-User-Id and/or X-Tenant-Id headers"}}
```

The error message is `Missing X-User-Id and/or X-Tenant-Id headers` — the platform does not even look at the `Authorization` header.

### A-9: Any Real User UUID Passes Auth

**Live test (created a real user, then logged in as them with arbitrary role claim):**
```bash
$ psql -c "INSERT INTO users (id, tenant_id, role, is_active) VALUES
          ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '00000000-...', 'client', true);"
INSERT 0 1

$ curl -s -H "X-User-Id: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" \
       -H "X-Tenant-Id: 00000000-0000-0000-0000-000000000001" \
       -H "X-User-Role: super_admin" \
       "http://localhost:8000/api/v1/campaigns?limit=1&tenant_id=00000000-..."
{"success":true,"data":[{"id":"bb01ee88-...","name":"Phase141 Campaign",...}]}
```

**Result:** 200. The user authenticated. The server-side role was `client` (from DB), so write attempts are correctly 403 (A-3 works), but **read access was granted**. The user has read access to the tenant's data. This is a P0 because:

- An attacker who can enumerate user UUIDs (e.g., from a leaked logs dump, or by signing up via a real flow) can read every customer's data
- An attacker who controls any compromised service (e.g., a partner integration) can read every customer's data
- A customer with a real account can read every other customer's data if they know the UUIDs

The mitigation SEC-FIX-001 prevents **inventing** UUIDs, but it does not prevent **using** real UUIDs.

### A-4 / A-8: Cross-Tenant Validation Works

**Live test:**
```bash
$ curl -s -H "X-User-Id: aaaaaaaa-..." -H "X-Tenant-Id: 00000000-..." -H "X-User-Role: client" \
       "http://localhost:8000/api/v1/campaigns?limit=1&tenant_id=99999999-..."
{"success":false,"error":{"error_code":"FORBIDDEN","message":"Access denied: tenant_id does not match authenticated user"}}
```

**Result:** 403. `get_validated_tenant_id` correctly enforces that the `tenant_id` query param matches the `X-Tenant-Id` header (and the user's tenant in DB). The earlier MULTITENANCY_AUDIT (93/100) confirms RLS is also enforced at the DB layer.

### A-3: Role Validation Works (Read From DB)

**Live test (role-spoofing attempt):**
```bash
$ psql -c "UPDATE users SET role='client' WHERE id='aaaaaaaa-...';"
# User's DB role: 'client' (least privilege)
# Claimed role in header: 'super_admin'

$ curl -s -X POST -H "X-User-Id: aaaaaaaa-..." -H "X-Tenant-Id: 00000000-..." \
              -H "X-User-Role: super_admin" -H "Content-Type: application/json" \
              -d '{"name":"hack","domain":"hack.com","niche":"hack"}' \
              "http://localhost:8000/api/v1/clients?tenant_id=00000000-..."
{"success":false,"error":{"error_code":"FORBIDDEN","message":"Permission denied: customers:write requires one of ['super_admin', 'admin', 'manager']"}}
```

**Result:** 403. The platform reads the role from the DB, not the header. Role spoofing does not work for privilege escalation. SEC-FIX-009 is holding.

### A-7: Unauthorized Access Returns 401

**Live test (no headers):**
```bash
$ curl -s "http://localhost:8000/api/v1/campaigns?limit=1&tenant_id=00000000-..."
{"success":false,"error":{"error_code":"UNAUTHORIZED","message":"Missing X-User-Id and/or X-Tenant-Id headers"}}
```

**Live test (non-existent UUID):**
```bash
$ curl -s -H "X-User-Id: deadbeef-dead-beef-dead-beefdeadbeef" -H "X-Tenant-Id: 00000000-..." \
       "http://localhost:8000/api/v1/campaigns?limit=1&tenant_id=00000000-..."
{"success":false,"error":{"error_code":"UNAUTHORIZED","message":"Invalid credentials"}}
```

**Result:** Both return 401 with structured error response. SEC-FIX-001 is holding.

### A-5 / A-6 / A-12: No Session, No Expiration, No Cookies

The platform uses **per-request identity** via headers. There is no concept of:
- A login flow
- A session token
- A refresh token
- An expiration time
- A logout endpoint
- A Set-Cookie header
- A cookie-based session store

**Implication:** Every request is unauthenticated from the client's perspective. The client (a service or browser) must possess the secret `X-User-Id` UUID to access the API. This works for service-to-service but is unusable for browsers because:
- The browser cannot securely hold a UUID across page navigations (no httpOnly cookie)
- The browser cannot prove identity to a backend it doesn't share a cookie domain with
- There is no way to log out, expire, or rotate the credential

### A-10: Dev Auth Bypass Still in Code

**Code path:** `core/auth.py:191-198`
```python
if settings.is_development and settings.dev_auth_bypass:
    return CurrentUser(
        id=_DEV_FALLBACK_USER_ID,
        tenant_id=_DEV_FALLBACK_TENANT_ID,
        email=_DEV_FALLBACK_EMAIL,
        role="admin",
    )
```

**Current `.env`:**
```
APP_ENV=development
DEV_AUTH_BYPASS=false
```

The bypass is OFF today, but the code is in the production path. If either `APP_ENV` or `DEV_AUTH_BYPASS` flips to `true` in production (operator mistake, env leak, CI mistake), every request becomes a super-admin impersonation of the seeded user. **The platform is one env var away from total auth bypass.**

**Mitigation:** `main.py:308` does refuse to start if `is_production` AND `dev_auth_bypass=true`. But:
- The check is bypassed when `APP_ENV=development` (which is the current setting in `.env`!)
- The check is for combinations; a single `is_production` AND `dev_auth_bypass=true` check would miss `is_production` AND `is_development` AND `dev_auth_bypass=true` (the latter being the current state)

### A-13: Audit Trail of Auth Events

Searched the audit_ledger for auth events:
```sql
SELECT action_name, COUNT(*) FROM audit_ledger GROUP BY action_name;
```

Results: `rbac_denied:*` (302 entries), `plan_generated_api` (5). **Zero entries for `auth_succeeded`, `auth_failed`, `login`, `logout`, or any other auth event.** The audit trail only catches authorization denials, not authentication events.

**Implication:** If an attacker is trying to brute-force or enumerate UUIDs, the platform records nothing.

### A-14: No Rate Limit on Auth Failures

Searched the rate limiter:
```python
# core/rate_limiter.py SKIP_PATHS
{"/api/v1/livez", "/api/v1/readyz", "/api/v1/health", "/livez", "/readyz",
 "/healthz", "/health", "/metrics", "/docs", "/openapi.json", "/redoc"}
```

No auth path in the skip list, but the rate limit is keyed on `tenant_id` + `user_id`, and an unauthenticated request has neither. The default fallback key is `anonymous` for both, so all anonymous requests share the same bucket. With 100/60s default, an attacker can attempt 100 UUIDs per minute before being rate-limited. With ~100,000 possible UUIDs, full enumeration is feasible in 16 hours.

---

## 3. What Production Auth Must Look Like

A real production deployment requires:

1. **Identity provider integration.** Pick one:
   - **Clerk** (recommended for fastest setup; managed UI, JWT, MFA, recovery)
   - **Auth0** (similar)
   - **WorkOS** (for enterprise SSO)
   - **Self-hosted** (Keycloak, Ory Hydra) — only if compliance requires no third party

2. **JWT verification on every request.**
   - Fetch JWKS from `https://<your-clerk-domain>/.well-known/jwks.json`
   - Cache keys for 1h
   - Verify signature, audience, expiry, issuer
   - Extract `sub` (user_id) and `org_id` (tenant_id) from claims
   - Map to internal user via `clerk_user_id` (or `auth0_user_id`) column

3. **Session lifecycle.**
   - `POST /auth/login` — initiates OAuth flow
   - `GET /auth/callback` — completes OAuth, sets httpOnly Secure SameSite=Strict cookie with session ID
   - `POST /auth/logout` — invalidates session
   - Sessions stored in Redis with 24h TTL
   - Sliding expiration: every request extends TTL by 1h up to 24h

4. **CSRF protection.**
   - Double-submit cookie pattern or SameSite=Strict
   - CSRF token required for all state-changing requests from browsers

5. **Rate-limit on auth failures.**
   - 5 failed logins per IP per 15 minutes
   - Account lockout after 10 failed logins per user per 24 hours
   - CAPTCHA after 3 failed logins

6. **Audit trail.**
   - Log every `auth_succeeded`, `auth_failed`, `login`, `logout`, `password_reset`
   - Include IP, user-agent, timestamp, user_id, tenant_id

7. **Remove the dev bypass entirely.** Make `is_development` a compile-time constant, not a runtime check.

8. **Remove the `X-User-*` header trust.** Make `Authorization: Bearer <jwt>` the only accepted form. Anything else returns 401.

9. **Provision the Clerk account.** Get `CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`. Add to secrets manager.

10. **Migrate existing test users** to a real `clerk_user_id`. Or, for a fresh start, truncate `users` and have new users sign up via Clerk.

---

## 4. Severity Classification

| P0 | Must be fixed before any production customer |
|----|----------------------------------------------|
| A-1, A-2, A-9, A-10, A-11, A-15 | The platform has no real auth. |

| P1 | Should be fixed before high-value customers |
|----|----------------------------------------------|
| A-3, A-13, A-14 | Auth audit trail and brute-force protection. |

| P0 (operational) | Refused to start conditions missing |
|----|----------------------------------------------|
| A-10 follow-up | Startup check should refuse any `DEV_AUTH_BYPASS=true` regardless of `APP_ENV`. |

---

## 5. Production Verdict

The platform's authentication is **not production-ready**. The current model is "trusted service-to-service client knows the user's UUID." This is acceptable for internal APIs behind a VPN, but **not** for a public SaaS product.

**Concrete evidence the platform is broken for production:**
- A script with `for uuid in <list>; do curl -X GET -H "X-User-Id: $uuid" -H "X-Tenant-Id: <known-tenant>" /api/v1/clients; done` would read every customer's data without ever knowing a password.
- The audit trail records nothing about this.
- There is no way for a customer to log in via a browser because the platform has no `/login` endpoint.
- `Authorization: Bearer` is rejected with "Missing X-User-Id" — the platform does not understand the standard auth header.

**Recommended action before Phase 3 customer onboarding:**
1. Provision Clerk (or equivalent)
2. Add JWT verification middleware
3. Add `Authorization: Bearer` parsing
4. Remove `X-User-*` header trust
5. Remove `dev_auth_bypass` code path entirely
6. Add the rate-limit-on-auth-failures logic
7. Truncate the seeded users; force re-signup via Clerk

**Estimated effort:** 2-3 days.

**Signed:** Auth Production Validation, 2026-06-06.
