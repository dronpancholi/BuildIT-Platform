# 10. PHASE_11_REMEDIATION_PLAN.md
**Phase 11 — Productionization & Fix Plan**
**Date:** 2026-06-14

## Priority Classification

### P0 — CRITICAL (Blocks real work)

| # | Issue | Root Cause | File | Fix | Effort |
|---|-------|------------|------|-----|--------|
| P0-1 | Simulated link intersect generates fake domains | Fallback produces non-existent domains | `services/scraping/engines/backlinks.py:129-162` | Remove fake data, return empty list with error | 30min |
| P0-2 | Fake forecast data | Falls back to fabricated historical values | `services/forecasting.py:108,149,184,213` | Return "insufficient data" instead of fake values | 30min |
| P0-3 | Hardcoded keyword volumes | Fallback returns fake volume/difficulty | `workflows/__init__.py:317` | Return keywords without metrics, mark as "unresearched" | 15min |
| P0-4 | Hardcoded domain health | Returns 0.98 for every domain | `services/deliverability/engine.py:31-44` | Return "not checked" status | 15min |

### P1 — HIGH (Misleading but not blocking)

| # | Issue | Root Cause | File | Fix | Effort |
|---|-------|------------|------|-----|--------|
| P1-1 | Copilot branded as AI | Keyword matching, no LLM | `services/copilot.py` | Relabel as "Quick Query" in frontend | 15min |
| P1-2 | Recommendations branded as AI | Threshold rules, no LLM | `services/ai_recommendations.py` | Relabel as "Smart Alerts" in frontend | 15min |
| P1-3 | Campaign Agent branded as AI | Status checks, no LLM | `services/campaign_agent.py` | Remove "Agent" branding or integrate LLM | 1hr |
| P1-4 | Audit trail not capturing | AuditLogger not wired to middleware | `core/audit_log.py` | Wire AuditLogger to request middleware | 1hr |
| P1-5 | Hardcoded demo email | `demo@buildit.local` in production code | `api/endpoints/campaigns.py:837` | Use configured sender email | 15min |
| P1-6 | Error messages opaque | Generic "internal error" responses | `api/middleware.py` | Add actionable error details | 1hr |

### P2 — MEDIUM (Quality improvements)

| # | Issue | Root Cause | File | Fix | Effort |
|---|-------|------------|------|-----|--------|
| P2-1 | No API key config UI | Must edit .env in terminal | Frontend Settings | Add API key input fields | 2hr |
| P2-2 | No Temporal status indicator | Operator doesn't know Temporal is required | Frontend Dashboard | Add service status panel | 1hr |
| P2-3 | Maintainability scores hardcoded | Static values for all analyses | `services/maintainability_dominance.py` | Compute real scores or remove | 2hr |
| P2-4 | Spam heuristic is toy | Naive word-matching | `services/deliverability/engine.py:46-64` | Integrate real spam checker | 2hr |
| P2-5 | Plan simulator has misleading docstring | Says "mock" but is no-op | `services/plan_simulator.py` | Update docstring | 5min |

## Implementation Plan

### Phase 11A: Remove All Fakes (P0) — 1.5 hours
1. Remove simulated link intersect matrix
2. Remove fake forecast fallback data
3. Remove hardcoded keyword volumes
4. Remove hardcoded domain health

### Phase 11B: Fix Branding & Wiring (P1) — 3 hours
1. Relabel copilot as "Quick Query"
2. Relabel recommendations as "Smart Alerts"
3. Fix audit trail wiring
4. Fix demo email
5. Improve error messages

### Phase 12: Operator Experience (P2) — 6 hours
1. Add API key configuration UI
2. Add service status dashboard
3. Fix maintainability scores
4. Improve spam heuristic

## Total Estimated Effort: ~10.5 hours

## Risk Assessment

| Fix | Risk | Mitigation |
|-----|------|------------|
| Remove fake data | LOW | Operators get honest "no data" instead of fake data |
| Relabel AI systems | LOW | Operators know what they're getting |
| Fix audit trail | MEDIUM | Need to verify middleware integration |
| Add API key UI | MEDIUM | Must handle encryption properly |
| Add service status | LOW | Read-only dashboard |
