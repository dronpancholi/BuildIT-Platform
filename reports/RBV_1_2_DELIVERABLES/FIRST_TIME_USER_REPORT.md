# FIRST_TIME_USER_REPORT.md

## Scenario
A brand‑new junior SEO analyst logs into the platform for the first time. No documentation or onboarding material has been provided.

## Walk‑through & Observed Friction
| Step | Expected Action | What the UI/UX actually shows | Confusion / Missing Guidance |
|------|-----------------|------------------------------|-------------------------------|
| **Login** | Enter credentials (or use dev bypass) | Login page accepts `dev:<user>:<tenant>` token; no UI hint that dev bypass is required. | New users unfamiliar with the token format will be blocked.
| **Dashboard** | Overview of campaigns, health, quick actions. | Dashboard shows a list of campaigns (if any) but no **"Create New Campaign"** button on the empty state. | Users don’t know how to start a campaign.
| **Create Campaign** | Fill simple form (name, type, target link count). | Form fields lack inline tooltips (e.g., what is *target_link_count*?). Validation errors are displayed as raw messages.
| **Run Prospect Discovery** | After creating a campaign, run a discovery job to populate `backlink_prospects`. | No obvious button/CTA on the campaign detail page. The only way is to call the API manually or invoke a background job via the CLI.
| **View Prospects** | See a table of discovered prospects, filter by relevance/authority. | When no prospects exist the table is empty with only column headers, no explanation of *why empty* or *how to generate*. 
| **Generate Outreach Drafts** | Click *Generate Drafts* → system creates outreach threads. | The button is missing because the workflow never runs (backend error). The UI shows a blank “Outreach Drafts” page with no message.
| **Approve Outreach** | Review each draft, click *Approve* to launch outreach. | No drafts exist; even if they did, the UI lacks a bulk‑approve option.
| **Review Links** | Navigate to *Acquired Links* to see verified backlinks. | Empty table with no context; users cannot tell whether the campaign is still processing.
| **Generate Report** | Click *Generate Report* to export metrics. | Report button is present but produces a generic JSON without a downloadable link; no guidance on interpreting the numbers.
| **Health Dashboard** | View component health scores. | Numbers are displayed raw (e.g., `postgresql: healthy`) without colour or severity cues, making it hard to spot issues.

## Recommendations – Onboarding Enhancements
1. **Welcome Tour** – after first login, display a modal walkthrough highlighting:
   - How to create a campaign (CTA button).
   - Where to run prospect discovery.
   - What the next steps are after a campaign is created.
2. **Inline Tooltips** on all form fields (target link count, min domain authority, etc.) with concise definitions.
3. **Contextual Empty‑State Panels** (see Phase 14C report) for each section:
   - Prospect List → *"No prospects yet. Click \"Run Discovery\" on the campaign page to start."*
   - Outreach Drafts → *"No drafts generated. After prospect qualification, click \"Generate Outreach Drafts\"."*
   - Acquired Links → *"No links acquired. Ensure the outreach workflow has been launched and monitor the \"Link Verification\" section."*
4. **Actionable Help Links** – each empty panel includes a link to the quick‑start guide (to be authored in Phase 14D).
5. **Default On‑Screen Quick‑Start Panel** on the dashboard with buttons:
   - `Create Campaign`
   - `Run Prospect Discovery`
   - `Generate Report`
6. **Error‑Friendly Login** – detect malformed dev token and show a hint: *"Use the format `dev:<user‑id>:<tenant‑id>` for local development."*
7. **Exportable Report** – after generating a report, automatically download a CSV/HTML file and display a success toast.
8. **Health Visualisation** – colour‑code health numbers (green/yellow/red) to give instant status at a glance.

## Expected Impact
- **Reduced time‑to‑first‑value** – a junior user can create a campaign and generate the first set of prospects within ~2 minutes.
- **Lower support tickets** – clear guidance eliminates confusion around missing drafts and empty tables.
- **Higher adoption likelihood** – users feel confident navigating the system without external documentation.

Implementing the above will satisfy the Phase 14 requirement that a junior SEO can operate the platform end‑to‑end without external help.
