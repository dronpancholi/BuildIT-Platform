# BuildIT — Production Blockers

> Everything that prevents BuildIT from being usable by a real SEO agency
> on a real client. Ranked by impact. Verified by audit, 2026-06-04.

A production-ready BuildIT means: an SEO agency manager signs in, creates a
real client, runs a real campaign, and the platform helps them do their job
end-to-end. Right now, 5 of the 6 stages of that journey are blocked.

---

## The Operator's Real Journey (what should work)

```
1. Sign in
2. Create a real client (or import one)
3. Discover prospects for that client
4. Generate AI-personalized emails
5. Approve the emails
6. Send the emails
7. See replies, follow up
8. Track which prospects link back
9. Report results to the client
```

**Of these 9 steps, only 1, 2 (partially), 7 (read-only), 8 (read-only), 9 (partially) work.**

---

## BLOCKER #1 [P0] — Zero External Provider API Keys Configured

**The platform cannot talk to the outside world.**

| Provider | Purpose | Status | Impact |
|----------|---------|--------|--------|
| SendGrid / Postmark / Mailgun / Resend | Send outreach emails | 0 keys | Cannot send any real email |
| Hunter.io | Discover contact emails | 0 keys | Cannot discover new prospects |
| DataForSEO | SERP data, keyword research | 0 keys | Keywords page empty (well, seeded) |
| Ahrefs | Backlink data | 0 keys | Backlink intelligence empty |
| NVIDIA NIM | LLM inference | ✓ key valid | LLM works (with deterministic fallback) |

**Effect:** A campaign can be created, but it cannot actually do outreach. The
"discover → generate emails → send" pipeline is offline.

**The only way to add keys today:** Edit `.env` and restart the backend.

**Time to fix:**
- Add 4 provider keys: ~1 hour
- Add a Settings → Integrations tab to manage keys: ~2 hours

**Operational impact:** Without this, BuildIT is a dashboard over an empty
database. Cannot serve a paying customer.

---

## BLOCKER #2 [P0] — Cannot Edit a Client (PATCH /clients 405)

**Operators can create a client, see it, and delete it. They cannot edit it.**

When the agency manager types the client name wrong, or the client changes
domain, or the niche needs updating, the only option is delete + recreate.
This:
- Loses the client's history
- Re-triggers onboarding workflows
- Forces re-doing keyword research

**This is the #1 thing an SEO agency does all day — update client records.**

**Time to fix:** Add `PATCH /clients/{id}` in the backend (~45 min) + 1 test.

---

## BLOCKER #3 [P0] — Cannot Pause or Resume a Campaign

**The "Pause" button in the new Command Center calls a 404 endpoint.**

This is the most common operator action. An outreach campaign overshoots;
the operator needs to pause it. They click Pause. Nothing happens.

**Time to fix:** Add `POST /campaigns/{id}/pause` and `/resume` (~30 min + 2 tests).

---

## BLOCKER #4 [P0] — Default Tenant Has Zero Outreach Data

The default tenant (`00000000-...-0001` "Acme Corp Enterprise") has:
- 0 communication templates
- 0 email drafts
- 0 scheduled emails
- 0 pending approvals

When a new operator signs in, they see an empty platform. They cannot
evaluate the outreach workflows. They cannot demo it.

The data IS in the database — but in test tenants, not the default one.

**Time to fix:** Seed default tenant with a baseline of 5-10 demo templates,
3-5 in-flight threads, 2-3 pending approvals. ~1 hour.

---

## BLOCKER #5 [P0] — All 4 Operational Pages Have Dev-Name H1s

`WAR_ROOM`, `INFRA_COMMAND`, `PROVIDER_HEALTH`, `KILL_SWITCHES`.

These read like a developer console, not a production product. Any first-time
operator would assume the system is unfinished.

**Time to fix:** Change 4 strings. ~5 minutes.

---

## BLOCKER #6 [P0] — Provider Health Reports False "Healthy" Status

`GET /provider-health` returns `healthy: true` for all 6 providers even though
no provider has been called in 24 hours (because no API keys are configured).

Operators will assume the providers are working. They are not.

**Time to fix:** When `total_calls_24h == 0` AND no key is configured, return
`healthy: false` with `reason: "no API key"`. ~30 minutes.

---

## BLOCKER #7 [P0] — Cannot Activate a Kill Switch (403 Forbidden)

The 6 "ENGAGE" buttons on `/dashboard/killswitches` return 403 Forbidden for
an admin user. They require `super_admin` role.

This means the operator cannot pause outbound outreach in an emergency.
That's the entire purpose of a kill switch.

**Time to fix:** Grant `system:write` to admin role, OR create a
`kill_switch:write` permission and assign it to admin. ~15 minutes.

---

## BLOCKER #8 [P1] — Cannot Configure Provider Keys from UI

There is no API endpoint, no UI, and no documentation for adding provider
keys at runtime. The only way is to edit `.env` and restart the backend.

For a SaaS product, this is unacceptable. An admin must be able to plug
in their own SendGrid key without engineering support.

**Time to fix:**
- Backend: `PUT /api/v1/providers/{name}/key` with encrypted storage
- Frontend: Settings → Integrations tab
- Total: ~2 hours

---

## BLOCKER #9 [P1] — Settings Page Is a Placeholder

5 tabs (General, Security, Notifications, Integrations, Public Profile) render
with no data. "Save Changes" does nothing. The entire page is decorative.

**Time to fix:** Add a settings model + API + form. ~3 hours.

---

## BLOCKER #10 [P1] — Cannot Create a Plan from a Clean State

The "Generate Plan" modal renders, but to call `POST /plans/generate` you need
a `goal_execution_id`. The only way to get one is for a workflow to auto-create
a goal. There is no "Create Goal" UI for an operator.

A new client cannot get a plan. Period.

**Time to fix:** Auto-create a default goal for new clients during onboarding.
Or add a "Create Goal" form. ~1 hour.

---

## Summary

| # | Blocker | P-Index | Time to Fix |
|---|---------|---------|-------------|
| 1 | Zero provider keys | P0 | 1h (+ 2h for UI) |
| 2 | Cannot edit client | P0 | 45m |
| 3 | Cannot pause campaign | P0 | 30m |
| 4 | Empty default tenant | P0 | 1h |
| 5 | Dev-name h1s | P0 | 5m |
| 6 | False provider health | P0 | 30m |
| 7 | Kill switch 403 | P0 | 15m |
| 8 | No key management UI | P1 | 2h |
| 9 | Settings placeholder | P1 | 3h |
| 10 | No plan from clean state | P1 | 1h |

**P0 total: ~4 hours 5 minutes of engineering work.**
**P1 total: ~6 hours.**

**With ~10 hours of focused work, the platform goes from "demo over test data"
to "operational for a real paying customer on a real domain."**
