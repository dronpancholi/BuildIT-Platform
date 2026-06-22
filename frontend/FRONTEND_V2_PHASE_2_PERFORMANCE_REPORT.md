# Frontend V2 Phase 2 — Performance Report

**Generated:** May 30, 2026

---

## 1. Build Summary

| Metric | Value |
|--------|-------|
| Build Status | SUCCESS |
| Framework | Next.js 16.2.6 |
| React | 19.2.4 |
| TypeScript | 5.x (strict mode) |
| Build Output | `.next/` (4.3GB dev cache) |
| Package Manager | pnpm |

---

## 2. Route Count

| Category | Count |
|----------|-------|
| Phase 2 Page Routes | 12 |
| Dynamic `[id]` Routes | 4 |
| Static Routes | 8 |
| Layout Files | 1 |
| Error Boundaries | 1 |
| **Total Dashboard Routes** | **12 pages + 1 layout** |

---

## 3. Dependency Analysis

### 3.1 Phase 2 Dependencies

| Package | Size (est.) | Impact |
|---------|-------------|--------|
| `recharts` | ~200KB gzipped | Charts library — used on Report Detail only |
| `@xyflow/react` | ~150KB gzipped | DAG visualization — used on Plan Detail only |

### 3.2 Full Dependency Tree (Key Packages)

| Package | Version | Bundle Impact |
|---------|---------|---------------|
| `next` | 16.2.6 | Core framework |
| `react` / `react-dom` | 19.2.4 | Core UI |
| `@tanstack/react-query` | 5.100.10 | Data fetching/caching |
| `framer-motion` | 12.38.0 | Animations |
| `@xyflow/react` | 12.10.2 | DAG visualization |
| `recharts` | 3.8.1 | Charts |
| `zustand` | 5.0.13 | State management (available, unused) |
| `@tiptap/*` | 3.23.6 | Rich text editor (available) |
| `zod` | 4.4.3 | Schema validation |
| `react-hook-form` | 7.76.1 | Form handling |
| `sonner` | 2.0.7 | Toast notifications |
| `lucide-react` | 1.14.0 | Icons |
| `date-fns` | 4.1.0 | Date formatting |
| `cmdk` | 1.1.1 | Command palette |
| `class-variance-authority` | 0.7.1 | Component variants |
| `tailwind-merge` | 3.6.0 | Tailwind class merging |

---

## 4. Code Metrics

### 4.1 Page File Sizes

| Page | Lines | Est. Size (unminified) |
|------|-------|----------------------|
| Command Center | 634 | ~18KB |
| Client List | 345 | ~10KB |
| Client Detail | 619 | ~18KB |
| Campaign List | 257 | ~7KB |
| Campaign Detail | 263 | ~8KB |
| Keyword Research | 534 | ~15KB |
| Planning Studio | 394 | ~11KB |
| Plan Detail (DAG) | 740 | ~21KB |
| Approval Center | 505 | ~15KB |
| Report List | 253 | ~7KB |
| Report Detail | 242 | ~7KB |
| Execution Monitor | 305 | ~9KB |
| **Total** | **5,091** | **~146KB** |

### 4.2 Shared Component Count

| Category | Count |
|----------|-------|
| UI Components (components/ui) | 21 |
| Layout Components | 3 (Sidebar, TopNav, CommandPalette) |
| Service Hooks | 5 (useApiList, useApiDetail, useApiCreate, useApiUpdate, useApiDelete) |
| API Client | 1 |
| Utility Functions | 2+ (formatDate, formatNumber, cn) |

---

## 5. Route-Level Code Splitting

Next.js App Router automatically code-splits at the route level:

| Route | Chunk | Est. First Load |
|-------|-------|-----------------|
| `/dashboard` | Command Center chunk | ~45KB |
| `/dashboard/clients` | Client List chunk | ~35KB |
| `/dashboard/clients/[id]` | Client Detail chunk | ~40KB |
| `/dashboard/campaigns` | Campaign List chunk | ~30KB |
| `/dashboard/campaigns/[id]` | Campaign Detail chunk | ~30KB |
| `/dashboard/keywords` | Keywords chunk | ~38KB |
| `/dashboard/plans` | Plans chunk | ~35KB |
| `/dashboard/plans/[id]` | Plan Detail + React Flow | ~200KB |
| `/dashboard/approvals` | Approvals chunk | ~40KB |
| `/dashboard/reports` | Reports chunk | ~30KB |
| `/dashboard/reports/[id]` | Report Detail + Recharts | ~250KB |
| `/dashboard/automation` | Automation chunk | ~32KB |

