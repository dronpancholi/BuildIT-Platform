'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  BarChart3,
  Users,
  Target,
  CalendarCheck,
  ClipboardCheck,
  FileBarChart,
  Lightbulb,
  MapPin,
  Zap,
  Settings,
  ChevronsLeft,
  ChevronsRight,
  Mail,
  Send,
  Inbox,
  Library,
  Activity,
  Server,
  Stethoscope,
  AlertOctagon,
  Power,
  Siren,
  Network,
  Brain,
  TrendingUp,
  Crosshair,
  ChevronDown,
  ChevronUp,
  Eye,
  Search,
  LineChart,
  Shield,
  ShieldAlert,
  Bell,
  CheckSquare,
  Briefcase,
  Globe,
  FlaskConical,
  GitBranch,
  Rocket,
  Cpu,
  Layers,
  Workflow,
  AlertCircle,
  Boxes,
  Bookmark,
  ScrollText,
  RotateCcw,
  Heart,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNavigationStore } from '@/stores/navigation-store';
import { useAuthStore } from '@/stores/auth-store';
import { useRBAC } from '@/hooks/use-rbac';
import { getInitials } from '@/lib/utils';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  permission?: string;
  badge?: 'approvals';
}

interface NavGroup {
  label: string;
  items: NavItem[];
  defaultOpen?: boolean;
  advanced?: boolean;
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Operations',
    defaultOpen: true,
    items: [
      { label: 'System Health', href: '/dashboard/system-health', icon: Stethoscope },
      { label: 'Workflow Status', href: '/dashboard/workflow-status', icon: Activity },
      { label: 'Command Center', href: '/dashboard', icon: LayoutDashboard },
      { label: 'Executive', href: '/dashboard/executive', icon: BarChart3, permission: 'executive:read' },
      { label: 'Customers', href: '/dashboard/clients', icon: Users, permission: 'customers:read' },
      { label: 'Campaigns', href: '/dashboard/campaigns', icon: Crosshair },
      { label: 'Plans', href: '/dashboard/plans', icon: CalendarCheck, permission: 'planning:read' },
    ],
  },
  {
    label: 'Execution',
    defaultOpen: true,
    items: [
      { label: 'Action Center', href: '/dashboard/action-center', icon: Bell },
      { label: 'Tasks', href: '/dashboard/tasks', icon: CheckSquare },
      { label: 'Campaign Operations', href: '/dashboard/campaign-operations', icon: Briefcase },
      { label: 'Outreach Operations', href: '/dashboard/outreach-operations', icon: Mail },
      { label: 'Citation Operations', href: '/dashboard/citation-operations', icon: Globe },
      { label: 'Approvals', href: '/dashboard/approvals', icon: Shield, badge: 'approvals' },
      { label: 'Automation', href: '/dashboard/automation', icon: Zap },
    ],
  },
  {
    label: 'Outreach',
    defaultOpen: true,
    items: [
      { label: 'Keywords', href: '/dashboard/keywords', icon: Target },
      { label: 'Prospects', href: '/dashboard/prospect-list', icon: Search },
      { label: 'Communication Hub', href: '/dashboard/communication-hub', icon: Mail },
      { label: 'Outbox', href: '/dashboard/outbox', icon: Inbox },
      { label: 'Templates', href: '/dashboard/templates', icon: Library },
      { label: 'Local SEO', href: '/dashboard/local-seo', icon: MapPin },
      { label: 'Citations', href: '/dashboard/citations', icon: Bookmark },
    ],
  },
  {
    label: 'Insights',
    defaultOpen: true,
    items: [
      { label: 'Reports', href: '/dashboard/reports', icon: FileBarChart, permission: 'reports:read' },
      { label: 'Smart Alerts', href: '/dashboard/recommendations', icon: Lightbulb },
      { label: 'Recommendations V2', href: '/dashboard/recommendations-v2', icon: Lightbulb },
      { label: 'Backlink Intel', href: '/dashboard/backlink-intelligence', icon: Network },
      { label: 'SEO Intel', href: '/dashboard/seo-intelligence', icon: Brain },
      { label: 'Trend Analysis', href: '/dashboard/predictive', icon: TrendingUp },
      { label: 'Competitor Intel', href: '/dashboard/competitor-intelligence', icon: Target },
      { label: 'SEO Health', href: '/dashboard/seo-health', icon: Heart },
      { label: 'Local SEO', href: '/dashboard/local-seo', icon: MapPin },
      { label: 'Citation Intel', href: '/dashboard/citation-intelligence', icon: Network },
    ],
  },
  {
    label: 'Safety & Health',
    defaultOpen: true,
    items: [
      { label: 'System Status', href: '/dashboard/system', icon: Server },
      { label: 'Live Operations', href: '/dashboard/war-room', icon: Stethoscope },
      { label: 'Provider Health', href: '/dashboard/providers', icon: Activity },
      { label: 'Temporal Ops', href: '/dashboard/temporal', icon: Workflow },
      { label: 'Kill Switches', href: '/dashboard/killswitches', icon: Power },
      { label: 'Incidents', href: '/dashboard/incidents', icon: Siren },
      { label: 'Failure Recovery', href: '/dashboard/recovery', icon: RotateCcw },
    ],
  },
  {
    label: 'Advanced',
    defaultOpen: false,
    advanced: true,
    items: [
      { label: 'Traces', href: '/dashboard/traces', icon: GitBranch },
      { label: 'Events', href: '/dashboard/events', icon: Workflow },
      { label: 'Intelligence', href: '/dashboard/intelligence', icon: FlaskConical },
      { label: 'Lineage', href: '/dashboard/lineage', icon: Layers },
      { label: 'Topology', href: '/dashboard/topology', icon: Boxes },
      { label: 'SEO Copilot', href: '/dashboard/copilot-v2', icon: Brain },
      { label: 'Workflow Monitor', href: '/dashboard/ai-ops', icon: Cpu },
      { label: 'Scraping', href: '/dashboard/scraping', icon: Eye },
      { label: 'Strategic', href: '/dashboard/strategic', icon: Rocket },
      { label: 'Governance', href: '/dashboard/governance', icon: ShieldAlert },
      { label: 'Economics', href: '/dashboard/economics', icon: LineChart },
      { label: 'Operations Lifecycle', href: '/dashboard/operations-lifecycle', icon: Workflow },
      { label: 'Advanced SRE', href: '/dashboard/advanced-sre', icon: Stethoscope },
      { label: 'Maintenance', href: '/dashboard/maintainability', icon: Settings },
      { label: 'Deployment', href: '/dashboard/deployment', icon: Server },
      { label: 'Global Infra', href: '/dashboard/global-infra', icon: Network },
      { label: 'Cross-tenant', href: '/dashboard/cross-tenant', icon: Layers },
      { label: 'Incidents Evolution', href: '/dashboard/incident-evolution', icon: Siren },
      { label: 'Ecosystem', href: '/dashboard/ecosystem-maturity', icon: Brain },
    ],
  },
  {
    label: 'Settings',
    defaultOpen: true,
    items: [
      { label: 'Settings', href: '/dashboard/settings', icon: Settings, permission: 'system:read' },
      { label: 'Provider Center', href: '/dashboard/providers-v2', icon: Settings, permission: 'system:read' },
      { label: 'Credential Vault', href: '/dashboard/settings/vault', icon: Shield, permission: 'system:read' },
      { label: 'Proxy Pools', href: '/dashboard/settings/proxies', icon: Server, permission: 'system:read' },
      { label: 'Audit Log', href: '/dashboard/audit', icon: ScrollText, permission: 'system:read' },
      { label: 'User Management', href: '/dashboard/settings/users', icon: Users, permission: 'system:read' },
    ],
  },
];

