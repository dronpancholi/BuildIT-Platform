# Frontend V2 Phase 2 — Architecture Document

**Generated:** May 30, 2026
**Status:** Complete — All 12 pages built, TypeScript clean, Build passing

---

## 1. Phase Overview

Phase 2 completes the core SEO operations dashboard by building all remaining domain pages. Phase 1 established the design system, component library, API client, and layout shell. Phase 2 adds the full CRUD and visualization layer across Clients, Campaigns, Keywords, Plans, Approvals, Reports, and Automation.

### Dependencies Added in Phase 2

| Package | Version | Purpose |
|---------|---------|---------|
| `recharts` | 3.8.1 | Charts and data visualizations (Line, Bar, Area, Pie) |
| `@xyflow/react` | 12.10.2 | React Flow DAG visualization for plan step graphs |

---

## 2. Pages Built

| # | Route | Page | Lines |
|---|-------|------|-------|
| 1 | `/dashboard` | Command Center (landing) | 634 |
| 2 | `/dashboard/clients` | Client List | 345 |
| 3 | `/dashboard/clients/[id]` | Client Detail | 619 |
| 4 | `/dashboard/campaigns` | Campaign List | 257 |
| 5 | `/dashboard/campaigns/[id]` | Campaign Detail | 263 |
| 6 | `/dashboard/keywords` | Keyword Research Center | 534 |
| 7 | `/dashboard/plans` | Planning Studio | 394 |
| 8 | `/dashboard/plans/[id]` | Plan Detail (DAG) | 740 |
| 9 | `/dashboard/approvals` | Approval Center | 505 |
| 10 | `/dashboard/reports` | Report List | 253 |
| 11 | `/dashboard/reports/[id]` | Report Detail (Charts) | 242 |
| 12 | `/dashboard/automation` | Execution Monitor | 305 |

**Total Phase 2 page code:** 5,091 lines across 12 page files

---

## 3. Component Architecture

### 3.1 Layout Stack

```
src/app/dashboard/layout.tsx
  ├── Sidebar (src/components/layout/sidebar.tsx)
  ├── TopNav (src/components/layout/top-nav.tsx)
  └── CommandPalette (src/components/command-palette/command-palette.tsx)
```

All Phase 2 pages render inside the dashboard layout, inheriting the sidebar navigation and top bar.

### 3.2 Shared UI Components Used

| Component | Source | Used By |
|-----------|--------|---------|
| `Button` | `components/ui/button.tsx` | All pages |
| `Card`, `CardContent`, `CardHeader`, `CardTitle` | `components/ui/card.tsx` | Most pages |
| `Badge` | `components/ui/badge.tsx` | All list/detail pages |
| `Input` | `components/ui/input.tsx` | Forms, search |
| `Select` | `components/ui/select.tsx` | Create dialogs |
| `Dialog`, `DialogContent`, `DialogHeader`, etc. | `components/ui/dialog.tsx` | Create/edit dialogs |
| `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` | `components/ui/tabs.tsx` | Campaign Detail, Keywords |
| `Label` | `components/ui/label.tsx` | Form fields |
| `EmptyState` | `components/ui/empty-state.tsx` | Empty data states |
| `ErrorState` | `components/ui/error-state.tsx` | Error states |
| `LoadingSpinner` | `components/ui/loading-spinner.tsx` | Loading states |
| `MetricCard` | `components/ui/metric-card.tsx` | Command Center |
| `Skeleton` | `components/ui/skeleton.tsx` | Skeleton loaders |

### 3.3 Page-Specific Components

**Plan Detail (`/plans/[id]`):**
- `StepNode` — Custom React Flow node for plan step visualization
- Uses `ReactFlow`, `Controls`, `Background`, `MiniMap` from `@xyflow/react`

**Report Detail (`/reports/[id]`):**
- `ChartCard` — Wrapper for Recharts with consistent sizing
- `SummaryCard` — Metric summary display
- Uses `LineChart`, `BarChart`, `AreaChart`, `PieChart` from `recharts`

**Approval Center (`/approvals`):**
- `ApprovalCard` — Individual approval item with risk badge, SLA countdown, action buttons
- `useCountdown` — Custom hook for SLA deadline countdown
- `useTimeAgo` — Custom hook for relative timestamps

**Automation Monitor (`/automation`):**
- `DetailPanel` — Slide-out panel for execution details
- `StatusBadge` — Colored status indicator
- `SkeletonRow` — Table skeleton loader

---

## 4. Data Flow Per Page

### 4.1 Command Center (`/dashboard`)

