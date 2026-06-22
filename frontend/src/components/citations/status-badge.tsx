"use client";

import { Badge } from "@/components/ui/badge";

const STATUS_STYLES: Record<string, string> = {
  active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  paused: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  completed: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  archived: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  pending: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  not_started: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  in_progress: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  submitted: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  already_exists: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  new_backlink: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
  rejected: "bg-red-500/10 text-red-400 border-red-500/20",
  expired: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  pending_review: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={`text-[10px] font-mono uppercase tracking-wider ${STATUS_STYLES[status] || STATUS_STYLES.pending}`}
    >
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
