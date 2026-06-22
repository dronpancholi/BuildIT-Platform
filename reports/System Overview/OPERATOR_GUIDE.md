# PROJECT 31A — PLATFORM OPERATOR & SRE GUIDE (DOCUMENT 12)
## Version 1.0.0
## Classification: CONFIDENTIAL — FOR INTERNAL DEVELOPMENT AND DUE DILIGENCE ONLY

---

## 1. THE OPERATOR WORKFLOW AXIOM

Project 31A operates as a semi-autonomous operations platform. The interface and workflows are structured around a central principle: **"AI proposes. Deterministic systems execute. Humans govern."**

Operators do not need to write copy, scrape sites, or configure complex routing trees. Instead, their role is to act as a **Governor**—inspecting, editing, and authorizing the actions proposed by the AI models before they are executed.

---

## 2. CLIENT ONBOARDING WALKTHROUGH

Before running any campaigns, a client site must be registered and analyzed.

```
Onboarding Tab ──► "Add Client" ──► Input Domain & Niche ──► Wait 2-3 mins ──► Verify Active
```

1. Navigate to the **Clients** tab in the sidebar.
2. Click **"Add Client"**.
3. Input the canonical root domain (e.g. `clientdomain.com`), display name, and target niche.
4. Input competitor domains if known, or leave blank to let the discovery model find them.
5. Click **"Launch Onboarding"**.
6. The dashboard displays the onboarding progress bar (DNS -> Enrichment -> Competitors).
7. Wait 2-3 minutes. Once onboarding finishes, the status shifts to `active`. Inspect the derived business profiles and keywords.

---

## 3. CREATING & LAUNCHING CAMPAIGNS

Campaigns are the containers for prospecting, scoring, and email outreach.

1. Navigate to the **Campaigns** tab in the sidebar.
2. Click **"Create Campaign"**.
3. Input a campaign name (e.g. `SaaS Skyscraper Q3`) and select the client target.
4. Select the campaign type (e.g. `skyscraper`, `niche_edit`, `guest_post`).
5. Set the **Target Link Count** (default `10`).
6. Configure the target metrics:
   - **Minimum Domain Authority (DA):** Default `30`.
   - **Maximum Spam Score:** Default `0.20`.
7. Click **"Launch Campaign"**.
8. The campaign status shifts to `prospecting`. The back-end launches the Temporal workflow `campaign-{campaign_id}` to start domain harvesting.

---

## 4. NAVIGATING THE APPROVALS WORKSPACE

The platform will pause execution at two critical approval gates to await operator authorization.

### 4.1 Gate 1: Prospect Verification
When prospecting completes, the campaign status transitions to `awaiting_approval`.
1. Open the **Approvals** center.
2. Select the pending `prospect_approval` item.
3. Review the discovered prospects table. You will see:
   - **Domain & URL:** The target site.
   - **Metrics:** Domain Rating (DR), relevance, and spam scores.
   - **Priority Score:** Combined AI score (0.0 to 1.0).
   - **Contact details:** Scraped email and verification status.
4. Check the boxes next to the domains you want to approve. Uncheck domains that are low quality or irrelevant.
5. Click **"Approve Selected Prospects"** to signal the workflow. The campaign transitions to `outreach_prep` to write the emails.

### 4.2 Gate 2: Outreach Content Review
When email generation completes, the campaign pauses at `awaiting_approval` for Gate 2.
1. Open the approvals queue and select the pending `outreach_approval` item.
2. Review the generated emails. You will see:
   - **Prospect:** Target contact email.
   - **Sequence:** Initial email + 2 follow-ups.
   - **Context:** The scraped facts utilized for personalization.
3. You can edit the text of any email inline if you want to adjust the wording.
4. If an email is poor quality, click **"Regenerate"** to request a new draft from the LLM.
5. Once satisfied, click **"Authorize Dispatch"**. The campaign transitions to `active` and begins email delivery.

---

## 5. MONITORING & MANUAL OUTREACH INTERVENTIONS

Once a campaign is active, you can monitor dispatches and manage replies in the **Communication Hub**.

- **Inbox Feed:** Displays all active threads, email status (delivered, opened), and inbound replies.
- **Reply Classifications:** Inbound replies are classified by the system:
  - `Interested`: Marks the thread in green. Requires operator follow-up.
  - `Unsubscribed` / `Rejected`: System stops follow-ups automatically.
- **Manual Intervention:** If a prospect replies with a question (e.g. asking for pricing or technical details), the operator can click **"Send Reply"** inside the thread to type a manual email. This action suspends follow-ups and hands control to the operator.

---

## 6. SRE RECOVERY & ESCALATION PROCEDURES

If infrastructure issues or API drops occur, campaigns may stall. Use these procedures to resolve stuck runs:

- **Check Temporal Worker Health:** Navigate to the **SRE Dashboard** to monitor active worker pools and task queue depths.
- **Verify API Key Quotas:** If Ahrefs or Hunter APIs return quota limits or auth errors, update the keys in the **Providers** tab.
- **Trigger Campaign Recovery:** If a campaign remains stuck in `prospecting` or `outreach_prep` for more than 2 hours:
  1. Open the **Recovery Console** `/dashboard/recovery`.
  2. Input the campaign ID.
  3. Click **"Force Replay Run"**.
  4. The system sends a reset signal to the Temporal workflow, forcing it to retry the active step.
- **Incident Response Escalation:**
  - **Level 1 (Operator):** Inspect logs, resolve approval blocks, retry activities.
  - **Level 2 (SRE):** Check Redis locks, check Temporal queue depths, restart worker containers.
  - **Level 3 (DBA/Dev):** Reset Alembic migrations, check database replication lags.
- **Verify Audit Logs:** Operators can review all actions in `/dashboard/audit` to track user mutations and system events.
- **Natural Language Assistant:** Use the AI assistant bar in the top menu to ask questions about system state: e.g. `"How many campaigns are currently active?"` or `"List all campaigns that failed due to Ahrefs quota limits."`
