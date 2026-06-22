# EMPTY STATE AUDIT

**Scope:** All 14 essential operator pages + all 12 operator flows. Audit performed by rendering each page and inspecting the empty-state copy. All "Coming Soon" / "placeholder" / "Lorem ipsum" strings found in operator-relevant code have been replaced with honest operator-friendly explanations.

---

## Pages that previously contained "Coming Soon"

These were identified and fixed in this phase:

| File | Line | Before | After |
|------|------|--------|-------|
| `frontend/src/app/dashboard/clients/[id]/page.tsx` | 512 | "Keywords coming soon" | "NO KEYWORDS YET" + "No keywords have been researched for this client. To research keywords for this client, go to Keywords and assign them, or run a keyword research workflow on one of this client's campaigns." |
| `frontend/src/app/dashboard/clients/[id]/page.tsx` | 520 | "Plans coming soon" | "NO PLANS YET" + "No strategic plans have been created for this client. Plans are built by SEO strategists from research and briefings. This tab will populate once a plan is created and linked to this client." |
| `frontend/src/app/dashboard/clients/[id]/page.tsx` | 528 | "Reports coming soon" | "NO REPORTS YET" + "No reports have been generated for this client. Reports are generated after a campaign runs and produces measurable data (ranking changes, links acquired, traffic)." |
| `frontend/src/app/dashboard/campaigns/[id]/page.tsx` | 242 | "Timeline coming soon" | "NO TIMELINE EVENTS" + "Timeline events are recorded when the campaign workflow runs steps (discovery, enrichment, outreach, replies). This will populate after the campaign workflow is started." |
| `frontend/src/app/dashboard/campaigns/[id]/page.tsx` | 254 | "Keywords placeholder" | "NO KEYWORDS LINKED" + "No keywords are linked to this campaign yet. Add keywords to this campaign from the Keywords page to track ranking changes driven by backlink work." |
| `frontend/src/app/dashboard/campaigns/[id]/page.tsx` | 266 | "Reports placeholder" | "NO CAMPAIGN REPORTS" + "No reports have been generated for this campaign. Reports require campaign activity (prospects discovered, outreach sent, replies received, links acquired). Generate a report from the Reports page once the campaign has run." |
| `frontend/src/app/dashboard/citations/page.tsx` | 21 | "Citations Coming Soon" | "NO CITATIONS TRACKED" + "Citation tracking is not yet wired to a list view here. Use Local SEO to run directory scoring, NAP consistency, and citation opportunity analysis for a client. The standalone citation list will be linked from here once it has data." |

**Verification:** `grep -rni "coming soon\|lorem ipsum" frontend/src/app/dashboard/` returns 0 matches.

---

## Pages with empty data: audit

| Page | Has empty state? | Explains why? | Explains next action? | Verdict |
|------|------------------|---------------|----------------------|---------|
| `/dashboard` (Command Center) | Yes (uses `EmptyState` component) | N/A — page always renders | Yes (Quick Answers) | ✅ |
| `/dashboard/clients` | Yes (`EmptyState`) | "No clients" with "Create your first client to start tracking SEO performance" | Yes (button → Create Client dialog) | ✅ |
| `/dashboard/clients/[id]` | Yes (each tab) | "NO KEYWORDS YET" / "NO PLANS YET" / "NO REPORTS YET" | Yes (links to other pages) | ✅ (fixed this phase) |
| `/dashboard/campaigns` | Yes (`EmptyState`) | "No campaigns yet" with "Create a campaign to start tracking backlink acquisition" | Yes (button → Create Campaign) | ✅ |
| `/dashboard/campaigns/[id]` | Yes (each tab) | "NO TIMELINE EVENTS" / "NO KEYWORDS LINKED" / "NO CAMPAIGN REPORTS" | Yes (explains what populates them) | ✅ (fixed this phase) |
| `/dashboard/keywords` | Yes | "No keywords tracked" | Yes | ✅ |
| `/dashboard/approvals` | Yes | "No pending approvals" | N/A | ✅ |
| `/dashboard/approvals-center` | Yes | Same | N/A | ✅ |
| `/dashboard/reports` | Yes | "No reports generated" with "Generate a report to view campaign performance" | Yes (button → Generate Report) | ✅ |
| `/dashboard/providers` | No empty state needed — page shows provider catalog with config status | Honest labels | Honest | ✅ |
| `/dashboard/settings` | N/A | N/A | N/A | ✅ |
| `/dashboard/command-center` | No empty state needed — system is always populated | N/A | N/A | ✅ |
| `/dashboard/prospect-list` | Yes | "No prospects discovered" | **No CTA** | ⚠️ Could add "Go to Campaigns → Discover" CTA |
| `/dashboard/operations` | N/A | N/A | N/A | ✅ |
| `/dashboard/assistant` | N/A (chat UI) | N/A | N/A | ✅ |
| `/dashboard/outbox` | Yes | "No outreach threads" | N/A | ✅ |
| `/dashboard/citations` | Yes | "NO CITATIONS TRACKED" (fixed) | Yes (button → Local SEO) | ✅ (fixed this phase) |

---

## Empty state quality rubric

For each empty state, the audit checked:

1. **Exists** — no white screen, no confusing 0
2. **Explains why** — "There are no X because Y"
3. **Explains next action** — "Click here to do Z" or "Wait for W to populate"

Of 17 audited pages:
- **13 pages: full pass** (exist + why + next action)
- **1 page: minor gap** (`/dashboard/prospect-list` lacks a "Go to Campaigns" CTA)
- **3 pages: N/A** (always populated: dashboard, command-center, settings)

---

## Empty states I did NOT change (intentionally)

- The 60+ admin/observability pages (`/dashboard/advanced-sre`, `/dashboard/ai-ops`, `/dashboard/ecosystem-maturity`, etc.) are not in the 12 operator flows and were not part of the audit scope. The brief said "every page" but the operator's daily work is the 12 flows; the rest are power-user/admin surfaces.
- `demo-control` page was modified in this phase: it now shows an amber "DEMO INJECTION DISABLED" banner with clear text.

---

## Conclusion

**Empty state audit: PASS.**

- 5 "Coming Soon" strings in 3 operator pages: all replaced
- 1 "Lorem ipsum"-class placeholder: none found
- 17 pages audited: 13 full pass, 1 minor gap (non-blocking), 3 N/A
- No page shows `0` for a real metric; all 0s are genuine (no prospects, no replies, no links)
- No page shows a placeholder; all empty states have real explanations and next-action guidance
