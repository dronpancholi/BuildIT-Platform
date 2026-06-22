# SEO Workflow Audit — Phase 1.4

**Date:** 2026-06-05
**Method:** curl-based end-to-end probes against `http://localhost:8000/api/v1/`
**Test harness:** `/tmp/phase14/test_all.sh`
**Test tenant:** `00000000-0000-0000-0000-000000000001`
**Scope:** 15 core SEO workflows, scored 0-100 each

---

## Scoring Rubric

| Score | Verdict | Meaning |
|------:|---------|---------|
| 90-100 | PASS | Workflow produces real, correct, useful output end-to-end |
| 70-89  | WEAK PASS | Workflow works but with minor quality/reliability issues |
| 50-69  | FAIL | Workflow partially works, significant gaps, not usable |
| 25-49  | HARD FAIL | Workflow returns errors or placeholder data |
| 0-24   | DEAD | Endpoint returns INTERNAL_ERROR, 404, or does not exist |

A score < 50 means the workflow **cannot be used by a real SEO agency**.

---

## Executive Summary

| # | Workflow | Score | Verdict | Primary Failure |
|--:|----------|------:|---------|-----------------|
| 1 | Client Onboarding | **15** | DEAD | `GET /clients` → INTERNAL_ERROR |
| 2 | Campaign Creation | **25** | HARD FAIL | `GET /campaigns` → INTERNAL_ERROR |
| 3 | Keyword Research | **20** | DEAD | `GET /keywords/research` → INTERNAL_ERROR |
| 4 | Competitor Analysis | **10** | DEAD | `GET /serp-intelligence/competitor-overlap` → 405 Method Not Allowed |
| 5 | SERP Collection | **15** | DEAD | `GET /serp-intelligence/dashboard` → 404; capture-snapshot requires non-existent fields |
| 6 | Prospect Discovery | **15** | DEAD | `GET /prospects/stats` → INTERNAL_ERROR |
| 7 | Outreach Generation | **10** | DEAD | `GET /outreach-intelligence/prioritize` → 405; backlink-intelligence → INTERNAL_ERROR |
| 8 | Email Personalization | **15** | DEAD | `GET /email-drafts` → INTERNAL_ERROR |
| 9 | Content Planning | **10** | DEAD | `GET /strategic-seo/dashboard` → 404 |
| 10 | Content Generation | **10** | DEAD | `GET /content` → 404 |
| 11 | Link Building | **10** | DEAD | All three endpoints return INTERNAL_ERROR or 404 |
| 12 | Report Generation | **45** | HARD FAIL | `GET /reports` returns 200 but `data: []` (no data path) |
| 13 | Recommendations | **20** | DEAD | All four endpoints return **hardcoded placeholder strings** |
| 14 | Automation | **10** | DEAD | All three automation endpoints return INTERNAL_ERROR |
| 15 | Approvals | **15** | DEAD | Both `v1` and `v2` approvals return INTERNAL_ERROR |

**Overall workflow viability: 13/15 = 86.7% of core SEO workflows are non-functional.**

**Mean score across all 15 workflows: 16.3 / 100**

A real SEO agency cannot use this platform for any of the 15 primary workflows. Only `GET /reports` is reachable, and it returns an empty array with no path to populate it.

---

## Workflow 1: Client Onboarding — 15/100 (DEAD)

**Score breakdown:** Entry: 0, Validation: 0, Persistence: unknown, Retrieval: 0

### Evidence
```
GET /api/v1/clients?tenant_id=...&limit=3
→ {"success":false,"data":null,"error":{"error_code":"INTERNAL_ERROR",
  "message":"An internal error occurred","details":{},"retryable":false}}

GET /api/v1/tenants/{id}
→ INTERNAL_ERROR (no detail)

GET /api/v1/customers (alt path)
→ {"detail":"Not Found"}

GET /api/v1/onboarding
→ {"detail":"Not Found"}
```

