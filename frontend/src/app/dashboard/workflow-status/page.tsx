"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity,
  Crosshair,
  Bookmark,
  ClipboardCheck,
  Clock,
  ArrowRight,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { workflowApi, WorkflowItem, WorkflowOverview } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  draft: "text-slate-400 bg-slate-500/10 border-slate-500/20",
  active: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  paused: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  completed: "text-platform-400 bg-platform-500/10 border-platform-500/20",
  pending: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  failed: "text-red-400 bg-red-500/10 border-red-500/20",
  in_progress: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
  already_exists: "text-slate-400 bg-slate-500/10 border-slate-500/20",
  not_started: "text-slate-400 bg-slate-500/10 border-slate-500/20",
};

const TYPE_ICONS: Record<string, React.ReactNode> = {
  campaign: <Crosshair className="w-4 h-4" />,
  citation_project: <Bookmark className="w-4 h-4" />,
  approval: <ClipboardCheck className="w-4 h-4" />,
};

const TYPE_COLORS: Record<string, string> = {
  campaign: "text-platform-400",
  citation_project: "text-cyan-400",
  approval: "text-amber-400",
};

function Progress({ value }: { value: number }) {
  return (
    <div className="w-full h-2 bg-slate-700/50 rounded-full overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="h-full rounded-full"
        style={{
          background:
            value >= 80
              ? "linear-gradient(90deg, #10b981, #34d399)"
              : value >= 40
                ? "linear-gradient(90deg, #f59e0b, #fbbf24)"
                : "linear-gradient(90deg, #6366f1, #818cf8)",
        }}
      />
    </div>
  );
}

function WorkflowCard({ item }: { item: WorkflowItem }) {
  const statusClass = STATUS_STYLES[item.status] || STATUS_STYLES.draft;
  const typeIcon = TYPE_ICONS[item.type] || <Activity className="w-4 h-4" />;
  const typeColor = TYPE_COLORS[item.type] || "text-slate-400";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-surface-border bg-surface-card p-4 hover:border-platform-500/30 transition-colors"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className={typeColor}>{typeIcon}</span>
          <h3 className="text-sm font-medium text-slate-200 truncate">{item.name}</h3>
        </div>
        <span className={`text-[11px] font-mono px-2 py-0.5 rounded-full border shrink-0 ${statusClass}`}>
          {item.status}
        </span>
      </div>

      <div className="mb-3">
        <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
          <span>Progress</span>
          <span className="font-mono">{item.progress}%</span>
        </div>
        <Progress value={item.progress} />
      </div>

      <div className="flex items-center gap-4 text-[11px] text-slate-500 mb-3">
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>{item.started ? new Date(item.started).toLocaleDateString() : "—"}</span>
        </div>
        <div className="flex items-center gap-1">
          <RefreshCw className="w-3 h-3" />
          <span>{item.updated ? new Date(item.updated).toLocaleDateString() : "—"}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/10">
        <ArrowRight className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span className="text-xs text-amber-300 font-medium">{item.next_action}</span>
      </div>
    </motion.div>
  );
}

function Section({
  title,
  icon,
  count,
  items,
}: {
  title: string;
  icon: React.ReactNode;
  count: number;
  items: WorkflowItem[];
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-slate-400">{icon}</span>
        <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
        <span className="text-[11px] font-mono text-slate-500">({count})</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-slate-500 italic">No items</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <WorkflowCard key={`${item.type}-${item.id}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function WorkflowStatusPage() {
  const { data, isLoading, refetch } = useQuery<WorkflowOverview>({
    queryKey: ["workflow-overview"],
    queryFn: () => workflowApi.getOverview(),
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-platform-400" />
          <h1 className="text-lg font-semibold text-slate-100">Workflow Status</h1>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-platform-400 animate-spin" />
        </div>
      ) : data ? (
        <>
          <div className="flex items-center gap-6 px-4 py-3 rounded-xl border border-surface-border bg-surface-card">
            <div className="flex items-center gap-2">
              <Crosshair className="w-4 h-4 text-platform-400" />
              <span className="text-xs text-slate-400">
                <span className="font-mono font-semibold text-slate-200">{data.campaigns.length}</span> active campaigns
              </span>
            </div>
            <div className="w-px h-4 bg-surface-border" />
            <div className="flex items-center gap-2">
              <Bookmark className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-slate-400">
                <span className="font-mono font-semibold text-slate-200">{data.citations.length}</span> citation projects
              </span>
            </div>
            <div className="w-px h-4 bg-surface-border" />
            <div className="flex items-center gap-2">
              <ClipboardCheck className="w-4 h-4 text-amber-400" />
              <span className="text-xs text-slate-400">
                <span className="font-mono font-semibold text-slate-200">{data.approvals.length}</span> pending approvals
              </span>
            </div>
            <div className="w-px h-4 bg-surface-border" />
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-400" />
              <span className="text-xs text-slate-400">
                <span className="font-mono font-semibold text-slate-200">{data.total_active}</span> total active
              </span>
            </div>
          </div>

          <Section
            title="Active Campaigns"
            icon={<Crosshair className="w-4 h-4" />}
            count={data.campaigns.length}
            items={data.campaigns}
          />

          <Section
            title="Citation Projects"
            icon={<Bookmark className="w-4 h-4" />}
            count={data.citations.length}
            items={data.citations}
          />

          <Section
            title="Pending Approvals"
            icon={<ClipboardCheck className="w-4 h-4" />}
            count={data.approvals.length}
            items={data.approvals}
          />
        </>
      ) : (
        <p className="text-sm text-slate-500 text-center py-10">No workflow data available</p>
      )}
    </div>
  );
}
