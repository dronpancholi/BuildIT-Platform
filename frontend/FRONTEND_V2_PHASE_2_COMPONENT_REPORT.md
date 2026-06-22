# Frontend V2 Phase 2 — Component Report

**Generated:** May 30, 2026

---

## Summary

| Metric | Count |
|--------|-------|
| Pages Created | 12 |
| Lines of Code (pages) | 5,091 |
| API Endpoints Used | 22 |
| Shared UI Components Used | 14 |
| Dependencies Added | 2 (recharts, @xyflow/react) |

---

## Page Inventory

| # | File Path | Page Name | Route | Lines | Description |
|---|-----------|-----------|-------|-------|-------------|
| 1 | `src/app/dashboard/page.tsx` | Command Center | `/dashboard` | 634 | Dashboard landing with metrics, quick actions, create dialogs, recent activity, alerts |
| 2 | `src/app/dashboard/clients/page.tsx` | Client List | `/dashboard/clients` | 345 | Client table with search, pagination, create dialog |
| 3 | `src/app/dashboard/clients/[id]/page.tsx` | Client Detail | `/dashboard/clients/:id` | 619 | 6-tab client view with edit/archive, campaign sub-list |
| 4 | `src/app/dashboard/campaigns/page.tsx` | Campaign List | `/dashboard/campaigns` | 257 | Campaign table with status filter tabs, search, create dialog |
| 5 | `src/app/dashboard/campaigns/[id]/page.tsx` | Campaign Detail | `/dashboard/campaigns/:id` | 263 | Campaign overview with tabs, pause/resume/archive actions |
| 6 | `src/app/dashboard/keywords/page.tsx` | Keyword Research | `/dashboard/keywords` | 534 | Research form, sortable results table, cluster view, insights |
| 7 | `src/app/dashboard/plans/page.tsx` | Planning Studio | `/dashboard/plans` | 394 | Plan list with generate dialog, strategy selector |
| 8 | `src/app/dashboard/plans/[id]/page.tsx` | Plan Detail | `/dashboard/plans/:id` | 740 | React Flow DAG visualization, approve/reject, risk/confidence scores |
| 9 | `src/app/dashboard/approvals/page.tsx` | Approval Center | `/dashboard/approvals` | 505 | Approval cards with risk badges, SLA countdown, SSE real-time |
| 10 | `src/app/dashboard/reports/page.tsx` | Report List | `/dashboard/reports` | 253 | Report table with generate dialog, view/export actions |
| 11 | `src/app/dashboard/reports/[id]/page.tsx` | Report Detail | `/dashboard/reports/:id` | 242 | Recharts visualizations (Line, Bar, Area, Pie), summary cards |
| 12 | `src/app/dashboard/automation/page.tsx` | Execution Monitor | `/dashboard/automation` | 305 | Auto-refresh execution table, stats row, detail panel |

---

## API Dependencies Per Page

### 1. Command Center
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/clients` | GET | Active clients count |
| `/campaigns` | GET | Active campaigns count |
| `/approvals` | GET | Pending approvals count |
| `/executions` | GET | Running executions count |
| `/clients` | POST | Create client dialog |
| `/campaigns` | POST | Create campaign dialog |

### 2. Client List
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/clients` | GET | List clients (with offset/limit/search) |
| `/clients` | POST | Create client |

### 3. Client Detail
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/clients/:id` | GET | Client profile |
| `/campaigns` | GET | Client's campaigns (filtered by client_id) |
| `/clients/:id` | PUT | Edit/Archive client |

### 4. Campaign List
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/campaigns` | GET | List campaigns (with status/search) |
| `/clients` | GET | Client name lookup |
| `/campaigns` | POST | Create campaign |

### 5. Campaign Detail
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/campaigns/:id` | GET | Campaign detail |
| `/campaigns/:id` | PUT | Pause/Resume/Archive |

### 6. Keyword Research
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/keywords/research` | POST | Trigger keyword research |
| `/keywords` | GET | Fetch keyword results |

### 7. Planning Studio
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/plans` | GET | List plans |
| `/goals` | GET | List goals for plan generation |
| `/plans/generate` | POST | Generate new plan |

### 8. Plan Detail
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/plans/:id` | GET | Plan detail with steps |
| `/plans/:id/approve` | POST | Approve/Reject plan |

### 9. Approval Center
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/approvals` | GET | List approvals |
| `/approvals/:id/decide` | POST | Approve/Reject |
| `/approvals/:id/escalate` | POST | Escalate approval |

### 10. Report List
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/reports` | GET | List reports |
| `/clients` | GET | Client name lookup |
| `/reports/generate` | POST | Generate report |

### 11. Report Detail
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/reports/:id` | GET | Report detail with data |

### 12. Execution Monitor
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/executions` | GET | List executions (10s auto-refresh) |

---

## Feature Matrix

| Page | Search | Filter | Sort | Create | Edit | Delete | Pagination | Real-time | Charts | DAG |
|------|--------|--------|------|--------|------|--------|------------|-----------|--------|-----|
| Command Center | — | — | — | ✅ | — | — | — | — | — | — |
| Client List | ✅ | — | — | ✅ | — | — | ✅ | — | — | — |
| Client Detail | — | — | — | — | ✅ | ✅ | — | — | — | — |
| Campaign List | ✅ | ✅ | — | ✅ | — | — | — | — | — | — |
| Campaign Detail | — | — | — | — | ✅ | — | — | — | — | — |
| Keyword Research | — | ✅ | ✅ | ✅ | — | — | — | — | — | — |
| Planning Studio | — | — | — | ✅ | — | — | — | ✅ | — | — |
| Plan Detail | — | — | — | — | ✅ | — | — | ✅ | — | ✅ |
| Approval Center | — | ✅ | — | — | ✅ | — | — | ✅ | — | — |
| Report List | — | — | — | ✅ | — | — | — | — | — | — |
| Report Detail | — | — | — | — | — | — | — | — | ✅ | — |
| Execution Monitor | — | ✅ | — | — | — | — | — | ✅ | — | — |

---

## UX State Coverage

| State | Component | Used By |
|-------|-----------|---------|
| Loading (Skeleton) | `animate-pulse` divs | Client List, Execution Monitor |
| Loading (Spinner) | `LoadingSpinner` | Client Detail, Campaign List/Detail, Reports |
| Loading (Inline) | `Loader2 animate-spin` | Dialogs, Plan pages, Approvals |
| Empty | `EmptyState` | Client List, Campaign List/Detail, Keywords, Reports, Approvals, Automation |
| Error | `ErrorState` | Client List, Client Detail, Reports |
| Error (Inline) | Red card | Campaign List, Approvals |
| Permission/RBAC | Button disabled states | All create/edit actions |
| Success | Toast (`sonner`) | All mutation hooks |

---

## Animation Inventory

| Animation | Library | Used By |
|-----------|---------|---------|
| Stagger children | `framer-motion` | Command Center, Client List, Plan List |
| Item fade-in | `framer-motion` | Client List rows, Approval cards, Plan rows |
| Tab transitions | `framer-motion` | Client Detail tabs |
| Progress bar | `framer-motion` | Plan Detail progress |
| Hover scale | CSS `transition` | Quick actions, table rows |
| Pulse | CSS `animate-pulse` | Skeleton loaders, running status badges |
| Ping | CSS `animate-ping` | Auto-refresh indicator |
| Slide-in | CSS | Execution Monitor detail panel |