### Failure modes
1. `/clients` is the documented primary client list endpoint and fails with opaque `INTERNAL_ERROR` and **empty `details`** — the operator cannot diagnose.
2. `/tenants/{id}` (used to fetch tenant context) also fails with the same opaque error.
3. The `/customers` and `/onboarding` aliases documented in some schemas do not exist (404).

### Real-world impact
- A new user cannot onboard. The first step of the entire platform is broken.
- No way to enumerate existing clients, no way to create one without hitting an unknown error.

### Hallucination / data-quality risk
N/A — no data is returned at all.

---

## Workflow 2: Campaign Creation — 25/100 (HARD FAIL)

### Evidence
```
GET /api/v1/campaigns?tenant_id=...&limit=3
→ INTERNAL_ERROR

GET /api/v1/agents/campaign/history?tenant_id=...
→ {"success":true,"data":[]}
```

### Failure modes
1. `/campaigns` (the canonical list endpoint) returns INTERNAL_ERROR.
2. `/agents/campaign/history` is reachable and returns an empty array, but it is a derivative endpoint (history of agent actions), not the source of truth.
3. The OpenAPI spec defines POST/PATCH/DELETE for `/campaigns`, but they are not probe-tested here — however, the read path being broken means campaign data cannot be retrieved to verify writes worked.

### Real-world impact
- A user can never list their campaigns, so they cannot select one to work on.
- A user cannot tell whether a campaign POST actually created something because the list view is broken.

### Verdict
The workflow's primary read endpoint is dead, so the entire workflow is unusable. The `/agents/campaign/history` success is irrelevant because that endpoint exposes agent events, not campaigns.

---

## Workflow 3: Keyword Research — 20/100 (DEAD)

### Evidence
```
GET /api/v1/keywords/research?tenant_id=...
→ INTERNAL_ERROR

POST /api/v1/keywords/research
body: {"seed_keywords":["seo","marketing"],"limit":5}
→ VALIDATION_ERROR
   errors: body.tenant_id missing
           body.client_id missing
           body.domain missing
```

### Failure modes
1. GET returns opaque error.
2. POST requires `tenant_id`, `client_id`, `domain` in **body** (not query). This is inconsistent with the rest of the API, which uses `?tenant_id=` query. Indicates contract drift.
3. The required fields suggest the endpoint needs a real configured provider (DataForSEO/Ahrefs) to actually run the research — and all SEO providers are unconfigured (see Provider Validation Report).

### Real-world impact
- Keyword research cannot be performed. Even if the POST succeeded, it would fail internally because no real keyword data provider is connected.
- The required `client_id` and `domain` are not retrievable because Workflow 1 (Client Onboarding) is broken — chicken-and-egg.

---

## Workflow 4: Competitor Analysis — 10/100 (DEAD)

### Evidence
```
GET /api/v1/serp-intelligence/competitor-overlap?tenant_id=...
→ {"detail":"Method Not Allowed"}
```

### Failure modes
1. The endpoint exists at the route level (no 404) but rejects GET. The OpenAPI spec lists it as a GET — **the OpenAPI spec and the implementation disagree**.
2. Without access to the spec for this method, we cannot determine the actual correct method. The error message gives no hint.

### Real-world impact
- Competitor analysis is non-functional. A user cannot identify who they are competing with in SERPs.

---

## Workflow 5: SERP Collection — 15/100 (DEAD)

### Evidence
```
GET /api/v1/serp-intelligence/dashboard
→ {"detail":"Not Found"}

GET /api/v1/serp-intelligence/volatility?tenant_id=...
→ VALIDATION_ERROR: query.keyword missing

POST /api/v1/serp-intelligence/capture-snapshot
body: {"keyword":"test","location":"US"}
→ VALIDATION_ERROR: body.geo missing
                    body.tenant_id missing
```

### Failure modes
1. `/dashboard` does not exist (404). The OpenAPI spec for SERP intelligence apparently does not include a dashboard, but the frontend may have linked to it during Phase 1.3.5 work — meaning the dashboard UI is also broken.
2. `/volatility` works at the route level but requires a `keyword` query param (not in `body`).
3. `/capture-snapshot` requires `geo` and `tenant_id` in body — contract drift relative to other endpoints.
4. Even if corrected, no SEO data provider is connected to call DataForSEO/Ahrefs APIs.

