# Frontend V2 Phase 1 - Architecture Document

## Overview

Frontend V2 Phase 1 establishes the foundational infrastructure for the BuildIT enterprise SEO operations platform. This phase delivers a complete design system, application shell, authentication/authorization framework, state management layer, API architecture, and error handling — all built on a dark-first, glass-panel enterprise aesthetic with a teal (#14b8a6) platform accent.

## Tech Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Framework | Next.js | 16.2.6 |
| Language | TypeScript | ^5 |
| React | React | 19.2.4 |
| Styling | Tailwind CSS | ^4 |
| State Management | Zustand | ^5.0.13 |
| Server State | TanStack React Query | ^5.100.10 |
| Forms | react-hook-form + @hookform/resolvers | ^7.76.1 / ^5.4.0 |
| Validation | Zod | ^4.4.3 |
| UI Primitives | Radix UI | various |
| Component Variants | class-variance-authority | ^0.7.1 |
| Command Palette | cmdk | ^1.1.1 |
| Toasts | Sonner | ^2.0.7 |
| Animation | Framer Motion | ^12.38.0 |
| Icons | Lucide React | ^1.14.0 |
| Package Manager | pnpm | - |

## Directory Structure

```
frontend/src/
├── app/
│   ├── layout.tsx              # Root layout (Inter font, Providers wrapper)
│   ├── providers.tsx           # Re-export from @/providers/providers
│   ├── globals.css             # Design tokens, glass-panel, scrollbar
│   ├── error.tsx               # Global error boundary page
│   ├── not-found.tsx           # 404 page
│   └── dashboard/
│       ├── layout.tsx          # V2 shell: Sidebar + TopNav + CommandPalette
│       ├── error.tsx           # Dashboard-scoped error boundary
│       └── [pages]/            # Feature pages (pre-existing)
├── components/
│   ├── ui/                     # Design system (21 components)
│   ├── layout/                 # App shell components
│   ├── command-palette/        # CMD+K palette
│   ├── rbac/                   # Authorization wrappers
│   └── error-boundary.tsx      # Reusable class error boundary
├── config/
│   ├── constants.ts            # Routes, API URL, pagination defaults
│   └── permissions.ts          # Permission matrix + hasPermission()
├── hooks/
│   ├── use-auth.ts             # Auth hook with auto-login
│   └── use-rbac.ts             # RBAC hook with role checks
├── lib/
│   ├── utils.ts                # cn, formatCurrency, formatNumber, etc.
│   └── errors.ts               # getErrorMessage, getErrorTitle
├── providers/
│   ├── providers.tsx           # Master provider composition
│   ├── query-provider.tsx      # QueryClientProvider wrapper
│   ├── auth-provider.tsx       # Auth context with loading state
│   ├── notification-provider.tsx # Sonner Toaster
│   └── keyboard-provider.tsx   # CMD+K global shortcut
├── services/
│   ├── api-client.ts           # Typed HTTP client with tenant injection
│   ├── query-client.ts         # QueryClient factory with retry logic
│   ├── hooks.ts                # Generic CRUD hooks (useApiList, etc.)
│   └── endpoints.ts            # Backend endpoint constants
├── stores/
│   ├── auth-store.ts           # User state, login, permissions
│   ├── tenant-store.ts         # Current tenant ID
│   ├── navigation-store.ts     # Sidebar collapse state
│   ├── command-palette-store.ts # Palette open/close
│   ├── notification-store.ts   # In-app notifications
│   └── preferences-store.ts    # Persisted user preferences
└── types/
    ├── api.ts                  # APIResponse, APIError, ResponseMeta, etc.
    ├── models.ts               # Client, Campaign, Keyword, Plan, etc.
    └── auth.ts                 # Role, CurrentUser, AuthState, Permission
```

## Design Principles

1. **Dark-first**: Forced dark theme via `globals.css` with `@apply bg-surface-dark`
2. **Glass panels**: `bg-surface-card/80 backdrop-blur-md border border-surface-border` pattern
3. **Platform accent**: Teal (#14b8a6) used for primary actions, active states, focus rings
4. **Surface hierarchy**: `darker (#0a0b0d)` → `card (#16181d)` → `border (#23262e)`
5. **Motion**: Framer Motion for sidebar collapse, active nav indicator, command palette
6. **Accessibility**: Radix primitives provide keyboard nav, ARIA attributes, focus management
7. **RBAC everywhere**: Nav items, actions, pages all gate on role permissions

## Data Flow

```
┌─────────────────────────────────────────────────────┐
│                    Providers                         │
│  QueryProvider → AuthProvider → NotificationProvider  │
│                     → KeyboardProvider                │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   App Shell                          │
│  Sidebar ← useNavigationStore + useRBAC             │
│  TopNav ← useCommandPaletteStore + useNotificationStore │
│  CommandPalette ← useCommandPaletteStore            │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              Page Components                         │
│  useApiList/Detail/Create/Update/Delete              │
│  → api.get/post/put/delete (api-client.ts)           │
│    → injects tenant_id from useTenantStore           │
│    → fetch(API_BASE_URL + endpoint + params)         │
│  → TanStack Query caching + retry                    │
│  → Sonner toast on success/error                     │
└─────────────────────────────────────────────────────┘
```

## State Management Architecture

### Zustand Stores (6 stores)

| Store | Purpose | Persistence |
|-------|---------|-------------|
| `auth-store` | User, auth status, login/logout, permission checks | No |
| `tenant-store` | Current tenant ID | No |
| `navigation-store` | Sidebar collapsed state | No |
| `command-palette-store` | Palette open/close | No |
| `notification-store` | In-app notification list + unread count | No |
| `preferences-store` | Theme, sidebar state | Yes (localStorage) |

### TanStack Query

- Stale time: 60 seconds
- GC time: 5 minutes
- No refetch on window focus
- Retry: max 2 retries, skips 401/403/404
- Mutations: no retry, toast feedback

## API Architecture

### Client (`api-client.ts`)

- Generic `request<T>()` function handles all HTTP methods
- Automatic `tenant_id` injection from `useTenantStore`
- Response unwrapping: returns `data.data` or `data`
- Error normalization: `ApiError` class with status, errorCode, message, retryable

### Generic Hooks (`hooks.ts`)

| Hook | Method | Description |
|------|--------|-------------|
| `useApiList<T>` | GET | Paginated list with params |
| `useApiDetail<T>` | GET | Single resource by ID |
| `useApiCreate<TData, TVariables>` | POST | Create with cache invalidation |
| `useApiUpdate<TData, TVariables>` | PUT | Update by ID with cache invalidation |
| `useApiDelete` | DELETE | Delete by ID with cache invalidation |

### Endpoints (`endpoints.ts`)

27 endpoint constants covering: clients, campaigns, keywords, plans, approvals, reports, goals, health, tenants, citations, executive, recommendations, SEO intelligence, backlink intelligence, automation, search, semantic, AI copilot, forecast, operations, actions, executions.

## Auth Architecture

### Flow

1. `AuthProvider` renders loading screen while `useAuth()` initializes
2. `useAuth()` calls `store.login()` on mount if not authenticated
3. `login()` currently sets a mock admin user (no backend auth yet)
4. `AuthContext` provides `{ isLoading, isAuthenticated }` to the tree

### User Model

```typescript
interface CurrentUser {
  id: string;
  tenant_id: string;
  email: string;
  name: string;
  role: Role; // 'super_admin' | 'admin' | 'manager' | 'operator' | 'viewer'
  avatar_url?: string;
}
```

## RBAC Architecture

### Role Hierarchy

```
super_admin (4) > admin (3) > manager (2) > operator (1) > viewer (0)
```

### Permission Matrix

- 27 permissions across resources: customers, campaigns, approvals, reports, planning, goal, system, memory, agent, execution, action, communications, executive
- Each permission maps to an array of allowed roles
- `hasPermission(role, permission)` checks if role is in allowed list

### Enforcement Points

1. **Sidebar**: `NAV_ITEMS` filtered by `can(permission)` — unauthorized items hidden
2. **ProtectedAction**: Wraps UI elements, renders fallback if unauthorized
3. **ProtectedPage**: Full-page access denied screen if unauthorized
4. **useRBAC() hook**: Provides `can()`, `isManager`, `isAdmin`, etc.

## File Tree (V2 Phase 1 Files)

```
src/
├── app/
│   ├── layout.tsx
│   ├── providers.tsx
│   ├── error.tsx
│   ├── not-found.tsx
│   └── dashboard/
│       ├── layout.tsx
│       └── error.tsx
├── components/
│   ├── ui/
│   │   ├── avatar.tsx
│   │   ├── badge.tsx
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── empty-state.tsx
│   │   ├── error-state.tsx
│   │   ├── input.tsx
│   │   ├── label.tsx
│   │   ├── loading-spinner.tsx
│   │   ├── metric-card.tsx
│   │   ├── scroll-area.tsx
│   │   ├── select.tsx
│   │   ├── separator.tsx
│   │   ├── skeleton.tsx
│   │   ├── switch.tsx
│   │   ├── tabs.tsx
│   │   ├── textarea.tsx
│   │   └── tooltip.tsx
│   ├── layout/
│   │   ├── breadcrumbs.tsx
│   │   ├── notification-center.tsx
│   │   ├── profile-menu.tsx
│   │   ├── sidebar.tsx
│   │   └── top-nav.tsx
│   ├── command-palette/
│   │   └── command-palette.tsx
│   ├── rbac/
│   │   ├── protected-action.tsx
│   │   └── protected-page.tsx
│   └── error-boundary.tsx
├── config/
│   ├── constants.ts
│   └── permissions.ts
├── hooks/
│   ├── use-auth.ts
│   └── use-rbac.ts
├── lib/
│   ├── errors.ts
│   └── utils.ts
├── providers/
│   ├── providers.tsx
│   ├── query-provider.tsx
│   ├── auth-provider.tsx
│   ├── notification-provider.tsx
│   └── keyboard-provider.tsx
├── services/
│   ├── api-client.ts
│   ├── query-client.ts
│   ├── hooks.ts
│   └── endpoints.ts
├── stores/
│   ├── auth-store.ts
│   ├── tenant-store.ts
│   ├── navigation-store.ts
│   ├── command-palette-store.ts
│   ├── notification-store.ts
│   └── preferences-store.ts
└── types/
    ├── api.ts
    ├── auth.ts
    └── models.ts
```
