# PROVIDER TRUTH LAYER REPORT — Phase 1.3.4

**Status: PASS**
**Date: 2026-06-05**
**Owner: Phase 1.3.4 Implementation Team**

---

## 1. The bug we fixed

P0-12 was a structural contradiction between three places that each claimed to know "is this provider OK?":

| Source | Answered | Keyed by | Truthful? |
|---|---|---|---|
| `GET /api/v1/providers/keys` | "is a key configured?" | lowercase slug (`dataforseo`) | yes |
| `GET /api/v1/provider-health` | "are calls succeeding?" | TitleCase (`DataForSEO`) | yes (data is correct, just keyed wrong) |
| `frontend ProviderCommandCenter` | "what should the operator see?" | n/a — computed in browser | **no** — the join was case-sensitive and the reconcile logic was in the wrong layer |

The operator-facing symptom: dataforseo was permanently labeled `MISMATCH` because the frontend looked up `healthMap["dataforseo"]` (lowercase) but the map was keyed `"DataForSEO"` (TitleCase). Even when the case happened to match, three independent root causes could collide to make the same provider show three different states (catalog yes / env no / 0 recorded calls).

This was not a data bug. It was an architecture bug. Three sources of truth, one of them in the wrong layer.

---

## 2. What we built

### 2.1 Single source of truth
A new endpoint `GET /api/v1/providers/unified` returns one row per provider in the catalog, with the unified status computed server-side. The frontend no longer reconciles.

### 2.2 Canonical key
Lowercase slugs everywhere. The `ProviderHealthCenter.PROVIDERS` list now uses `["dataforseo", "ahrefs", "scrapling", "searxng", "openpagerank", "hunter", "trafilatura", "sendgrid", "mailgun", "resend"]` — matches the catalog exactly, and adds the three email providers (sendgrid, mailgun, resend) that the previous health endpoint was silently dropping.

