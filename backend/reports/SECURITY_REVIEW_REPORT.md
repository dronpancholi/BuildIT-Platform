# Security Review Report — Phase 14.3B

## Scope

Audited RBAC enforcement across all planning-related API endpoints and supporting authentication infrastructure.

## Methodology

- Reviewed endpoint files in `api/endpoints/` for `Depends(get_current_user)` and `Depends(_require_admin)` usage
- Traced RBAC dependency functions in `api/dependencies.py`, `core/auth.py`, and `core/rbac.py`
- Checked audit ledger integration for RBAC failures

## Findings

### Endpoint Coverage Summary

| File | Total Endpoints | Protected | Unprotected |
|------|----------------|-----------|-------------|
| `plans.py` | 11 | 0 | 11 |
| `goals.py` | 6 | 6 | 0 |
| `semantic_memory.py` | 14 | 0 | 14 |
| `approvals.py` | 2 | 0 | 2 |
| `approvals_v2.py` | 2 | 0 | 2 |
| **Total** | **35** | **6** | **29** |

### Critical Findings

#### 1. 29 Endpoints Missing RBAC (Severity: CRITICAL)

All mutable operations on plans (approve, reject, generate, simulate, optimize) and all memory/approval endpoints are unprotected.

**`plans.py`** — `_require_admin` is defined at line 33 but never wired into any route.
**`semantic_memory.py`** — Zero auth infrastructure. No imports from `core.auth`.
**`approvals.py` / `approvals_v2.py`** — Approval decisions (state-changing operations) exposed without access control.

#### 2. Role Name Mismatch (Severity: HIGH)

- `_require_admin` checks for `{"super_admin", "tenant_admin", "manager"}`
- `core/rbac.py` defines role as `"admin"`, not `"tenant_admin"` 
- `core/auth.py` mock returns `role="admin"` which would fail the check

This means even the correctly-wired `goals.py` endpoints always return 403 in development.

#### 3. No Audit for RBAC Failures (Severity: MEDIUM)

No `AuditLedgerEntry` records are created when 403 is raised. Permission-denied events are invisible in the audit trail.

#### 4. Rate Limiting

Rate limiting middleware is active (`core/rate_limiter.py`), confirmed by middleware chain in error traceback.

## Verdict

| Requirement | Status |
|-------------|--------|
| RBAC on `/plans/*` | ❌ Not enforced |
| RBAC on `/goals/*` | ✅ Enforced (but has role-name bug) |
| RBAC on `/memory/*` | ❌ Not enforced |
| RBAC on `/approvals/*` | ❌ Not enforced |
| Audit entries for operations | ✅ Partial (plans.py) |
| Audit entries for RBAC failures | ❌ Missing |
| Rate limiting active | ✅ Confirmed |
| Approval enforcement active | ✅ Confirmed (governance engine) |

## Recommendations

1. Wire `Depends(_require_admin)` (or equivalent) into all unprotected endpoints
2. Fix role-name mismatch: unify to one role vocabulary
3. Add `AuditLedgerEntry` creation on 403 for RBAC failures
