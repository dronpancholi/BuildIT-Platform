# Frontend V2 Phase 2 — UAT Guide

**For:** SEO Team
**Version:** Phase 2 (12 pages)
**Date:** May 30, 2026

---

## How to Use This Guide

Each section below walks through a complete user workflow. Follow each step exactly as written. Report any discrepancies to the development team.

---

## 1. How to Create a Client

**Page:** Command Center (`/dashboard`) or Client List (`/dashboard/clients`)

### Steps

1. Navigate to the **Command Center** (dashboard landing page)
2. Click the **"New Client"** button in the top-right header area
3. A dialog modal appears with the title "New Client"
4. Fill in the following fields:
   - **Client Name** (required) — e.g., "Acme Corp"
   - **Domain** (required) — e.g., "acme.com"
   - **Niche** (optional) — Select from dropdown (B2B SaaS, E-commerce, Healthcare, etc.)
   - **Business Type** (optional) — Select from dropdown (SaaS, E-commerce Store, Agency, etc.)
5. Click **"Create Client"** button
6. The dialog closes automatically on success
7. A toast notification appears: "Client created successfully"
8. The client appears in the Active Clients metric card and the Client List

### Expected Behavior
- Button is disabled while the request is loading (spinner shown)
- Button is disabled if required fields are empty
- Cancel button or clicking outside the dialog dismisses it
- After creation, the client list updates automatically

### What to Verify
- [ ] Client name and domain are required — form won't submit without them
- [ ] Niche dropdown has 14 options
- [ ] Business Type dropdown has 8 options
- [ ] Success toast appears
- [ ] Client appears in the list

---

## 2. How to Create a Campaign

**Page:** Command Center (`/dashboard`), Campaign List (`/dashboard/campaigns`), or Client Detail

### Steps

1. Navigate to **Command Center** or **Campaigns** page
2. Click **"New Campaign"** button
3. A dialog modal appears with the title "New Campaign"
4. Fill in:
   - **Campaign Name** (required) — e.g., "Q1 Guest Post Push"
   - **Client** (required) — Select from dropdown (lists existing clients)
   - **Campaign Type** (required) — Select: Guest Post, Broken Link, or Resource Page
5. Click **"Create Campaign"** button
6. Dialog closes, toast appears: "Campaign created successfully"
7. Campaign appears in the campaign list

### Expected Behavior
- Client dropdown is populated from existing clients
- All three fields are required
- Campaign type has 3 options: Guest Post, Broken Link, Resource Page

### What to Verify
- [ ] Client dropdown shows existing clients
- [ ] All fields required before submit
- [ ] Toast notification on success
- [ ] Campaign appears in list with correct status (active)

---

## 3. How to Research Keywords

**Page:** Keyword Research (`/dashboard/keywords`)

### Steps

1. Navigate to **Keywords** page from the sidebar
2. You see a "Research" card with input fields
3. Enter **Seed Keywords** in the text field (comma-separated) — e.g., "seo tools, rank tracker, backlink checker"
4. Optionally enter a **Domain** — e.g., "example.com"
5. Click **"Research Keywords"** button
6. A loading spinner appears while the API processes
7. Results appear in a table with columns: Keyword, Volume, Difficulty, CPC, Intent, Cluster
8. Three view tabs become available: **Results**, **Cluster View**, **Insights**

### Filtering and Sorting

- **Sort:** Click any column header (Keyword, Volume, Difficulty, CPC, Intent, Cluster) to sort ascending/descending
- **Difficulty Filter:** Use the All / Easy / Medium / Hard buttons above the table
- **Select:** Click checkboxes to select individual keywords or use the header checkbox for all

### Cluster View

1. Click **"Cluster View"** tab
2. Keywords are grouped by cluster name
3. Each cluster shows a badge with keyword count
4. Keywords within each cluster are displayed as chips

### Insights View

1. Click **"Insights"** tab
2. View summary cards: Total Keywords, Avg. Volume, Avg. Difficulty, Avg. CPC
3. View Difficulty Distribution bar chart (Easy/Medium/Hard)
4. View Search Intent Breakdown bar chart

### What to Verify
- [ ] Seed keywords input accepts comma-separated values
- [ ] Enter key triggers research
- [ ] Loading state appears during research
- [ ] Results table shows all columns
- [ ] Sort toggles between ascending/descending
- [ ] Difficulty filter works (All/Easy/Medium/Hard)
- [ ] Cluster view groups keywords correctly
- [ ] Insights show computed statistics
- [ ] Empty state shows when no results found

---

## 4. How to Generate a Plan

**Page:** Planning Studio (`/dashboard/plans`)

### Steps

1. Navigate to **Plans** page from the sidebar
2. Click **"Generate Plan"** button in the top-right
3. A dialog modal appears with the title "Generate Plan"
4. Fill in:
   - **Goal** (required) — Select from dropdown (lists existing goals from the API)
   - **Domain / Focus Area** (optional) — e.g., "Technical SEO", "Content", "Backlinks"
   - **Strategy** — Choose one of three options:
     - **Balanced** (default) — Steady growth, moderate risk
     - **Aggressive** — Rapid gains, higher resource commitment
     - **Conservative** — Low-risk, long-term sustainability
5. Click **"Generate Plan"** button
6. The plan appears in the plans list with status "pending_approval" or "draft"
7. Each plan row shows: Name, Status, Confidence %, Risk Score %, Steps count, Created date

### What to Verify
- [ ] Goal dropdown populated from API
- [ ] Strategy selector shows 3 options with descriptions
- [ ] Loading spinner during generation
- [ ] Plan appears in list after creation
- [ ] Confidence and Risk scores display correctly (color-coded: green/amber/red)
- [ ] Clicking plan name navigates to plan detail

