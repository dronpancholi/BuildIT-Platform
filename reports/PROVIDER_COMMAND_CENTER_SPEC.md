# PHASE 1.2.3 — Provider Command Center Spec

## Purpose
Single source of truth for provider status. Resolves the Phase 1.1.5 P0-12 contradiction (keys catalog vs status endpoint disagree).

## Scope
The `/dashboard/providers` page.

## The Data Conflict (P0-12)
- `/api/v1/providers/keys` returns `catalog: [{provider, configured: true/false}]` — 7 providers
- `/api/v1/provider-health` returns `providers: {Name: {not_configured, healthy, ...}}` — 8 providers
- These two lists don't fully overlap by name, AND they disagree on configuration state (dataforseo: configured in catalog, not_configured in health).

## Resolution Strategy
Use the **keys catalog as the source of truth for "is this provider configured?"**.
Use **provider-health for "is this provider healthy right now?"**.

Compute a unified status per provider:
- `configured` (from keys catalog)
- `healthy` (from provider-health, case-insensitive name match)
- `effective_status`:
  - if not configured → `NOT CONFIGURED` (warning, not critical)
  - if configured and healthy → `HEALTHY`
  - if configured and not healthy → `BROKEN` (critical)
  - if configured but missing from health endpoint → `UNKNOWN`

This is the only place this logic should exist. Other pages should consume the unified view, not re-derive it.

## Per-Provider Display

```
+------------------------------------------------------------------+
| DataForSEO                                          [HEALTHY]    |
| SEO Data                                                          |
+------------------------------------------------------------------+
| API Key:  Configured (updated 6h ago)                            |
| Last call: 2 min ago                                              |
| Last success: 2 min ago                                           |
| Last failure: none in last 7 days                                 |
| Uptime (24h): 99.4%                                               |
+------------------------------------------------------------------+
| [Test Connection]  [Retry Last Call]                              |
+------------------------------------------------------------------+
```

```
+------------------------------------------------------------------+
| Ahrefs                                              [NOT CONFIGURED] |
| SEO Data                                                          |
+------------------------------------------------------------------+
| API Key:  Not set                                                 |
| No traffic in last 24h                                            |
+------------------------------------------------------------------+
| [Add API Key]                                                     |
+------------------------------------------------------------------+
```

## Status Vocabulary

- **HEALTHY** — green. Configured + healthy.
- **NOT CONFIGURED** — amber. No API key set.
- **BROKEN** — red. Configured but circuit breaker open OR repeated failures.
- **UNKNOWN** — gray. Configured but no health data.

## Actions

- **Test Connection** — enabled when configured. Calls `POST /api/v1/providers/{name}/test` (if exists) or hits health endpoint. Shows "Testing..." → "OK" or "Failed: <plain-English reason>".
  - If no test endpoint exists, the button shows "Test endpoint not available — try a real call".
- **Retry Last Call** — enabled when configured AND last call failed. Calls a retry endpoint or refreshes health.
- **Add API Key** — opens a modal with the field schema (already exists).

## Aggregate Header
```
Providers  7 in catalog
- Configured  1 (DataForSEO)
- Not configured  6
- Healthy now  1
- Broken now  0
```

## Error / Inconsistency Display
If the keys catalog and health endpoint disagree on configuration state, show a **"Data discrepancy"** banner at the top:
> "Provider health endpoint is out of sync with the keys catalog. Showing catalog as source of truth."

## What this page does NOT do
- Does not show historical uptime charts
- Does not show per-call latency
- Does not show cost data

## Acceptance
- The same provider shows the SAME configured state in keys catalog and this view.
- "Broken" providers are visible in <1 second.
- Test Connection returns a result or a clear "not available" message — never silent.
