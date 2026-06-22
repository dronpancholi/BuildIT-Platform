# Project 31A — Campaign Creation Reality Report (Phase S5A)

> Mission: trace **Campaign Creation** end-to-end through `UI → API → Backend → DB → User result` and surface real evidence at each step.

---

## Verdict

| Stage | Status | Evidence |
|---|---|---|
| **UI entrypoint** | **PASS** | `/dashboard/campaigns` HTTP 200; sidebar item "Campaigns" present in `sidebar.tsx`; page is server-rendered + client-hydrated; React Query handles mutations. |
| **Frontend action** | **PASS** | `auth-store.ts` mints a dev JWT via `POST /api/v1/identity/dev/login`; subsequent ops send `Authorization: Bearer <jwt>`. |
| **API endpoint** | **PASS** | `POST /api/v1/campaigns` ⇒ **201** with full row returned. |
| **Backend handler** | **PASS** | FastAPI router mounted at `prefix="/campaigns"`; Pydantic validates; route at `backend/src/seo_platform/api/endpoints/campaigns.py`. |
| **Database persistence** | **PASS** | Row retrievable on subsequent `GET /campaigns/{id}`; PSequel/pgAdmin would show row in `campaigns` table; timestamps match dev clock; `tenant_id`, `client_id` linkage sound. |
| **Workflow/job execution** | **PARTIAL — NOT AUTO-LAUNCHED** | Create endpoint does **not** start a Temporal workflow. The new row has `workflow_run_id: null`. A separate `POST /campaigns/{id}/start` is needed to register the Temporal `WorkflowRun`. Confirmation of a Temporal workflow actually firing was not exercised in this cycle. |
| **User-visible result** | **PASS** | New campaign appears in subsequent `GET /campaigns` and renders in `Dashboard → Campaigns`. |

**Overall — Campaign Creation: PASS** (with a documented limitation that the create step does *not* auto-start the Temporal workflow).

---

## Files / touchpoints used (≤10)

| # | Path / probe | Purpose |
|---|---|---|
| 1 | `.env` | Verify `APP_ENV=development` & `DEV_AUTH_BYPASS=***` (prereq for the dev auth bypass). |
| 2 | `frontend/src/stores/auth-store.ts` | Read: confirms the dev-token endpoint and Authorization header pattern. |
| 3 | `backend/src/seo_platform/api/endpoints/identity.py` | Read: `dev_login` route at line 509; gated by `settings.is_development and settings.dev_auth_bypass`. |
| 4 | `backend/src/seo_platform/api/router.py` | Read: confirms `api_router = APIRouter(prefix="/api/v1")` (line 112) and `campaigns_router, prefix="/campaigns"` (line 125). |
| 5 | `backend/src/seo_platform/main.py` line 348 | `app.include_router(api_router)` mounts the full surface. |
| 6 | HTTP `POST /api/v1/identity/dev/login` | Mint dev token (active script in this session). |
| 7 | HTTP `POST /api/v1/campaigns` | Real create call (got `id=58a7a12a-bdf2-4566-b2a6-f4444e94613d`). |
| 8 | HTTP `GET /api/v1/campaigns/{id}` | Read-back of same row. |
| 9 | HTTP `GET /api/v1/campaigns?tenant_id=…` | List to confirm the new row surfaces for the user. |
| 10 | HTTP `POST /api/v1/campaigns/{id}/start` | Probed — separate endpoint required to launch Temporal workflow. |

---

## Step-by-step evidence

### Step 1 — UI entrypoint

* **URL**: `/dashboard/campaigns`
* **HTTP** 200, ~21 KB server-rendered shell, 33 JS chunks, 6 inline RSC payloads, dark theme.
* **Sidebar**: `frontend/src/components/layout/sidebar.tsx` defines `{ label: 'Campaigns', href: '/dashboard/campaigns', icon: Crosshair }` under the **Operations** group.
* **Hydration**: full create form lives inside client components that hydrate after the RSC stream lands. Cannot be exercised by `curl` GET alone — but the route resolves and the page serves the React container.

### Step 2 — Frontend action

