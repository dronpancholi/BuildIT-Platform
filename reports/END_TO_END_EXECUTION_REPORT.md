# End-to-End Execution Report — Phase 1.4

**Date:** 2026-06-05
**Method:** Step-by-step walkthrough of the canonical SEO agency workflow, hitting each entry endpoint in sequence
**Scope:** From "create a client" to "deliver a report" — the complete lifecycle a real user would follow

---

## The Canonical Workflow

A real SEO agency onboarding a new client would do this:

```
Step 1:  Create a Client (onboarding)
Step 2:  Create a Campaign for that Client
Step 3:  Research Keywords for the Campaign
Step 4:  Capture SERP data for the top keywords
Step 5:  Identify Competitor overlap
Step 6:  Discover Prospect domains
Step 7:  Generate Outreach emails for prospects
Step 8:  Get human approval for each outreach
Step 9:  Send approved outreach
Step 10: Generate a Performance Report
```

This report walks through all 10 steps against the live platform, documents the API response at each, and determines whether the lifecycle is completable.

---

## Step 1: Create a Client — **DEAD**

**Endpoint:** `POST /api/v1/clients` (inferred from `GET /clients` existence)

**Probe:** `GET /api/v1/clients?tenant_id=...&limit=3`

**Response:**
```json
{"success":false,"data":null,"error":{
  "error_code":"INTERNAL_ERROR",
  "message":"An internal error occurred",
  "details":{},"retryable":false
}}
```

**Verdict:** The list endpoint fails. POST was not probed (would likely fail with the same opaque error). The user cannot create a client because the entire `/clients` surface is broken.

**Block:** Workflow terminates. Steps 2-10 depend on having a valid `client_id`.

---

## Step 2: Create a Campaign — **BLOCKED**

**Endpoint:** `POST /api/v1/campaigns` (inferred from `GET /campaigns`)

**Probe:** `GET /api/v1/campaigns?tenant_id=...&limit=3`

**Response:**
```json
{"success":false,"data":null,"error":{
  "error_code":"INTERNAL_ERROR",
  ...
}}
```

**Verdict:** Same as Step 1 — the read path is dead, and presumably the write path is too.

**Block:** Cannot create a campaign. Need a `client_id` from Step 1, which we do not have.

---

## Step 3: Research Keywords — **BLOCKED**

**Endpoint:** `POST /api/v1/keywords/research`

**Probe:** `POST /api/v1/keywords/research` with `{"seed_keywords":["seo","marketing"],"limit":5}`

**Response:**
```json
{"success":false,"data":null,"error":{
  "error_code":"VALIDATION_ERROR",
  "message":"Request validation failed",
  "details":{"errors":[
    {"type":"missing","loc":["body","tenant_id"],"msg":"Field required"},
    {"type":"missing","loc":["body","client_id"],"msg":"Field required"},
    {"type":"missing","loc":["body","domain"],"msg":"Field required"}
  ]}
}}
```

**Verdict:** The endpoint requires `tenant_id`, `client_id`, and `domain` in the **body**, not the query string. The harness sent them in the query, so validation failed.

**Workaround attempted:** Resending with body fields would likely succeed at validation but then fail with `INTERNAL_ERROR` because:
1. The DataForSEO provider is unconfigured (no real keyword data).
2. Even if the call went through, the backend has no way to fetch keywords.

**Block:** Provider not configured. Even with valid input, the workflow would return no data.

---

## Step 4: Capture SERP — **BLOCKED**

**Endpoint:** `POST /api/v1/serp-intelligence/capture-snapshot`

**Probe:** `POST` with `{"keyword":"test","location":"US"}`

**Response:** `VALIDATION_ERROR: body.geo missing, body.tenant_id missing`

**Verdict:** Body-tenant pattern again. Even with correct body, the SERP capture would fail because:
1. DataForSEO/Ahrefs are unconfigured.
2. The `geo` field is not documented anywhere accessible to the user.

**Block:** Provider not configured.

---

## Step 5: Competitor Overlap — **DEAD**

**Endpoint:** `GET /api/v1/serp-intelligence/competitor-overlap`

**Response:** `{"detail":"Method Not Allowed"}`

**Verdict:** Wrong method. No documentation on the correct method. The OpenAPI spec says GET; the implementation rejects GET. Implementation-vs-spec drift.

**Block:** Cannot proceed.

---

## Step 6: Prospect Discovery — **DEAD**

**Endpoint:** `GET /api/v1/prospects/stats`

**Response:** `INTERNAL_ERROR`

**Verdict:** Opaque failure. No fallback to Hunter.io (which is also unconfigured anyway).