**Note:** React Flow and Recharts are only loaded on their respective detail pages, keeping other routes lightweight.

---

## 6. Load Time Estimates

### 6.1 First Contentful Paint (FCP)

| Route | Estimated FCP | Notes |
|-------|---------------|-------|
| `/dashboard` | ~1.2s | 4 API calls, skeleton loaders |
| `/dashboard/clients` | ~0.8s | 1 API call, skeleton rows |
| `/dashboard/clients/[id]` | ~1.0s | 1 API call, lazy campaign load |
| `/dashboard/campaigns` | ~0.8s | 1 API call |
| `/dashboard/campaigns/[id]` | ~0.7s | 1 API call |
| `/dashboard/keywords` | ~0.5s | No initial API call (form only) |
| `/dashboard/plans` | ~0.9s | 2 API calls, 15s refetch |
| `/dashboard/plans/[id]` | ~1.5s | 1 API call + React Flow render |
| `/dashboard/approvals` | ~0.9s | 1 API call + SSE connect |
| `/dashboard/reports` | ~0.8s | 1 API call |
| `/dashboard/reports/[id]` | ~1.3s | 1 API call + 4 charts render |
| `/dashboard/automation` | ~0.8s | 1 API call, 10s auto-refresh |

### 6.2 Largest Contentful Paint (LCP)

| Route | Estimated LCP | Bottleneck |
|-------|---------------|------------|
| `/dashboard` | ~2.0s | 4 parallel API calls |
| `/dashboard/plans/[id]` | ~2.5s | React Flow initialization |
| `/dashboard/reports/[id]` | ~2.2s | 4 Recharts render |
| `/dashboard/approvals` | ~1.8s | SSE + approval cards |

---

## 7. Auto-Refresh Impact

| Page | Refresh Interval | API Calls/Hour |
|------|-----------------|----------------|
| Planning Studio | 15s | 240 |
| Plan Detail | 10s | 360 |
| Approval Center | 10s | 360 |
| Execution Monitor | 10s | 360 |

**Total background API calls/hour (if all 4 pages open):** ~1,320

### Mitigation
- React Query caches data between refetches
- SSE (Approval Center) reduces polling need for real-time updates
- Consider implementing `refetchOnWindowFocus: false` for less critical pages

---

## 8. Optimization Notes

### 8.1 Strengths

- **Route-level code splitting** — Heavy libraries (recharts, @xyflow/react) only load on specific pages
- **Skeleton loaders** — Perceived performance improved with immediate visual feedback
- **React Query caching** — Duplicate requests avoided, stale-while-revalidate pattern
- **Lazy data loading** — Client Detail only fetches campaigns when the Campaigns tab is active
- **CSS animations** — Hardware-accelerated (transform, opacity) instead of layout-triggering properties

### 8.2 Recommendations

| Priority | Recommendation | Impact |
|----------|---------------|--------|
| High | Lazy-load `recharts` with `next/dynamic` on Report Detail | Reduce bundle for non-report routes |
| High | Lazy-load `@xyflow/react` with `next/dynamic` on Plan Detail | Reduce bundle for non-plan routes |
| Medium | Implement `React.lazy` for dialog components | Reduce initial bundle |
| Medium | Add `loading="lazy"` to any future image components | Reduce initial load |
| Medium | Consider virtual scrolling for large keyword lists (>100 rows) | Improve table performance |
| Low | Add service worker for API response caching | Reduce server load |
| Low | Implement prefetching on sidebar hover | Improve navigation speed |

### 8.3 Known Performance Concerns

1. **Keyword Research** — Client-side sort/filter on large datasets could lag with 1000+ keywords
2. **Approval Center** — SSE connection + 10s polling is redundant; consider removing polling when SSE is connected
3. **Plan Detail DAG** — React Flow re-renders on every 10s refetch; consider debouncing
4. **Report Detail** — 4 charts render simultaneously; consider intersection observer for below-fold charts

---

## 9. Bundle Size Summary (Estimated)

| Chunk | Estimated Size (gzipped) |
|-------|-------------------------|
| Shared (React, Next.js, Query) | ~90KB |
| Dashboard Layout | ~15KB |
| Phase 2 Pages (combined) | ~180KB |
| recharts (lazy) | ~200KB |
| @xyflow/react (lazy) | ~150KB |
| **Total First Load** | **~105KB** (without lazy chunks) |
| **Total with all lazy chunks** | **~455KB** |

---

## 10. Quality Gates

| Gate | Status |
|------|--------|
| TypeScript strict mode | PASS (0 errors) |
| Next.js build | PASS |
| ESLint | PASS |
| All 12 pages compile | PASS |
| All pages render without crash | PASS |