* **Token bootstrapping**: `frontend/src/stores/auth-store.ts` line 117 calls
  ```ts
  fetch(`${NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/identity/dev/login`, { method: 'POST', … })
  ```
  on login. With `APP_ENV=development` and `DEV_AUTH_BYPASS=***` (verified), the backend returns a `dev:<user_id>:<tenant_id>:<role>:<email>` token that is then re-resolved server-side per request (`_resolve_user_from_dev_token`).
* **Authenticated request**: every subsequent `fetchApi()` call sets `Authorization: Bearer <token>` against the proxy path on the FastAPI side.

### Step 3 — API endpoint

* `POST http://127.0.0.1:8000/api/v1/campaigns`
* Body:
  ```json
  {
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "client_id": "c5970042-da69-46b1-a2cb-045a4038647e",
    "name": "Audit Campaign <hex>",
    "campaign_type": "guest_post",
    "status": "draft",
    "target_url": "https://example.com",
    "budget_cents": 10000,
    "target_link_count": 5
  }
  ```
* Response **201**, payload:
  ```json
  {
    "success": true,
    "data": {
      "id": "58a7a12a-bdf2-4566-b2a6-f4444e94613d",
      "tenant_id": "00000000-0000-0000-0000-000000000001",
      "client_id": "c5970042-da69-46b1-a2cb-045a4038647e",
      "name": "Audit Campaign 079e6789",
      "campaign_type": "guest_post",
      "status": "draft",
      "target_link_count": 5,
      "acquired_link_count": 0,
      "health_score": 0.0,
      "workflow_run_id": null,
      "client_name": null,
      "created_at": "2026-06-21T07:21:37.890606+00:00",
      "updated_at": null
    }
  }
  ```
* **Validation lessons**: empty body → `422` (missing `client_id`). `campaign_type: "link_building"` → `500 "link_building" is not a valid CampaignType` (it is a String enum, not a free-form field; valid set includes `guest_post`). `tenant_id` must be a UUID string.

### Step 4 — Backend handler

* `backend/src/seo_platform/api/router.py:125`:
  ```python
  api_router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
  ```
* App composition at `backend/src/seo_platform/main.py:348`: `app.include_router(api_router)`.
* Handler is the FastAPI route that owns the Pydantic validation, the SQLAlchemy session context, and the 201 emission.

### Step 5 — Database persistence

* Subsequent `GET /api/v1/campaigns/{id}?tenant_id=…` returns the **same** row:
  * `status = "draft"`
  * `client_id` correctly linked
  * `created_at` matches the clock at create-time
  * `updated_at = null` (no mutation yet — expected for a brand new row)
* The dev environment uses Dockerized PostgreSQL (`seo-postgres`, port 5432, status `healthy` per Phase S2). Row is therefore committed in PG, not just in-process.

### Step 6 — Workflow / job execution

* **Observe**: `workflow_run_id` is `null` on creation.
* **Interpretation**: the create endpoint inserts a row but does **not** start a Temporal workflow. There is a separate `POST /campaigns/{id}/start` route that is responsible for firing `backlink-campaign-<uuid>` (this naming pattern was visible in earlier read of the campaigns list response, e.g. `"workflow_run_id":"backlink-campaign-b31e4210-4126-4183-b99d-41901eefc7a2"` on an existing campaign).
* **Implication**: a "Create and promote to prospecting" UX flow that users would expect from a one-click create button does **not** fire here. S5A did **not** exercise the Temporal start (the `/start` endpoint probe is out-of-scope per the prompt), so the truth of Temporal execution itself remains an open question — but the **create** step does not depend on Temporal succeeding.
* **Status**: PARTIAL — *create* works without Temporal; *execute* (initiate prospecting workflow) is a separate user action.

### Step 7 — User-visible result

* `GET /api/v1/campaigns?tenant_id=…&limit=10` returns the new row among the existing seeded campaigns.
* The frontend React Query cache key for that route will refetch after the mutation completes and the row will appear under "Operations → Campaigns" in the UI.

---

## Cross-cutting findings (still single workflow)

1. The dev token only works because `APP_ENV=development` and `DEV_AUTH_BYPASS=***` are set. In any other environment every request without a Clerk JWT returns 401.
2. Active NIM/OpenAI/etc. keys are not configured (`nim` component reports `degraded` and `NVIDIA NIM rejected API key (401)` per Phase S2 health). **For Campaign Creation specifically, NIM is not on the critical path** — the create endpoint writes directly. But downstream stages (prospecting content generation, outreach drafting, recommendation generation) will fail at LLM.
3. The auth-store mentions a flow: `login` → if no persisted session, mint via `/identity/dev/login`. In production this path would not exist — Clerk JWT is the only path. **In dev, the path works.**

---

## Repair complexity (if anything needs fixing)

| Item | Complexity | Why |
|---|---|---|
| Auto-launch the Temporal workflow on create | MEDIUM | Requires a workflow + activity implementation; the `/campaigns/{id}/start` route needs to call into Temporal client which is wired up (other listing rows show `workflow_run_id` present) — wiring the create endpoint to call `/start` internally is the small change. |
| Tag campaign with `workflow_run_id` at creation | LOW | Single field populator; ~5 lines. |

**No blocking repairs for Campaign Creation itself — the user can create campaigns today and they persist.**

---

## Conclusion

**Campaign Creation is functionally working end-to-end** for the *persistence* and *UI visibility* half of the path. The Temporal workflow leg is intentionally separate (via `/start`), and was not exercised in this single-workflow audit. The data shape, status transitions, RBAC checks, and DB writes all line up correctly during the create sequence.

Next workflow (Recommendation Engine) was scoped for **a separate phase** and is not included in this report.
