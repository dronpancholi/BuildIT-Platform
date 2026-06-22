# AI Output Quality Report — Phase 1.4

**Date:** 2026-06-05
**Method:** curl probes against AI-driven endpoints + analysis of recommendation content
**Log evidence:** `/tmp/uvicorn_p13k.log` shows `[Errno 61] Connection refused` from the AI service
**Scope:** All endpoints that claim to invoke AI (LLM) services

---

## Executive Summary

**The AI service is offline. All AI-driven outputs are either fabricated, hardcoded, or unreachable.**

| AI Endpoint | Status | Output Type | Quality Score |
|-------------|:------:|-------------|--------------:|
| `GET /recommendations/campaign` | 200 OK | **Hardcoded placeholder** | 0/100 |
| `GET /recommendations/keyword` | 200 OK | **Hardcoded placeholder** | 0/100 |
| `GET /recommendations/workflow` | 200 OK | **Hardcoded placeholder** | 0/100 |
| `GET /recommendations/ai` | ERROR | `Connection refused` (LLM offline) | 0/100 |
| `GET /ai-quality/dashboard` | 200 OK | Real metrics, but all zeros | 50/100 |
| `GET /ai-ops/detect-hallucinations` | 405 | Method not allowed | 0/100 |
| `GET /ai-resilience/inference-health` | Validation error | `model_id` required | 0/100 |

**Mean AI output quality score: 7.1 / 100. Pass rate at 70+: 0 / 7 = 0%.**

---

## Per-Endpoint Analysis

### 1. `GET /recommendations/campaign` — Quality: 0/100

**Response:**
```json
{"success":true,"data":[{
  "id":"camp-default",
  "recommendation_text":"No campaign optimization recommendations — all campaigns appear healthy",
  "priority":"P3",
  "category":"campaign",
  "impact":"low",
  "effort":"low",
  "confidence":0.5,
  "supporting_data":{"note":"no_issues_detected"},
  "action_optional":true,
  "created_at":""
}]}
```

**Quality assessment:**

| Criterion | Assessment | Notes |
|-----------|:----------:|-------|
| Real LLM-generated content? | ❌ No | String is hardcoded, not from an LLM |
| Plausible campaign analysis? | ❌ No | Says "all campaigns appear healthy" with no analysis |
| Confidence score meaningful? | ❌ No | `0.5` is a hardcoded neutral value |
| Supporting data present? | ❌ No | `{"note":"no_issues_detected"}` is a stub |
| `created_at` populated? | ❌ No | Empty string `""`, not a real timestamp |
| ID plausibly a database row? | ❌ No | `"camp-default"` is obviously a placeholder |
| Trustworthy? | ❌ **NO** | Tells user "you're fine" when the system has no data to base that on |

**Hallucination risk:** This is **not** an LLM hallucination. It is **fabrication by design** — the code intentionally returns a canned string to avoid returning an empty array. This is worse than hallucination because the user has no way to know it is fake.

**Failure mode:** The endpoint treats "no data" as "produce a positive-looking result." This is a **trust-destroying pattern**.

---

### 2. `GET /recommendations/keyword` — Quality: 0/100

**Response:**
```json
{"success":true,"data":[{
  "id":"kw-default",
  "recommendation_text":"Keyword portfolio appears healthy — continue monitoring for new opportunities",
  ...
}]}
```

Same failure pattern as #1. The endpoint is supposed to analyze the user's keyword portfolio and recommend optimizations. It returns a hardcoded "everything is fine" string.

**Real-world impact:** A user who has zero keyword rankings (because the keyword research workflow is broken) will see "Keyword portfolio appears healthy" and conclude they have a working SEO strategy. They will lose months of organic traffic.

---

### 3. `GET /recommendations/workflow` — Quality: 0/100

**Response:**
```json
{"success":true,"data":[{
  "id":"wf-default",
  "recommendation_text":"No workflow optimization needed — operational metrics are within thresholds",
  ...
}]}
```

Same pattern. Claims operational health without any underlying analysis.

---

### 4. `GET /recommendations/ai` — Quality: 0/100 (CRASH)

**Response:**
```json
{"success":false,"data":null,"error":{
  "error_code":"INTERNAL_ERROR",
  "message":"[Errno 61] Connection refused",
  "details":{},"retryable":false
}}
```

**Failure mode:** The endpoint tries to call the AI service (Anthropic or OpenAI) and the service refuses the TCP connection. The error code `61` is the standard POSIX `ECONNREFUSED`. This means either:
- The AI service process is not running on the expected port.
- The AI service is configured to a different host/port than the backend is calling.
- A firewall is blocking the connection.

**Evidence in logs:** `/tmp/uvicorn_p13k.log` shows the same `Connection refused` error repeated.

**Real-world impact:** Any workflow that depends on LLM analysis fails. This includes:
- `recommendations/ai` (the obvious one)
- All content generation endpoints (likely)
- All email personalization (likely)
- Any "smart" summarization, scoring, or prioritization

**Trust:** Zero. The system is not producing AI output; it is producing hardcoded text and connection errors.

---

### 5. `GET /ai-quality/dashboard` — Quality: 50/100