interface ApprovalCount {
  success: boolean;
  data: unknown[] | null;
}

function useApprovalsCount(): number {
  const { data } = useQuery<ApprovalCount>({
    queryKey: ['approvals-count', MOCK_TENANT_ID],
    queryFn: () =>
      fetchApi<ApprovalCount>(
        `/approvals?tenant_id=${MOCK_TENANT_ID}&status=pending&limit=1`
      ),
    refetchInterval: 30_000,
  });
  if (data && Array.isArray(data.data)) return data.data.length;
  return 0;
}

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useNavigationStore();
  const user = useAuthStore((s) => s.user);
  const { can } = useRBAC();
  const approvalsCount = useApprovalsCount();
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const isActive = (href: string) => {
    if (href === '/dashboard') return pathname === '/dashboard';
    return pathname === href || pathname.startsWith(href + '/');
  };

  const renderNavItem = (item: NavItem) => {
    if (item.permission && !can(item.permission)) return null;
    const Icon = item.icon;
    const active = isActive(item.href);
    const showBadge = item.badge === 'approvals' && approvalsCount > 0;

    const link = (
      <Link
        href={item.href}
        className={cn(
          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors relative',
          active
            ? 'bg-platform-600/10 text-platform-400'
            : 'text-slate-400 hover:bg-surface-card hover:text-slate-200'
        )}
        data-testid={`nav-${item.href.replace(/\//g, '-')}`}
      >
        {active && (
          <motion.div
            layoutId="sidebar-active"
            className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-platform-500 rounded-r"
            transition={{ duration: 0.2 }}
          />
        )}
        <Icon className="w-4 h-4 shrink-0" />
        <AnimatePresence mode="wait">
          {!sidebarCollapsed && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.15 }}
              className="whitespace-nowrap overflow-hidden flex-1"
            >
              {item.label}
            </motion.span>
          )}
        </AnimatePresence>
        {showBadge && !sidebarCollapsed && (
          <span
            className="ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/20"
            data-testid="nav-approvals-badge"
          >
            {approvalsCount}
          </span>
        )}
        {showBadge && sidebarCollapsed && (
          <span
            className="absolute top-1 right-1 w-2 h-2 rounded-full bg-amber-400"
            data-testid="nav-approvals-dot"
          />
        )}
      </Link>
    );

    if (sidebarCollapsed) {
      return (
        <Tooltip key={item.href}>
          <TooltipTrigger asChild>{link}</TooltipTrigger>
          <TooltipContent side="right">
            {item.label}
            {showBadge && ` (${approvalsCount})`}
          </TooltipContent>
        </Tooltip>
      );
    }
    return <div key={item.href}>{link}</div>;
  };

  return (
    <TooltipProvider delayDuration={0}>
      <motion.aside
        initial={false}
        animate={{ width: sidebarCollapsed ? 64 : 240 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className="flex flex-col h-screen bg-surface-card border-r border-surface-border shrink-0 overflow-hidden"
      >
        {/* Logo */}
        <div className="flex items-center h-14 px-4 border-b border-surface-border shrink-0">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-platform-600 shrink-0">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <AnimatePresence mode="wait">
              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.15 }}
                  className="text-sm font-semibold text-slate-100 whitespace-nowrap overflow-hidden"
                >
                  BuildIT
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-3">
          {NAV_GROUPS.map((group) => {
            if (group.advanced && !advancedOpen && !sidebarCollapsed) {
              return (
                <button
                  key={group.label}
                  onClick={() => setAdvancedOpen(true)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-500 hover:text-slate-300 transition-colors"
                  data-testid="nav-advanced-toggle"
                >
                  <ChevronDown className="w-3 h-3" />
                  {group.label} ({group.items.length})
                </button>
              );
            }
            if (group.advanced && !advancedOpen && sidebarCollapsed) {
              return null;
            }
            return (
              <div key={group.label} className="space-y-0.5">
                {!sidebarCollapsed && (
                  <div className="flex items-center justify-between px-3 py-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                      {group.label}
                    </span>
                    {group.advanced && (
                      <button
                        onClick={() => setAdvancedOpen(false)}
                        className="text-slate-500 hover:text-slate-300"
                        aria-label="Collapse advanced"
                      >
                        <ChevronUp className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                )}
                {group.items.map(renderNavItem)}
              </div>
            );
          })}
        </nav>

        {/* User info */}
        <div className="border-t border-surface-border p-3 shrink-0">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-platform-600/20 flex items-center justify-center shrink-0 text-xs font-medium text-platform-400">
              {user ? getInitials(user.name) : '?'}
            </div>
            <AnimatePresence mode="wait">
              {!sidebarCollapsed && (
                <motion.div
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.15 }}
                  className="overflow-hidden"
                >
                  <p className="text-sm font-medium text-slate-200 truncate">
                    {user?.name ?? 'Unknown'}
                  </p>
                  <p className="text-xs text-slate-500 capitalize truncate">
                    {user?.role ?? 'viewer'}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Collapse button */}
        <div className="border-t border-surface-border p-2 shrink-0">
          <button
            onClick={toggleSidebar}
            className={cn(
              'flex items-center justify-center w-full rounded-lg py-2 text-slate-400 hover:bg-surface-card hover:text-slate-200 transition-colors'
            )}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? (
              <ChevronsRight className="w-5 h-5" />
            ) : (
              <ChevronsLeft className="w-5 h-5" />
            )}
          </button>
        </div>
      </motion.aside>
    </TooltipProvider>
  );
}