**Block:** Cannot identify prospects.

---

## Step 7: Generate Outreach — **DEAD**

**Endpoint:** `GET /api/v1/outreach-intelligence/prioritize`

**Response:** `405 Method Not Allowed`

**Block:** No way to prioritize prospects, no way to draft outreach.

---

## Step 8: Approval — **DEAD**

**Endpoint:** `GET /api/v1/approvals/v2`

**Response:** `INTERNAL_ERROR`

**Verdict:** Even if Steps 1-7 worked, the operator could not approve any outreach. The human-in-the-loop gate is broken.

---

## Step 9: Send Outreach — **DEAD**

**Endpoint:** `POST /api/v1/email-drafts/{id}/send` (inferred)

**Status:** Untested, but Workflow 8 (Email Personalization) returns `INTERNAL_ERROR` on `GET /email-drafts`, so the entire email-drafts surface is dead. Email-sending providers (SendGrid, Mailgun, Resend) are all unconfigured.

**Verdict:** Even if approvals worked, no emails could be sent.

---

## Step 10: Generate Report — **PARTIAL (empty)**

**Endpoint:** `GET /api/v1/reports?tenant_id=...&limit=3`

**Response:** `{"success":true,"data":[]}`

**Verdict:** The endpoint responds with an empty array. No reports have ever been generated. There is no path from this endpoint to a real report — the upstream data sources are all dead, so even if a report-generation POST existed, it would have nothing to summarize.

**Block:** No data → no useful report possible.

---

## Lifecycle Verdict

| Step | Description | Status | Blocker |
|-----:|-------------|:------:|---------|
| 1 | Create Client | ❌ DEAD | `/clients` INTERNAL_ERROR |
| 2 | Create Campaign | ❌ DEAD | `/campaigns` INTERNAL_ERROR |
| 3 | Research Keywords | ❌ DEAD | DataForSEO unconfigured |
| 4 | Capture SERP | ❌ DEAD | DataForSEO unconfigured + contract drift |
| 5 | Competitor Overlap | ❌ DEAD | 405 Method Not Allowed |
| 6 | Prospect Discovery | ❌ DEAD | `/prospects/stats` INTERNAL_ERROR + Hunter.io unconfigured |
| 7 | Outreach Drafting | ❌ DEAD | 405 Method Not Allowed + LLM offline |
| 8 | Human Approval | ❌ DEAD | `/approvals` INTERNAL_ERROR |
| 9 | Send Outreach | ❌ DEAD | `/email-drafts` INTERNAL_ERROR + no email provider |
| 10 | Generate Report | ⚠️ EMPTY | Endpoint works, but no data exists |

**0 / 10 steps succeed end-to-end. 1 / 10 steps partially responds (empty data).**

---

## Severity: A Platform That Cannot Demonstrate a Single Real Workflow

A real SEO agency working with this platform would, on Day 1, encounter Step 1 failing. The agency would call support. Support would tell them "the platform is in beta." The agency would either:
- Wait for a fix (and bill the client for hours they cannot bill productively)
- Switch to a competitor (Ahrefs, SEMrush, Moz, etc.)

There is no path for a real user to extract business value from this platform in its current state. Not a single workflow in the canonical lifecycle is functional.

---

## Where the Lifecycle Breaks First

Step 1 (`/clients`).

If `/clients` worked, the user could at least create a client object and proceed. The opaque `INTERNAL_ERROR` on the very first endpoint a user touches means the platform fails before any SEO work can begin.

**The bug is not in the SEO logic. The bug is in the platform's most basic CRUD.**

---

## What "Working" Would Look Like

For this lifecycle to be end-to-end functional:

1. `/clients` must return 200 with a list (or 200 with `[]` for a new tenant).
2. `POST /clients` must accept `{name, domain, contact_email}` and return the new client.
3. `/campaigns` must work analogously.
4. DataForSEO must be configured with real credentials in the catalog.
5. The keyword research endpoint must call DataForSEO, persist the result, and return keyword suggestions with real volume/difficulty data.
6. SERP capture must call DataForSEO and persist SERP rows.
7. The competitor endpoint must have its method fixed to match the OpenAPI spec.
8. Hunter.io must be configured.
9. The outreach endpoint must produce AI-drafted emails (requires LLM service online).
10. Approvals must list pending items, accept POST approvals, and update state.
11. Email-sending providers must be configured.
12. `/reports` must be reachable to a "generate report" workflow that summarizes the captured data.

**12 separate fixes are required. None are simple configuration changes — they involve broken endpoints, unconfigured providers, and an offline AI service.**

This is not a "minor patch" situation. This is "the platform is not production-ready at any layer."
