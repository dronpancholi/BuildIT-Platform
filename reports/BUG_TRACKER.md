# Phase 10: Bug Tracker

**Date:** 2026-05-31  
**Total Bugs Found:** 6  
**Fixed:** 3 | **Remaining:** 3

---

## FIXED BUGS

### BUG-001: Client CRUD Endpoints Return 404

| Field | Detail |
|-------|--------|
| **Severity** | CRITICAL |
| **Status** | FIXED |
| **Endpoints** | `GET /api/v1/clients/:id`, `PUT /api/v1/clients/:id`, `DELETE /api/v1/clients/:id` |
| **Reproduction** | `curl /api/v1/clients/<valid-id>` → 404 Not Found |
| **Root Cause** | Client routes not mounting UUID path parameters correctly |
| **Fix Applied** | Route parameter binding fixed in client router |
| **Verification** | All 3 endpoints now return 200 OK |

### BUG-002: Campaign Create Returns 500 on Invalid FK

| Field | Detail |
|-------|--------|
| **Severity** | HIGH |
| **Status** | FIXED |
| **Endpoint** | `POST /api/v1/campaigns` |
| **Reproduction** | POST campaign with non-existent `client_id` → 500 Internal Server Error |
| **Root Cause** | Missing foreign key validation before insert |
| **Fix Applied** | Added FK existence check before database insert |
| **Verification** | Now returns 400 Bad Request with descriptive error |

### BUG-003: Prospect Discovery Fails Without `competitor_domains`

| Field | Detail |
|-------|--------|
| **Severity** | MEDIUM |
| **Status** | FIXED |
| **Endpoint** | `POST /api/v1/campaigns/:id/discover` |
| **Reproduction** | POST discover without `competitor_domains` field → error |
| **Root Cause** | Required field not handled gracefully |
| **Fix Applied** | Made `competitor_domains` optional with sensible defaults |
| **Verification** | Discovery runs without competitor domains |

---

## REMAINING BUGS

### BUG-004: Plan Generate Requires `goal_execution_id`

| Field | Detail |
|-------|--------|
| **Severity** | MEDIUM |
| **Status** | OPEN |
| **Endpoint** | `POST /api/v1/plans/generate` |
| **Reproduction** | POST to `/api/v1/plans/generate` → 422 Unprocessable Entity |
| **Root Cause** | Endpoint requires `goal_execution_id` in request body, which is not documented or obtainable through normal flow |
| **Impact** | Plan generation workflow cannot be used end-to-end |
| **Suggested Fix** | Either auto-generate `goal_execution_id` or make field optional |

### BUG-005: Redis DOWN — Full Functionality Blocked

| Field | Detail |
|-------|--------|
| **Severity** | HIGH |
| **Status** | OPEN |
| **Component** | Redis cache/session store |
| **Reproduction** | `redis-cli ping` → Connection refused |
| **Root Cause** | Redis server not running |
| **Impact** | Caching, session management, rate limiting, and queue operations degraded |
| **Suggested Fix** | Start Redis: `brew services start redis` or `redis-server` |

### BUG-006: Two Dead Routes Still Registered

| Field | Detail |
|-------|--------|
| **Severity** | LOW |
| **Status** | OPEN |
| **Routes** | `/demo-scenarios`, `/api/v1/demo-scenarios` |
| **Reproduction** | GET either route → 404 or no response |
| **Root Cause** | Routes registered in router but no handler implemented |
| **Impact** | Dead code — no functional impact |
| **Suggested Fix** | Remove route registrations or implement handlers |

---

## Bug Severity Distribution

| Severity | Count | Fixed | Remaining |
|----------|-------|-------|-----------|
| CRITICAL | 1 | 1 | 0 |
| HIGH | 2 | 1 | 1 |
| MEDIUM | 2 | 1 | 1 |
| LOW | 1 | 0 | 1 |
| **TOTAL** | **6** | **3** | **3** |

---

## Remaining Risk Assessment

| Bug | Risk Level | Mitigation |
|-----|-----------|------------|
| BUG-004 (Plan Generate) | Medium | Use Plan List workflow instead |
| BUG-005 (Redis DOWN) | High | Start Redis before demo |
| BUG-006 (Dead Routes) | Low | Ignore — cosmetic issue |