---

## 5. How to Approve a Plan

**Page:** Plan Detail (`/dashboard/plans/[id]`) or Approval Center (`/dashboard/approvals`)

### From Plan Detail

1. Navigate to **Plans** page
2. Click on a plan name to open its detail page
3. The plan detail shows:
   - Plan name, status badge, domain, strategy
   - Risk Score and Confidence Score (top-right, color-coded)
   - Progress bar (completed steps / total steps)
   - **DAG Visualization** — Interactive flowchart showing plan steps as nodes
   - Side panel with: Plan Details, Forecast, Risk Assessment
4. If the plan status is "pending_approval" or "draft", an **Actions** card appears
5. Optionally enter a **Comment** in the textarea
6. Click **"Approve"** button (green) to approve the plan
7. Click **"Reject"** button (red) to reject the plan
8. Status updates immediately after action

### From Approval Center

1. Navigate to **Approvals** page from the sidebar
2. Filter tabs show: All, Pending (with count), Approved, Rejected
3. Each approval card shows:
   - Entity type, action, risk level badge (color-coded left border)
   - AI Risk Summary (if available)
   - Requested by, time ago, SLA countdown timer
4. Click **"Approve"** button — first click shows "Confirm?", second click executes
5. Click **"Reject"** button — same double-click confirmation
6. Click **"Escalate"** button to escalate the approval
7. A "NEW" badge appears briefly when a new approval arrives via SSE

### What to Verify
- [ ] DAG visualization renders with nodes and edges
- [ ] Nodes are color-coded by status (green=completed, amber=in-progress, red=failed, gray=pending)
- [ ] MiniMap and Controls are visible on the DAG
- [ ] Risk/Confidence scores are color-coded
- [ ] Progress bar animates on load
- [ ] Approve/Reject buttons work with double-click confirmation
- [ ] SLA countdown timer updates in real-time
- [ ] SSE pushes new approval alerts
- [ ] Escalate button works

---

## 6. How to Generate a Report

**Page:** Report List (`/dashboard/reports`) or Report Detail (`/dashboard/reports/[id]`)

### Generate

1. Navigate to **Reports** page from the sidebar
2. Click **"Generate Report"** button
3. A dialog modal appears with the title "Generate Report"
4. Fill in:
   - **Report Type** — Select: Monthly, Quarterly, or Custom
   - **Client** (required) — Select from dropdown
5. Click **"Generate Report"** button
6. Toast appears: "Report generation started"
7. Report appears in the list with status (completed/generating/failed)

### View Report

1. Click the **eye icon** (View) on any report row
2. A dialog opens showing report data as key-value pairs in a grid
3. Click **"Export PDF"** button (placeholder)
4. Click **"Close"** to dismiss

### Report Detail Page

1. Click on a report name or navigate to `/dashboard/reports/:id`
2. The detail page shows:
   - Report title, type badge, generated date
   - **Summary Cards:** Total Keywords, Total Backlinks, Traffic Change, ROI
   - **4 Charts:**
     - Keyword Growth Over Time (Line chart)
     - Campaign Performance (Bar chart)
     - Traffic Growth (Area chart)
     - Traffic Sources (Pie chart)
   - Raw Report Data section (JSON view)
3. Click **"PDF"** or **"CSV"** export buttons (placeholder)

### What to Verify
- [ ] Report type dropdown has 3 options
- [ ] Client dropdown populated
- [ ] Report appears in list after generation
- [ ] Status badge shows correct state
- [ ] Report detail shows 4 summary cards
- [ ] All 4 charts render with data
- [ ] Charts have tooltips on hover
- [ ] PDF/CSV buttons are present
- [ ] Raw data section shows JSON

---

## 7. How to Monitor Executions

**Page:** Execution Monitor (`/dashboard/automation`)

### Steps

1. Navigate to **Automation** page from the sidebar (labeled "Operations Monitor")
2. The page auto-refreshes every 10 seconds (indicated by pulsing green dot)
3. **Stats Row** shows 4 cards: Running, Completed, Failed, Total
4. **Filter Tabs:** Running, Completed, Failed, All — with counts
5. **Execution Table** shows columns: ID, Type, Status, Started, Duration, Actions
6. Click any row to open the **Detail Panel** (slides in from the right)

### Detail Panel

- Shows: Status, Type, Started, Duration, Completed time
- If failed: Error message in red box
- If logs exist: Execution log viewer (scrollable)
- Click the **X** button or click outside to close

### What to Verify
- [ ] Auto-refresh indicator is visible (pulsing green dot)
- [ ] Stats row shows correct counts
- [ ] Tab filters work (Running/Completed/Failed/All)
- [ ] Status badges are color-coded (blue=running, green=completed, red=failed, amber=pending)
- [ ] Clicking a row opens the detail panel
- [ ] Detail panel shows execution metadata
- [ ] Error messages display for failed executions
- [ ] Log viewer is scrollable
- [ ] Panel closes on X click or backdrop click
- [ ] Skeleton loaders appear during initial load

---

## General Checks (All Pages)

- [ ] Sidebar navigation works for all 12 pages
- [ ] Dark theme is consistent across all pages
- [ ] Loading spinners appear during data fetch
- [ ] Empty states show with appropriate messages
- [ ] Error states show with retry options
- [ ] Dialog modals open/close correctly
- [ ] Toast notifications appear for actions
- [ ] Responsive layout works on smaller screens
- [ ] Animations are smooth (stagger, hover, transitions)
- [ ] No console errors in browser developer tools