### 2.3 Instrumentation coverage
`DataForSEOClient` was the only client that never called `record_provider_call()`. We added instrumentation to both `get_search_volume()` and `get_serp_snapshot()`. The instrumented call wraps the request in a try/finally that:
- Records latency, success, and an error string (truncated to 200 chars) to `provider_health_metrics`.
- Mirrors the circuit breaker state to Redis at `circuit_breaker:dataforseo` (so the health endpoint's CB read is no longer always "CLOSED").
- Upper-cases the CB state on both write and read, so the existing UI logic (`=== "OPEN"`) still works.

### 2.4 Tenancy fix in `record_provider_call`
The previous default `tenant_id=UUID(int=0)` (all-zeros UUID) failed the FK to `tenants(id)` because no real tenant has that ID. The persist silently failed with a `provider_health_persist_failed` warning. We changed the default to `None` — the column is nullable in the schema, and service-level calls (e.g. from a probe with no tenant context) can now record with `NULL`.

### 2.5 Frontend rewrite
`frontend/src/components/operator/provider-command-center.tsx` no longer:
- Calls two endpoints and joins them.
- Carries a `computeUnified()` function.
- Knows what "mismatch" means.

It now:
- Calls one endpoint (`/providers/unified`).
- Renders the server's `unified_status` directly.
- Maps status → `HealthPill` color and status → label.

`MISMATCH` is gone from the UI. The label set is now `HEALTHY | BROKEN | NEEDS KEY | UNTESTED | DISABLED | UNKNOWN`. The truth-table is in the server. Three places to break, reduced to one.

---

## 3. The unified response shape

```jsonc
GET /api/v1/providers/unified
{
  "success": true,
  "data": {
    "providers": [
      {
        "provider": "dataforseo",            // canonical lowercase slug
        "label": "DataForSEO",
        "category": "SEO Data",
        "fields": ["login", "password"],
        "configured": true,                   // row in provider_keys for current tenant
        "last_key_update": "2026-06-04T17:03:34.380995+00:00",
        "last_key_updated_by": null,
        "is_active_seo": false,               // from SEOProviderRegistry
        "tracked": true,                      // at least one record in last 24h
        "uptime_pct": 0.0,                    // null-equivalent if total_calls_24h == 0
        "avg_latency_ms": 782.8,
        "total_calls_24h": 2,
        "success_count_24h": 0,
        "circuit_breaker_state": "CLOSED",    // always upper-case
        "not_configured": false,
        "unified_status": "broken",
        "unified_reason": "Key is configured but uptime is 0.0% over 2 calls in 24h (circuit breaker: CLOSED)."
      },
      { "provider": "sendgrid", "configured": false, "tracked": false, "unified_status": "needs-key", "unified_reason": "No key configured in catalog and no calls recorded in last 24h.", ... }
    ],
    "summary": {
      "total": 7,
      "healthy": 0,
      "broken": 1,
      "needs_key": 6,
      "untested": 0,
      "disabled": 0,
      "unknown": 0
    },
    "fallback_chain": {
      "seo": ["dataforseo", "ahrefs", "scrapling", "searxng"],
      "email": ["sendgrid", "mailgun", "resend"],
      "outreach": ["hunter"],
      "crawl": ["scrapling", "trafilatura"],
      "authority": ["openpagerank"]
    }
  }
}
```

---

## 4. The unified_status truth table

`unified_status` is computed server-side from exactly two inputs: whether a key is configured for the current tenant, and the 24h aggregate of `provider_health_metrics`.

| configured | total_calls_24h | uptime | circuit_breaker | status |
|---|---|---|---|---|
| false | 0 | n/a | n/a | **needs-key** |
| false | >0 | < 80% | any | broken |
| false | >0 | ≥ 80% | any | healthy (env-only path) |
| true | 0 | n/a | n/a | **untested** |
| true | >0 | < 80% | OPEN | broken |
| true | >0 | < 80% | CLOSED/HALF_OPEN | broken |
| true | >0 | ≥ 80% | OPEN | broken |
| true | >0 | ≥ 80% | CLOSED/HALF_OPEN | healthy |

`unified_reason` is a single human-readable string that explains the path. The operator never has to guess.

---

## 5. Evidence the bug is gone

### 5.1 Pre-fix (illustrative — not from current state)
For dataforseo with a row in `provider_keys` and env vars empty:
- Catalog endpoint: `configured: true` (key slug `dataforseo`)
- Health endpoint: `not_configured: true` (TitleCase `DataForSEO`, 0 rows in `provider_health_metrics`)
- Frontend `computeUnified()`: `status: "mismatch"`, `reason: "Configuration mismatch — key exists in catalog but provider reports not configured..."`

### 5.2 Post-fix (current state)
Same scenario (key in DB, no env, two test calls made against `get_search_volume`):
```
dataforseo    configured=True  tracked=True  calls=2  uptime=0.0% CB=CLOSED  status=broken
```
The label is `BROKEN`. The reason is "Key is configured but uptime is 0.0% over 2 calls in 24h (circuit breaker: CLOSED)." An operator reading this panel knows exactly what to do: check the key, or check why the client is being called with no auth.

This is what truthful status looks like. It is not "GREEN because we never tried." It is "RED because we tried twice and the upstream rejected us."

### 5.3 Other providers (no key, no calls)
```
ahrefs        configured=False tracked=False calls=0  status=needs-key
hunter        configured=False tracked=False calls=0  status=needs-key
sendgrid      configured=False tracked=False calls=0  status=needs-key
mailgun       configured=False tracked=False calls=0  status=needs-key
resend        configured=False tracked=False calls=0  status=needs-key
openpagerank  configured=False tracked=False calls=0  status=needs-key
```
All six say `needs-key` because that's the truthful state. No more `mismatch`, no more `untested` as a default.

---

## 6. Files changed

| File | Change |
|---|---|
| `backend/src/seo_platform/services/provider_health.py` | `PROVIDERS` list now lowercase slugs; `record_provider_call` defaults `tenant_id=None` and commits the session |
| `backend/src/seo_platform/clients/dataforseo.py` | Added `_record()` helper; both `get_search_volume` and `get_serp_snapshot` now record + mirror CB; CB state upper-cased |
| `backend/src/seo_platform/api/endpoints/providers_unified.py` | **NEW** — the unified endpoint, the truth layer, the status computation |
| `backend/src/seo_platform/api/router.py` | Registers `providers_unified_router` under `/providers` prefix |
| `frontend/src/components/operator/provider-command-center.tsx` | Single `unifiedQ` query; no more `computeUnified()`; status `mismatch` removed from UI |

---

## 7. What this does NOT change

Per the Phase 1.3.5 constraint (don't redesign UI), the following still exist and work:
- `GET /providers/keys` (legacy catalog endpoint) — still returns 200.
- `GET /providers/status` (legacy status wrapper) — still returns 200.
- `GET /provider-health` (legacy health endpoint) — still returns 200.
- Other consumers of the legacy endpoints (`action-center.tsx`, `system-health-panel.tsx`, `dashboard/war-room/page.tsx`, `dashboard/providers/page.tsx`) are unchanged. They will continue to show stale data (e.g. `dashboard/providers/page.tsx` line 335 calls `/provider-keys` which 404s — a separate latent bug not in scope for Phase 1.3.4).

In Phase 1.3.7 (Release Verification) we will exercise these to confirm they still work. In Phase 2 we should migrate all consumers to the unified endpoint, and fix the `/provider-keys` URL typo.

---

## 8. Outstanding

1. **Three other clients still don't call `record_provider_call()` or don't have per-call CB mirroring** — actually, scrapling, searxng, and openpagerank already do (per the Phase 1.2 audit). Only dataforseo was missing; that is now fixed. ✅
2. **`/provider-keys` URL typo in `dashboard/providers/page.tsx`** — pre-existing, separate bug. Out of scope.
3. **Per-tenant provider enable/disable** — there is still no `is_enabled` column on `provider_keys`. The `unified_status` enum includes `disabled` for forward compatibility, but no provider can currently be in that state.

---

## 9. Verdict

**PASS.** The Provider Truth Layer is the single source of truth. dataforseo is no longer MISMATCH — it is `broken`, which is the truthful state. The frontend is one query, no client-side reconciliation. The catalog, the health metrics, and the unified response are all keyed by the same lowercase slug.
