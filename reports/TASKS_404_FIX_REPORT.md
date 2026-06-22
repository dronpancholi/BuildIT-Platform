# Project 31A — Tasks 404 Fix Report (Phase S4 / Task 1+2)

> Mission: implement the lowest-risk fix for the Tasks 404 and verify the route resolves.
> Implementation choice: server-side redirect to `/dashboard/action-center?tab=task` (reuses existing UI, no new business logic, no placeholder content).

---

## Fix applied

| | |
|---|---|
| Path created | `frontend/src/app/dashboard/tasks/page.tsx` |
| Lines of code added | 9 (excluding comments) |
| New business logic | none |
| New UI | none (server-side redirect only) |
| Redirect target | `/dashboard/action-center?tab=task` (existing **Action Center** page, **Tasks** tab) |

### File contents (final)

```tsx
import { redirect } from 'next/navigation';

// Tasks is consolidated under the existing Execution → Action Center surface.
// This page intentionally performs a server-side redirect (no UI) so the
// sidebar entry resolves without a 404 and lands the user on the Tasks tab
// of Action Center. No new business logic, no placeholder content.
export default function TasksRedirect(): never {
  redirect('/dashboard/action-center?tab=task');
}
```

> **Why a server-component `redirect()` and not a meta-refresh or `next.config.ts` rewrite?** App-Router-native, zero config drift, preserves the user-facing URL semantics, and reuses the existing Action Center component (which already handles `?tab=`).

---

## Verification (Task 2)

Endpoint verified: `GET http://127.0.0.1:3000/dashboard/tasks`

| Probe | Result |
|---|---|
| `curl -I /dashboard/tasks` | `HTTP/1.1 200 OK`, `X-Powered-By: Next.js`, `Content-Type: text/html` (no `Location` header — Next dev streams the redirect target in-band) |
| `curl /dashboard/tasks` (no follow) | `200`, body starts with `<!DOCTYPE html><html lang="en" class="dark">…` |
| `curl -L /dashboard/tasks` (follow) | `HTTP_FINAL=200`, `REDIRS=0`, `URL=http://127.0.0.1:3000/dashboard/tasks` — Next dev collapses the RSC redirect transparently |
| `curl /dashboard/action-center?tab=task` | `200` — redirect target is a live, valid route (Action Center Tasks tab) |

### Next.js dev log evidence

```
 GET /dashboard/tasks 200 in 891ms (next.js: 800ms, application-code: 91ms)
 GET /dashboard/tasks 200 in 17ms  (next.js: 1090µs, application-code: 16ms)
 GET /dashboard/action-center?tab=task 200 in 34ms (next.js: 13ms, application-code: 21ms)
```

Two known probes of `/dashboard/tasks` followed by one request to `/dashboard/action-center?tab=task` — the dev server is transparently following the server-side redirect into Action Center.

### 404 status — gone

* No `not-found` lookup observed.
* Response is `200` against the canonical tasks URL, end user lands on the Tasks tab of Action Center.

---

## Side effects / things explicitly NOT done

* No `placeholder.tsx` or "coming soon" UI.
* No new sidebar entries added or removed — `sidebar.tsx` was not touched.
* No backend route added — Tasks is an Action Center tab in the existing UI.
* No `middleware.ts` introduced.
* No `next.config.ts` change — no redirects/rewrites added (the redirect lives in the page component).
* Auth/RBAC: Action Center is reached through the same dashboard layout as before; no auth surface change.

---

## Files touched

| # | Path | Op |
|---|---|---|
| 1 | `frontend/src/app/dashboard/tasks/page.tsx` | **CREATE** |
| – | _implicit_ | folder `frontend/src/app/dashboard/tasks/` was created as the parent for the page above |

That's it for the fix. Other recommended reports (Sidebar Route Integrity) follow separately.