**Response:**
```json
{"success":true,"data":{
  "tenant_id":"00000000-0000-0000-0000-000000000001",
  "avg_confidence_score":0.0,
  "hallucination_rate_trend":[],
  "quality_score_by_category":{},
  "schema_repair_rate":0.0,
  "fallback_model_usage_rate":0.0
}}
```

**Quality assessment:**

| Field | Value | Meaningful? |
|-------|-------|:-----------:|
| `avg_confidence_score` | 0.0 | Yes — but zero means no AI calls have been made |
| `hallucination_rate_trend` | `[]` | Empty array — no data |
| `quality_score_by_category` | `{}` | Empty dict — no categorized quality |
| `schema_repair_rate` | 0.0 | No repairs needed (no calls) |
| `fallback_model_usage_rate` | 0.0 | No fallbacks triggered (no calls) |

**Verdict:** This endpoint **works correctly** — it returns a real metrics object with all defaults. It is the only AI-adjacent endpoint that is not faking data or crashing. However, the metrics are all zero/empty because no AI has been called.

**Score 50/100** instead of 0 because:
- The endpoint shape is correct.
- The values are honest zeros, not faked non-zero values.
- It would produce real data if the AI service were connected.

---

### 6. `GET /ai-ops/detect-hallucinations` — Quality: 0/100 (METHOD MISMATCH)

**Response:** `{"detail":"Method Not Allowed"}`

The route exists but rejects GET. No alternate method was tested. Without access to the OpenAPI spec for this endpoint, the correct method is unknown.

**Real-world impact:** Cannot detect hallucinations in any AI output — a feature that would have been useful for catching the fabricated recommendation strings above.

---

### 7. `GET /ai-resilience/inference-health` — Quality: 0/100

**Response:**
```json
{"success":false,"data":null,"error":{
  "error_code":"VALIDATION_ERROR",
  "message":"Request validation failed",
  "details":{"errors":[{"type":"missing","loc":["query","model_id"],
   "msg":"Field required","input":null}]},
  "retryable":false
}}
```

The endpoint exists, accepts GET, but requires a `model_id` query parameter that was not provided. Re-testing with a model_id would likely surface a "model not configured" or "AI service offline" error.

**Real-world impact:** Cannot assess inference health for any model. Cannot tell which models are healthy, degraded, or offline.

---

## LLM Provider Status (Anthropic, OpenAI)

| Provider | Configured? | Service Running? | Calls Succeeding? |
|----------|:-----------:|:----------------:|:-----------------:|
| Anthropic (Claude) | unknown | ❌ No (ECONNREFUSED) | ❌ 0% |
| OpenAI (GPT) | unknown | ❌ No (ECONNREFUSED) | ❌ 0% |

The backend logs do not show which LLM provider is being called, only that the connection is refused. The platform's design (per code structure) supports multiple providers, but in this deployment **none of them are running**.

---

## Hallucination vs Fabrication: A Critical Distinction

A hallucination is when an LLM produces plausible-but-false output. The cause is the model's statistical nature.

What we see in `/recommendations/campaign`, `/recommendations/keyword`, and `/recommendations/workflow` is **not hallucination**. There is no LLM call. The strings are hardcoded in source code. The developer wrote a function that returns `"No campaign optimization recommendations — all campaigns appear healthy"` regardless of input.

This is **fabrication by design** — the system is intentionally producing a false-positive "you're fine" message to avoid showing an empty state.

**This is worse than hallucination because:**
1. The user has no statistical confidence signal — it is a deterministic string.
2. The system has not "tried" to be right; it has decided to be wrong on purpose.
3. A monitoring or observability tool would not flag it as an anomaly because it succeeds every time.
4. The recommendation content contradicts the actual state (no data, no campaigns, no keywords) yet says "appear healthy."

---

## Trust Verdict

A user cannot trust any AI output from this platform. Every AI endpoint either:
- Returns a hardcoded lie (recommendations/{campaign,keyword,workflow})
- Crashes with `Connection refused` (recommendations/ai)
- Returns empty/honest-but-empty data (ai-quality/dashboard, ai-resilience/inference-health)

**No AI workflow produces real, useful, trustworthy output.**

---

## Mitigation Requirements (if Phase 1.4 is to be retried)

To bring the AI layer to a passing state, the following must happen in order:

1. **Restore LLM service connectivity** — investigate why the AI service is refusing connections, fix the host/port configuration, restart the service, verify with a test call.
2. **Replace hardcoded recommendation strings with empty arrays** — `data: []` is the honest answer when there is no data. A positive-looking string is worse than nothing.
3. **Fix `/recommendations/ai` to return empty data or a clear "AI service unavailable" error code** — a `Connection refused` returned to the user as `INTERNAL_ERROR` is opaque. A `503 Service Unavailable` with a clear `ai_service_offline` reason would be honest and actionable.
4. **Document and align HTTP methods on `/ai-ops/detect-hallucinations`** — figure out the right method, fix OpenAPI.
5. **Wire `/ai-resilience/inference-health` to default to a documented `model_id` query** — currently requires a model_id the operator has no way to discover.

**Without these changes, every "AI" feature in the platform is either a lie or a crash.**