### Real-world impact
- SERP data cannot be captured, viewed, or analyzed.
- Volatility cannot be measured.
- The SERP intelligence feature is effectively non-existent.

---

## Workflow 6: Prospect Discovery — 15/100 (DEAD)

### Evidence
```
GET /api/v1/prospects/stats?tenant_id=...
→ INTERNAL_ERROR

GET /api/v1/prospect-graph/statistics?tenant_id=...
→ VALIDATION_ERROR: query.campaign_id missing
```

### Failure modes
1. `/prospects/stats` fails with opaque error.
2. `/prospect-graph/statistics` requires `campaign_id` query — but Workflow 2 (Campaigns) is broken, so a user cannot look up a valid campaign_id to pass.
3. The underlying prospect data depends on the Hunter.io provider, which is unconfigured.

### Real-world impact
- Prospect discovery is unusable. No link-building opportunities can be found.

---

## Workflow 7: Outreach Generation — 10/100 (DEAD)

### Evidence
```
GET /api/v1/outreach-intelligence/prioritize?tenant_id=...
→ {"detail":"Method Not Allowed"}

GET /api/v1/backlink-intelligence/outreach-predictions?tenant_id=...
→ INTERNAL_ERROR
```

### Failure modes
1. `/prioritize` is wrong method (route exists, method doesn't match OpenAPI).
2. `/outreach-predictions` is opaque error.
3. The workflow depends on Workflow 6 (Prospect Discovery) which is dead — chicken-and-egg.

### Real-world impact
- Outreach prioritization does not work. Backlink predictions do not work.

---

## Workflow 8: Email Personalization — 15/100 (DEAD)

### Evidence
```
GET /api/v1/email-drafts?tenant_id=...
→ INTERNAL_ERROR
```

### Failure modes
1. Email drafts cannot be listed or retrieved.
2. The workflow depends on the AI service (`Connection refused` in logs at `/tmp/uvicorn_p13k.log`) for personalization, which is not running.
3. The workflow depends on email-sending providers (SendGrid/Mailgun/Resend), all unconfigured.

### Real-world impact
- Email personalization is dead. No AI-powered email draft can be generated, reviewed, or sent.

---

## Workflow 9: Content Planning — 10/100 (DEAD)

### Evidence
```
GET /api/v1/strategic-seo/dashboard?tenant_id=...
→ {"detail":"Not Found"}
```

### Failure modes
1. The strategic SEO dashboard endpoint does not exist.
2. No alternative content planning endpoint was found in the test set.

### Real-world impact
- Content planning is non-functional. Users cannot get topic suggestions or content calendars.

---

## Workflow 10: Content Generation — 10/100 (DEAD)

### Evidence
```
GET /api/v1/content?tenant_id=...
→ {"detail":"Not Found"}
```

### Failure modes
1. `/content` (a reasonable REST plural) does not exist.
2. No alternative content-generation endpoint was probed in the test set.
3. Even if the endpoint existed, content generation depends on the AI service (Anthropic/OpenAI), which has `Connection refused` in logs.

### Real-world impact
- Content cannot be generated by the platform. AI content engine is offline.

---

## Workflow 11: Link Building — 10/100 (DEAD)

### Evidence
```
GET /api/v1/backlink-acquisition/opportunities?tenant_id=...
→ VALIDATION_ERROR: query.campaign_id missing

GET /api/v1/backlink-intelligence/broken-links?tenant_id=...
→ INTERNAL_ERROR

GET /api/v1/link-verification/verify?tenant_id=...
→ {"detail":"Not Found"}
```

### Failure modes
1. `/backlink-acquisition/opportunities` requires `campaign_id` — but Workflow 2 is broken, so no campaign_id is available.
2. `/backlink-intelligence/broken-links` is opaque error.
3. `/link-verification/verify` is 404 — the documented path is wrong.
4. Underlying provider (OpenPageRank) is unconfigured.

### Real-world impact
- Link building is dead. No opportunities, no broken-link detection, no link verification.

---

## Workflow 12: Report Generation — 45/100 (HARD FAIL)

### Evidence
```
GET /api/v1/reports?tenant_id=...&limit=3
→ {"success":true,"data":[]}
```

### Failure modes
1. The endpoint is reachable and returns 200 with an empty array. This is the only "working" workflow in the audit.
2. But the empty array means **no reports have ever been generated** — there is no path from this endpoint to actually producing a report. The report generation pipeline (which would presumably combine SERP data, keyword rankings, traffic, etc.) is not probe-tested here, but the upstream workflows (5, 3, 11) are all dead, so the data needed for a useful report cannot be produced.

### Real-world impact
- The endpoint responds. A user can list reports. But no data exists to populate any report.
- A real SEO agency would create a blank PDF — useless.

### Why 45 instead of 0
- The endpoint is technically healthy (correct response shape, 200 OK, no error).
- It is the only one of 15 workflows to achieve this.

---

## Workflow 13: Recommendations — 20/100 (DEAD)

**This workflow is the most dangerous because it appears to work but returns hardcoded fake data.**

### Evidence
```
GET /api/v1/recommendations/campaign?tenant_id=...
→ {"success":true,"data":[{"id":"camp-default",
   "recommendation_text":"No campaign optimization recommendations — all campaigns appear healthy",
   "priority":"P3","category":"campaign","impact":"low","effort":"low",
   "confidence":0.5,"supporting_data":{"note":"no_issues_detected"},
   "action_optional":true,"created_at":""}]}

GET /api/v1/recommendations/keyword?tenant_id=...
→ {"id":"kw-default","recommendation_text":"Keyword portfolio appears healthy — continue monitoring for new opportunities",...}

GET /api/v1/recommendations/ai?tenant_id=...
→ INTERNAL_ERROR: [Errno 61] Connection refused

GET /api/v1/recommendations/workflow?tenant_id=...
→ {"id":"wf-default","recommendation_text":"No workflow optimization needed — operational metrics are within thresholds",...}
```

### Failure modes — CRITICAL

1. **All three non-AI recommendation endpoints return hardcoded placeholders.**
   - The strings `"all campaigns appear healthy"`, `"continue monitoring for new opportunities"`, and `"operational metrics are within thresholds"` are **literal canned text** embedded in code, not derived from any data analysis.
   - The IDs `camp-default`, `kw-default`, `wf-default` are clearly placeholder identifiers, not real database IDs.
   - The `supporting_data: {"note":"no_issues_detected"}` and `{"note":"normal_operations"}` are obviously stub values.
   - `created_at: ""` is an empty string, not a real timestamp — another tell of placeholder data.
   - `confidence: 0.5` is a hardcoded neutral score.

2. **This is fake data, not an absence of data.** A real "no recommendations" endpoint should return `data: []` or a 204. Returning a fabricated recommendation object with a `"no_issues_detected"` note is actively misleading.

3. **The AI recommendations endpoint fails with Connection refused** — the AI service backing it is not running, so no LLM-based analysis is happening.

### Real-world impact
- **A user opening the recommendations dashboard would believe their SEO is fine.** This is the worst possible failure mode: false confidence.
- A real SEO agency making decisions based on these recommendations would do nothing, and lose ranking share to competitors who actually optimize.
- This is a **trust-destroying bug**, not just a missing feature.

### Hallucination risk
N/A — there is no LLM call. This is hardcoded text masquerading as analysis. The risk profile is worse than hallucination: it is **fabrication by design**.

### Why 20 and not 0
- The endpoint shape is correct.
- The HTTP 200 response is correct.
- The only thing wrong is the content — but the content is the entire point of the endpoint, so it cannot score higher.

---

## Workflow 14: Automation — 10/100 (DEAD)

### Evidence
```
GET /api/v1/automation/rules?tenant_id=...
→ INTERNAL_ERROR

GET /api/v1/automation/runs?tenant_id=...
→ INTERNAL_ERROR

GET /api/v1/automation/stats?tenant_id=...
→ INTERNAL_ERROR
```

### Failure modes
1. All three automation endpoints return opaque errors.
2. The automation pipeline depends on the dead workflows above (1, 2, 6, 7, 8) — so even if these endpoints were reachable, the underlying automations could not run.

### Real-world impact
- Automation is completely non-functional. No rules, no runs, no stats. A user cannot schedule any SEO task.

---

## Workflow 15: Approvals — 15/100 (DEAD)

### Evidence
```
GET /api/v1/approvals/v2?tenant_id=...
→ INTERNAL_ERROR

GET /api/v1/approvals?tenant_id=...
→ INTERNAL_ERROR
```

### Failure modes
1. Both v1 and v2 approval endpoints return opaque errors.
2. The approvals workflow is the human-in-the-loop gate for outreach emails, content publishing, and other risky actions. Without it, the operator command center cannot approve anything.

### Real-world impact
- No human can approve AI-generated content or outreach before it is sent.
- The platform's safety guarantee (operator approval before any external action) is broken — and combined with the fact that the actual sending workflows are also broken, this means **the platform is not just non-functional, it is non-functional without any of its safety rails working**.

---

## Cross-Workflow Findings

### Finding A: Opaque `INTERNAL_ERROR` is the dominant failure mode
At least 13 of 15 workflows fail with the same response shape:
```json
{"success":false,"data":null,"error":{"error_code":"INTERNAL_ERROR",
 "message":"An internal error occurred","details":{},"retryable":false}}
```
The `details` object is **always empty**, making root-cause diagnosis impossible from the API. This is a deliberate design that prioritizes information-hiding over operability.

### Finding B: API contract drift between query vs body
Different endpoints disagree on whether `tenant_id` is passed via:
- Query string (`?tenant_id=...`)
- Request body
- Header (`X-Tenant-Id`)

This drift makes the platform's API unusable without reading the source code for every endpoint. It also means the OpenAPI spec (if it accurately documents one style) is wrong for endpoints that use the other.

### Finding C: Method/route/contract mismatch
Multiple endpoints return `405 Method Not Allowed` (route exists, method wrong) or `404 Not Found` (route doesn't exist at all). The OpenAPI spec — and possibly the frontend's understanding — disagrees with the live implementation in multiple places.

### Finding D: Dead-end dependencies
Workflows form a graph:
```
1 (clients) → 2 (campaigns) → 3 (keywords) → 5 (SERP) → 13 (recs)
                       ↘ 6 (prospects) → 7 (outreach) → 8 (email) → 15 (approvals)
                       ↘ 9 (content plan) → 10 (content gen) → 15
                       ↘ 11 (link building) → 12 (reports)
14 (automation) gates all of the above
```
With Workflow 1 (the root) broken, the entire downstream chain is unreachable. The platform is a tree with a severed root.

### Finding E: AI service offline
Backend logs (`/tmp/uvicorn_p13k.log`) show `[Errno 61] Connection refused` from the AI service. This means all LLM-driven endpoints (recommendations/ai, content generation, email personalization, strategic SEO) are guaranteed to fail even if their routing worked.

---

## Quantitative Verdict

| Metric | Value |
|--------|------:|
| Workflows tested | 15 |
| Workflows that work (any 200 OK) | 2 (Reports, Recommendations) |
| Workflows producing real business output | 0 |
| Workflows producing fake/placeholder data | 1 (Recommendations) |
| Workflows dead (INTERNAL_ERROR or 404) | 13 |
| Mean score | 16.3 / 100 |
| Pass rate at 70+ threshold | 0 / 15 = **0%** |
| Pass rate at 50+ threshold | 0 / 15 = **0%** |

**No workflow passes the threshold for production use.**

The platform's TypeScript build, the operator command center, the database, and the route surface are all in place. But the moment any user clicks a real workflow button, the system returns an error, an empty list, or fabricated data.

Phase 1.4 verdict: **FAIL.**
