# Frontend V2 Phase 1 - Component Inventory

## Design System Components (src/components/ui/)

| # | Component | File Path | Props Interface | Description | Dependencies |
|---|-----------|-----------|-----------------|-------------|--------------|
| 1 | Button | `src/components/ui/button.tsx` | `ButtonProps` extends `React.ButtonHTMLAttributes` + `VariantProps<typeof buttonVariants>` — `variant?: 'default' \| 'destructive' \| 'outline' \| 'secondary' \| 'ghost' \| 'link'`; `size?: 'default' \| 'sm' \| 'lg' \| 'icon'`; `asChild?: boolean` | Primary action button with 6 variants and 4 sizes. Supports Slot pattern via Radix. | `@radix-ui/react-slot`, `class-variance-authority`, `cn` |
| 2 | Input | `src/components/ui/input.tsx` | `InputProps` extends `React.InputHTMLAttributes<HTMLInputElement>` | Text input with dark theme styling, focus ring, file input support. | `cn` |
| 3 | Textarea | `src/components/ui/textarea.tsx` | `TextareaProps` extends `React.TextareaHTMLAttributes<HTMLTextAreaElement>` | Multi-line text input, min-height 80px, no resize. | `cn` |
| 4 | Select | `src/components/ui/select.tsx` | `SelectProps` extends `React.SelectHTMLAttributes` — `options: { label: string; value: string }[]`; `placeholder?: string` | Native select dropdown with dark theme styling. | `cn` |
| 5 | Card | `src/components/ui/card.tsx` | `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` — all extend `React.HTMLAttributes` | Glass-panel card container with header/footer sections. Uses `bg-surface-card/80 backdrop-blur-md`. | `cn` |
| 6 | Badge | `src/components/ui/badge.tsx` | `BadgeProps` extends `React.HTMLAttributes` + `VariantProps<typeof badgeVariants>` — `variant?: 'default' \| 'secondary' \| 'destructive' \| 'outline' \| 'success' \| 'warning'` | Status badge with 6 color variants. | `class-variance-authority`, `cn` |
| 7 | Skeleton | `src/components/ui/skeleton.tsx` | `React.HTMLAttributes<HTMLDivElement>` | Pulse-animated placeholder for loading states. | `cn` |
| 8 | Separator | `src/components/ui/separator.tsx` | `React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>` — `orientation?: 'horizontal' \| 'vertical'`; `decorative?: boolean` | Horizontal or vertical divider line. | `@radix-ui/react-separator`, `cn` |
| 9 | Tooltip | `src/components/ui/tooltip.tsx` | `Tooltip`, `TooltipTrigger`, `TooltipContent`, `TooltipProvider` — Radix primitives | Hover tooltip with portal, animation, dark theme. | `@radix-ui/react-tooltip`, `cn` |
| 10 | Dialog | `src/components/ui/dialog.tsx` | `Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, `DialogDescription`, `DialogClose`, `DialogPortal`, `DialogOverlay` — Radix primitives | Modal dialog with overlay, close button, animations. | `@radix-ui/react-dialog`, `lucide-react`, `cn` |
| 11 | DropdownMenu | `src/components/ui/dropdown-menu.tsx` | `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuCheckboxItem`, `DropdownMenuRadioItem`, `DropdownMenuLabel`, `DropdownMenuSeparator`, `DropdownMenuShortcut`, `DropdownMenuGroup`, `DropdownMenuPortal`, `DropdownMenuSub`, `DropdownMenuSubContent`, `DropdownMenuSubTrigger`, `DropdownMenuRadioGroup` — Radix primitives | Context menu with sub-menus, checkboxes, radio items. | `@radix-ui/react-dropdown-menu`, `lucide-react`, `cn` |
| 12 | ScrollArea | `src/components/ui/scroll-area.tsx` | `ScrollArea`, `ScrollBar` — Radix primitives | Custom scrollbar with vertical/horizontal orientation. | `@radix-ui/react-scroll-area`, `cn` |
| 13 | Tabs | `src/components/ui/tabs.tsx` | `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` — Radix primitives | Tabbed interface with active state styling. | `@radix-ui/react-tabs`, `cn` |
| 14 | Avatar | `src/components/ui/avatar.tsx` | `Avatar`, `AvatarImage`, `AvatarFallback` — Radix primitives | User avatar with image and fallback states. | `@radix-ui/react-avatar`, `cn` |
| 15 | Switch | `src/components/ui/switch.tsx` | `Switch` — Radix primitive | Toggle switch with checked/unchecked states. | `@radix-ui/react-switch`, `cn` |
| 16 | Label | `src/components/ui/label.tsx` | `Label` — Radix primitive + `VariantProps<typeof labelVariants>` | Form label with peer-disabled support. | `@radix-ui/react-label`, `class-variance-authority`, `cn` |
| 17 | LoadingSpinner | `src/components/ui/loading-spinner.tsx` | `LoadingSpinnerProps` extends `React.HTMLAttributes` — `size?: 'sm' \| 'md' \| 'lg'` | SVG-based spinning loader with 3 sizes. | `cn` |
| 18 | EmptyState | `src/components/ui/empty-state.tsx` | `EmptyStateProps` — `icon?: ReactNode`; `title: string`; `description: string`; `action?: { label: string; onClick: () => void }`; `secondaryAction?: { label: string; onClick: () => void }` | Placeholder for empty lists/pages with optional CTA. | `Button`, `cn` |
| 19 | ErrorState | `src/components/ui/error-state.tsx` | `ErrorStateProps` — `error?: Error \| null`; `onRetry?: () => void`; `message?: string` | Inline error display with retry button. | `Button`, `LoadingSpinner`, `lucide-react`, `cn` |
| 20 | MetricCard | `src/components/ui/metric-card.tsx` | `MetricCardProps` extends `React.HTMLAttributes` — `label: string`; `value: string \| number`; `change?: { value: number; direction: 'up' \| 'down' }`; `icon?: ReactNode` | KPI card with trend indicator and optional icon. | `lucide-react`, `cn` |

## Layout Components (src/components/layout/)

| # | Component | File Path | Props Interface | Description | Dependencies |
|---|-----------|-----------|-----------------|-------------|--------------|
| 21 | Sidebar | `src/components/layout/sidebar.tsx` | None (uses stores) | Collapsible sidebar (240px/64px) with RBAC-filtered nav items, user info, collapse toggle. Framer Motion animated. | `useNavigationStore`, `useAuthStore`, `useRBAC`, `Tooltip`, `lucide-react`, `framer-motion`, `cn` |
| 22 | TopNav | `src/components/layout/top-nav.tsx` | None (uses stores) | Sticky top bar with breadcrumbs, search/CMD+K button, notification bell with badge, profile menu. | `useCommandPaletteStore`, `useNotificationStore`, `Breadcrumbs`, `NotificationCenter`, `ProfileMenu`, `lucide-react` |
| 23 | Breadcrumbs | `src/components/layout/breadcrumbs.tsx` | None (uses pathname) | Dynamic breadcrumb generator from URL segments. Maps segment slugs to display labels. | `next/navigation`, `next/link`, `lucide-react` |
| 24 | NotificationCenter | `src/components/layout/notification-center.tsx` | `open: boolean`; `onClose: () => void` | Dropdown notification panel with read/dismiss actions. | `useNotificationStore`, `ScrollArea` |
| 25 | ProfileMenu | `src/components/layout/profile-menu.tsx` | `open: boolean`; `onClose: () => void` | User profile dropdown with logout action. | `useAuthStore`, `DropdownMenu` |

## Command Palette (src/components/command-palette/)

| # | Component | File Path | Props Interface | Description | Dependencies |
|---|-----------|-----------|-----------------|-------------|--------------|
| 26 | CommandPalette | `src/components/command-palette/command-palette.tsx` | None (uses store) | CMD+K command palette using cmdk. Groups: Navigation (11 items) + Actions (4 items). Keyboard shortcut, search, Framer Motion animations. | `cmdk`, `useCommandPaletteStore`, `next/navigation`, `framer-motion`, `lucide-react` |

## RBAC Components (src/components/rbac/)

| # | Component | File Path | Props Interface | Description | Dependencies |
|---|-----------|-----------|-----------------|-------------|--------------|
| 27 | ProtectedAction | `src/components/rbac/protected-action.tsx` | `permission: string`; `children: ReactNode`; `fallback?: ReactNode` | Conditional render wrapper — shows children if user has permission, otherwise fallback. | `useRBAC` |
| 28 | ProtectedPage | `src/components/rbac/protected-page.tsx` | `permission: string`; `children: ReactNode` | Full-page access denied screen with Shield icon if user lacks permission. | `useRBAC`, `lucide-react` |

## Error Handling Components

| # | Component | File Path | Props Interface | Description | Dependencies |
|---|-----------|-----------|-----------------|-------------|--------------|
| 29 | ErrorBoundary | `src/components/error-boundary.tsx` | `children: ReactNode`; `fallback?: ReactNode`; `onError?: (error: Error, errorInfo: ErrorInfo) => void` | Reusable class-based error boundary with reset capability. | `Button`, `lucide-react` |
| 30 | GlobalError | `src/app/error.tsx` | `error: Error & { digest?: string }`; `reset: () => void` | Next.js error page for root-level errors. Full-page with retry + redirect. | `Button`, `lucide-react` |
| 31 | NotFound | `src/app/not-found.tsx` | None | 404 page with back-to-dashboard link. | `Button`, `next/link` |
| 32 | DashboardError | `src/app/dashboard/error.tsx` | `error: Error & { digest?: string }`; `reset: () => void` | Next.js error page for dashboard-scoped errors. | `Button`, `lucide-react` |

## Error Handling Utilities (src/lib/)

| # | Function | File Path | Signature | Description | Dependencies |
|---|----------|-----------|-----------|-------------|--------------|
| 33 | getErrorMessage | `src/lib/errors.ts` | `(error: unknown) => string` | Extracts user-friendly message from ApiError, Error, or unknown. | `ApiError` |
| 34 | getErrorTitle | `src/lib/errors.ts` | `(error: unknown) => string` | Returns contextual title (Not Found, Access Denied, etc.) based on HTTP status. | `ApiError` |

## Utility Functions (src/lib/)

| # | Function | File Path | Signature | Description |
|---|----------|-----------|-----------|-------------|
| 35 | cn | `src/lib/utils.ts` | `(...inputs: ClassValue[]) => string` | Tailwind class merger (clsx + tailwind-merge). |
| 36 | formatCurrency | `src/lib/utils.ts` | `(value: number) => string` | USD currency formatting. |
| 37 | formatNumber | `src/lib/utils.ts` | `(value: number) => string` | Compact number formatting (1.2K, 3.4M). |
| 38 | formatPercent | `src/lib/utils.ts` | `(value: number) => string` | Percentage formatting with 1 decimal. |
| 39 | formatDate | `src/lib/utils.ts` | `(date: Date \| string, options?: Intl.DateTimeFormatOptions) => string` | Date formatting, default "Jan 1, 2026". |
| 40 | sleep | `src/lib/utils.ts` | `(ms: number) => Promise<void>` | Promise-based delay. |
| 41 | debounce | `src/lib/utils.ts` | `<T extends Function>(fn: T, delay: number) => (...args) => void` | Standard debounce. |
| 42 | getInitials | `src/lib/utils.ts` | `(name: string) => string` | Extracts up to 2 uppercase initials from name. |
| 43 | truncate | `src/lib/utils.ts` | `(str: string, maxLength: number) => string` | Truncates string with ellipsis. |
| 44 | generateId | `src/lib/utils.ts` | `() => string` | UUID v4 generator via crypto.randomUUID(). |
| 45 | classNames | `src/lib/utils.ts` | `(...classes: (string \| boolean \| undefined \| null)[]) => string` | Simple class name joiner. |
