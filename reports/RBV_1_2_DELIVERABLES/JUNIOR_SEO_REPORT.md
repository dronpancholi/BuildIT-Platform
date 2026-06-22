# JUNIOR SEO REPORT

**Scenario:** A new SEO analyst joins the team with no prior exposure to the platform and no formal documentation.

## Tasks Attempted & Observed Friction
| Task | Expected Action | Observed Issue | Time spent (min) |
|------|----------------|----------------|------------------|
| Create a new campaign | Fill simple form, click *Create* | The *Create Campaign* wizard lacks tooltip explanations for fields like *target_link_count* or *min_domain_authority*. | 12 |
| Browse prospects | Click *Prospects* tab to view list | Prospects table is empty for the demo tenant (only 39 seeded rows hidden behind a filter). No guidance on how to run a discovery job. | 10 |
| Approve outreach | Open *Outreach* tab and click *Approve* | No outreach drafts exist; the UI shows a blank state with no hint that a workflow must be launched first. | 8 |
| Track link acquisition | Navigate to *Links* view | Only 2 acquired links are present; the column headings are cryptic (e.g., `provider_message_id`). No explanation of how verification works. | 9 |
| Generate report | Click *Generate Report* button | The report wizard asks for a *report template* that is undocumented. The generated JSON is hard to interpret without a viewer. | 11 |
| Understand recommendations | Open *Recommendations* panel | Recommendations are largely repetitive `campaign_stalled` alerts with no context; there is no inline help to explain the `effort_score` field.
| Review health | Visit *Health* dashboard | Health metrics are displayed as raw numbers without thresholds or color coding, making it hard to spot issues.

## Confusion Points & Training Needs
1. **Onboarding tutorial** – a step‑by‑step walkthrough that explains the end‑to‑end flow (create campaign → run discovery → qualification → outreach → approval → reporting).
2. **Inline help tooltips** for all form fields and table columns.
3. **Missing documentation** about required background jobs (e.g., `discovery` cron) to populate prospects.
4. **Visibility of pending outreach drafts** – a dedicated view showing “drafts awaiting approval”.
5. **Explanation of recommendation engine** – why certain alerts fire and how to act on them.

## UX Weaknesses
- Empty states are not explanatory (e.g., blank outreach tab).
- No searchable Help Center link within the app.
- The UI mixes technical terms (`effort_score`, `confidence`) without layman explanations.
- Navigation hierarchy is deep; a junior user must click through multiple menus to reach basic data.

## Recommendations for Junior Adoption
- Provide a **quick‑start guide** (PDF or in‑app modal) covering the full workflow.
- Add **contextual onboarding prompts** the first time a user accesses a feature.
- Create **sample data sets** (larger prospect pool, pre‑generated outreach drafts) for training.
- Implement a **“What should I do next?”** sidebar that suggests the next logical action based on campaign state.

**Conclusion:** With the current UI and limited documentation, a junior SEO would experience significant friction, likely spending >60 minutes just to complete a simple campaign setup. Targeted onboarding and UI refinements are required to make the platform approachable for newcomers.