```
API Calls:
  GET /clients         → useApiList → Active Clients count
  GET /campaigns       → useApiList → Active Campaigns count
  GET /approvals       → useApiList → Pending Approvals count
  GET /executions      → useApiList → Running Executions count
  POST /clients        → useApiCreate → Create Client dialog
  POST /campaigns      → useApiCreate → Create Campaign dialog

State: Local useState for dialog open/close, form values
Real-time: None (static recent activity/alerts data)
```

### 4.2 Client List (`/dashboard/clients`)

```
API Calls:
  GET /clients?offset=&limit=&search= → useApiList → Client table
  POST /clients → useApiCreate → Create Client

State: search, offset (pagination), showCreate, form
Pagination: Client-side (PAGE_SIZE = 20)
```

### 4.3 Client Detail (`/dashboard/clients/[id]`)

```
API Calls:
  GET /clients/:id → useApiDetail → Client profile
  GET /campaigns?client_id=:id → useApiList → Campaign sub-list (lazy)
  PUT /clients/:id → useApiUpdate → Edit/Archive

State: activeTab, showEdit, showArchive, editForm
Tabs: overview, campaigns, keywords, plans, reports, activity
```

### 4.4 Campaign List (`/dashboard/campaigns`)

```
API Calls:
  GET /campaigns?status=&search= → useApiList → Campaign table
  GET /clients → useApiList → Client name lookup
  POST /campaigns → useApiCreate → Create Campaign

State: statusFilter, searchQuery, showCreateDialog, createForm
```

### 4.5 Campaign Detail (`/dashboard/campaigns/[id]`)

```
API Calls:
  GET /campaigns/:id → useApiDetail → Campaign detail
  PUT /campaigns/:id → useApiUpdate → Pause/Resume/Archive

State: None beyond API data
Tabs: overview, timeline, keywords, reports
```

### 4.6 Keyword Research (`/dashboard/keywords`)

```
API Calls:
  POST /keywords/research → useApiCreate → Trigger research
  GET /keywords → useApiList → Results (lazy, after search)

State: seedKeywords, domain, activeTab, sortField, sortDir,
       difficultyFilter, selectedIds, hasSearched
Computed: filteredKeywords (sort+filter), clusters (grouped),
          insights (aggregated stats)
```

### 4.7 Planning Studio (`/dashboard/plans`)

```
API Calls:
  GET /plans?tenant_id=X → useQuery → Plans list (15s refetch)
  GET /goals?tenant_id=X → useQuery → Goal options
  POST /plans/generate?tenant_id=X → useMutation → Generate plan

State: showGenerate, goalId, domain, strategy
Uses: Direct @tanstack/react-query + fetchApi (not hooks wrapper)
```

### 4.8 Plan Detail (`/dashboard/plans/[id]`)

```
API Calls:
  GET /plans/:id?tenant_id=X → useQuery → Plan detail (10s refetch)
  POST /plans/:id/approve?tenant_id=X → useMutation → Approve
  POST /plans/:id/approve?tenant_id=X → useMutation → Reject

State: approvalComment
Computed: flowNodes, flowEdges (DAG layout from steps/dependencies)
Renders: ReactFlow with custom StepNode, risk/confidence scores,
         forecast, risk assessment panels
```

### 4.9 Approval Center (`/dashboard/approvals`)

```
API Calls:
  GET /approvals?tenant_id=X → useQuery → Approvals (10s refetch)
  POST /approvals/:id/decide?tenant_id=X → useMutation → Approve/Reject
  POST /approvals/:id/escalate?tenant_id=X → useMutation → Escalate

State: activeTab (filter), newApprovalAlert
SSE: useSSE(tenantId, "approvals") → Real-time approval updates
Hooks: useCountdown (SLA timer), useTimeAgo (relative time)
```

### 4.10 Report List (`/dashboard/reports`)

```
API Calls:
  GET /reports → useApiList → Reports table
  GET /clients → useApiList → Client name lookup
  POST /reports/generate → useApiCreate → Generate report

State: showGenerateDialog, generateForm, viewingReport
```

### 4.11 Report Detail (`/dashboard/reports/[id]`)

```
API Calls:
  GET /reports/:id → useApiDetail → Report data

State: None (render-only)
Charts: LineChart (keyword growth), BarChart (campaign perf),
        AreaChart (traffic growth), PieChart (traffic sources)
Data: Currently uses demo/hardcoded chart data
```

### 4.12 Execution Monitor (`/dashboard/automation`)

```
API Calls:
  GET /executions → useApiList → Executions (10s refetch)

State: activeTab (filter), selectedExecution (detail panel)
Computed: filtered executions by status
```

---

## 5. API Integrations

### 5.1 Endpoint Map

| Endpoint | Method | Used By |
|----------|--------|---------|
| `/clients` | GET | Command Center, Client List, Client Detail, Campaign List, Report List |
| `/clients` | POST | Command Center, Client List |
| `/clients/:id` | GET | Client Detail |
| `/clients/:id` | PUT | Client Detail (Edit/Archive) |
| `/campaigns` | GET | Command Center, Campaign List, Client Detail |
| `/campaigns` | POST | Command Center, Campaign List |
| `/campaigns/:id` | GET | Campaign Detail |
| `/campaigns/:id` | PUT | Campaign Detail (Pause/Resume/Archive) |
| `/keywords` | GET | Keyword Center |
| `/keywords/research` | POST | Keyword Center |
| `/plans` | GET | Planning Studio |
| `/plans/:id` | GET | Plan Detail |
| `/plans/generate` | POST | Planning Studio |
| `/plans/:id/approve` | POST | Plan Detail |
| `/goals` | GET | Planning Studio |
| `/approvals` | GET | Command Center, Approval Center |
| `/approvals/:id/decide` | POST | Approval Center |
| `/approvals/:id/escalate` | POST | Approval Center |
| `/reports` | GET | Report List |
| `/reports/:id` | GET | Report Detail |
| `/reports/generate` | POST | Report List |
| `/executions` | GET | Command Center, Automation Monitor |

### 5.2 API Client Patterns

Two patterns are used:

1. **`useApiList` / `useApiDetail` / `useApiCreate` / `useApiUpdate`** (from `src/services/hooks.ts`)
   - Wraps `@tanstack/react-query` with generic typing
   - Auto-invalidates query keys on mutation
   - Shows toast on success/error via `sonner`
   - Used by: Command Center, Clients, Campaigns, Keywords, Reports, Automation

2. **Direct `useQuery` / `useMutation`** (from `@tanstack/react-query`)
   - Uses `fetchApi` + `MOCK_TENANT_ID` directly
   - Used by: Plans, Plan Detail, Approvals
   - These pages were likely built with a slightly different pattern

### 5.3 SSE Integration

- **Approval Center** uses `useSSE` hook for real-time approval event streaming
- Listens for `approval_update` events to trigger toast alerts and query invalidation

---

## 6. State Management

| Pattern | Where Used |
|---------|------------|
| **React Query (server state)** | All pages — data fetching, caching, invalidation |
| **Local `useState`** | All pages — UI state (dialogs, forms, filters, tabs) |
| **`useMemo`** | Keywords (filtering/sorting/clustering), Plan Detail (DAG layout) |
| **SSE + `useEffect`** | Approval Center (real-time updates) |
| **Zustand** | Available in `package.json` but not used in Phase 2 pages |

No global client-side state store is used. All data is server-cached via React Query.

---

## 7. Route Structure

```
src/app/dashboard/
├── layout.tsx                    # Dashboard shell (sidebar + topnav)
├── error.tsx                     # Error boundary
├── page.tsx                      # /dashboard — Command Center
├── clients/
│   ├── page.tsx                  # /dashboard/clients — Client List
│   └── [id]/
│       └── page.tsx              # /dashboard/clients/:id — Client Detail
├── campaigns/
│   ├── page.tsx                  # /dashboard/campaigns — Campaign List
│   └── [id]/
│       └── page.tsx              # /dashboard/campaigns/:id — Campaign Detail
├── keywords/
│   └── page.tsx                  # /dashboard/keywords — Keyword Research
├── plans/
│   ├── page.tsx                  # /dashboard/plans — Planning Studio
│   └── [id]/
│       └── page.tsx              # /dashboard/plans/:id — Plan Detail (DAG)
├── approvals/
│   └── page.tsx                  # /dashboard/approvals — Approval Center
├── reports/
│   ├── page.tsx                  # /dashboard/reports — Report List
│   └── [id]/
│       └── page.tsx              # /dashboard/reports/:id — Report Detail
└── automation/
    └── page.tsx                  # /dashboard/automation — Execution Monitor
```

**Total routes:** 12 unique page routes (8 top-level + 4 dynamic `[id]` routes)

---

## 8. Design System Consistency

All Phase 2 pages follow the Phase 1 dark theme design system:

- **Color palette:** `slate-*` neutrals, `platform-*` primary, semantic colors (emerald/red/amber/blue)
- **Glass panels:** `glass-panel` utility class with `border-surface-border`
- **Typography:** `font-mono` for data, `font-sans` for headings, uppercase tracking for labels
- **Animations:** `framer-motion` stagger variants on lists, tab transitions, progress bars
- **Responsive:** Grid layouts with `sm:`, `lg:`, `xl:` breakpoints
- **Loading states:** Skeleton loaders (`animate-pulse`), `LoadingSpinner`, `Loader2` spinners
- **Empty states:** `EmptyState` component with icon + description + optional CTA
- **Error states:** `ErrorState` component with retry button
