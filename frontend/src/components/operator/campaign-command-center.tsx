"use client";

/**
 * Campaign Command Center — single surface showing status/progress/next action
 * with inline Pause/Resume/Archive controls.
 */

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import {
  Play, Pause, Archive, AlertTriangle, Activity, Loader2,
  CheckCircle2, Clock, XCircle, ChevronRight, Search,
} from "lucide-react";
import { fetchApi, ApiError } from "@/lib/api";
import { HealthPill } from "./health-pill";
import { HealthLevel } from "./health";
import { safeArr, safeUpper, safeLower } from "@/lib/safe";

interface Campaign {
  id: string;
  name: string;
  client_id: string;
  client_name?: string;
  campaign_type: string;
  status?: string;
  target_link_count?: number;
  acquired_link_count?: number;
  health_score?: number;
  started_at?: string;
  completed_at?: string;
  updated_at?: string;
  created_at?: string;
}

type Status = "active" | "paused" | "draft" | "completed" | "failed" | "archived" | "unknown";

function deriveStatus(c: Campaign): Status {
  const s = (c.status || "").toLowerCase();
  if (["active", "running", "in_progress", "executing"].includes(s)) return "active";
  if (s === "paused") return "paused";
  if (s === "draft") return "draft";
  if (["completed", "complete", "done", "success"].includes(s)) return "completed";
  if (s === "archived") return "archived";
  if (s === "failed" || s === "error") return "failed";
  // Infer from health
  if (typeof c.health_score === "number" && c.health_score < 0.2 && (c.acquired_link_count ?? 0) === 0) return "failed";
  return s ? (s as Status) : "unknown";
}

function statusLevel(s: Status): HealthLevel {
  switch (s) {
    case "active": return "healthy";
    case "paused": case "draft": return "warning";
    case "completed": return "healthy";
    case "failed": return "critical";
    case "archived": return "unknown";
    default: return "unknown";
  }
}

function statusLabel(s: Status): string {
  return safeUpper(s);
}

function progressPercent(c: Campaign): number {
  if (!c.target_link_count || c.target_link_count === 0) return 0;
  return Math.min(100, Math.round(((c.acquired_link_count ?? 0) / c.target_link_count) * 100));
}

function nextActionFor(s: Status, c: Campaign): string {
  switch (s) {
    case "active": return "Running prospect discovery";
    case "paused": return "Resume to continue";
    case "draft": return "Launch to start";
    case "completed": return "Archive to clean up";
    case "failed": return "Investigate why it stopped";
    case "archived": return "No further action";
    default: return "Status unknown";
  }
}

function lastFailureFor(c: Campaign): string {
  if (typeof c.health_score === "number" && c.health_score < 0.3) {
    return `Health score low (${(c.health_score * 100).toFixed(0)}%)`;
  }
  if ((c.acquired_link_count ?? 0) === 0 && c.started_at) {
    return "No links acquired yet";
  }
  return "none in last 24h";
}

export function CampaignCommandCenter() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | Status>("all");

  const q = useQuery<any>({
    queryKey: ["ccc-campaigns"],
    queryFn: () => fetchApi<any>("/campaigns?limit=100"),
    refetchInterval: 15000,
  });

  const pauseMut = useMutation({
    mutationFn: (id: string) => fetchApi(`/campaigns/${id}/pause`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ccc-campaigns"] }),
  });

  const resumeMut = useMutation({
    mutationFn: (id: string) => fetchApi(`/campaigns/${id}/resume`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ccc-campaigns"] }),
  });

  const archiveMut = useMutation({
    mutationFn: (id: string) => fetchApi(`/campaigns/${id}/archive`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ccc-campaigns"] }),
  });

  if (q.isError) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-6">
        <div className="flex items-center gap-2 mb-2">
          <XCircle className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-bold text-slate-100">Campaigns unavailable</h2>
        </div>
        <p className="text-sm text-slate-300">
          The platform is having trouble loading campaigns.
        </p>
        <p className="text-xs text-slate-500 mt-2 font-mono">
          Error: {q.error instanceof ApiError ? q.error.status : "unknown"} ·{" "}
          {q.error instanceof Error ? q.error.message : "unknown"}
        </p>
        <button
          onClick={() => q.refetch()}
          className="mt-3 px-3 py-1.5 rounded-md border border-surface-border text-sm text-slate-300 hover:border-slate-500"
        >
          Try again
        </button>
      </div>
    );
  }

  const items: Campaign[] = (q.data?.data as any) || (q.data as any) || [];
  const filtered = safeArr<Campaign>(items).filter((c) => {
    if (statusFilter !== "all" && deriveStatus(c) !== statusFilter) return false;
    if (search && !safeLower(c.name, "").includes(safeLower(search, ""))) return false;
    return true;
  });

  // Aggregate counts
  const counts = {
    total: items.length,
    active: items.filter((c) => deriveStatus(c) === "active").length,
    paused: items.filter((c) => deriveStatus(c) === "paused").length,
    completed: items.filter((c) => deriveStatus(c) === "completed").length,
    failed: items.filter((c) => deriveStatus(c) === "failed").length,
    needsAction: items.filter((c) => deriveStatus(c) === "failed").length,
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="rounded-xl border border-surface-border bg-surface-card/80 backdrop-blur-md p-5 shadow-xl shadow-black/20">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-2">
              <Activity className="w-4 h-4 text-platform-400" />
              Campaigns
            </h2>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              {counts.total} total · {counts.active} active · {counts.paused} paused · {counts.completed} completed · {counts.failed} failed
            </p>
          </div>
          <div className="flex items-center gap-2">
            {counts.needsAction > 0 && (
              <Link
                href="#needs-action"
                className="px-3 py-1.5 rounded-md border border-red-500/30 bg-red-500/10 text-red-300 text-xs font-mono font-bold hover:bg-red-500/20"
              >
                {counts.needsAction} NEEDS ACTION ↓
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search campaigns…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-md border border-surface-border bg-surface-darker text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500"
          />
        </div>
        <div className="flex items-center gap-1 text-[10px] font-mono uppercase">
          {(["all", "active", "paused", "failed", "completed"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f as any)}
              className={`px-2 py-1 rounded border transition-colors ${
                statusFilter === f
                  ? "border-platform-500 bg-platform-500/20 text-platform-300"
                  : "border-surface-border text-slate-500 hover:text-slate-300"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Campaigns list */}
      {q.isLoading ? (
        <div className="text-center py-12 text-slate-500">
          <Loader2 className="w-6 h-6 mx-auto animate-spin mb-2" />
          <div className="text-xs font-mono">Loading campaigns…</div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-surface-border bg-surface-card/80 p-12 text-center">
          <div className="text-sm text-slate-300 font-semibold mb-1">No campaigns</div>
          <div className="text-xs text-slate-500">No campaigns match your filters.</div>
        </div>
      ) : (
        <ul className="space-y-2">
          {filtered.map((c) => (
            <CampaignRow
              key={c.id}
              c={c}
              onPause={() => pauseMut.mutate(c.id)}
              onResume={() => resumeMut.mutate(c.id)}
              onArchive={() => archiveMut.mutate(c.id)}
              pausing={pauseMut.isPending && pauseMut.variables === c.id}
              resuming={resumeMut.isPending && resumeMut.variables === c.id}
              archiving={archiveMut.isPending && archiveMut.variables === c.id}
              lastError={
                pauseMut.error && pauseMut.variables === c.id ? String(pauseMut.error) :
                resumeMut.error && resumeMut.variables === c.id ? String(resumeMut.error) :
                archiveMut.error && archiveMut.variables === c.id ? String(archiveMut.error) :
                null
              }
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function CampaignRow({ c, onPause, onResume, onArchive, pausing, resuming, archiving, lastError }: {
  c: Campaign;
  onPause: () => void;
  onResume: () => void;
  onArchive: () => void;
  pausing: boolean;
  resuming: boolean;
  archiving: boolean;
  lastError: string | null;
}) {
  const status = deriveStatus(c);
  const level = statusLevel(status);
  const percent = progressPercent(c);
  const nextAction = nextActionFor(status, c);

  return (
    <li
      id={status === "failed" ? "needs-action" : undefined}
      className={`rounded-md border p-4 transition-colors ${
        status === "failed"
          ? "border-red-500/30 bg-red-500/5"
          : status === "paused"
          ? "border-amber-500/30 bg-amber-500/5"
          : "border-surface-border bg-surface-card/40 hover:border-slate-500"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <Link
              href={`/dashboard/campaigns/${c.id}`}
              className="text-sm font-semibold text-slate-100 hover:text-platform-300 transition-colors"
            >
              {c.name || `Campaign ${c.id.slice(0, 8)}`}
            </Link>
            <HealthPill level={level} size="sm" />
            {c.campaign_type && (
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">· {c.campaign_type}</span>
            )}
          </div>
          <div className="text-xs text-slate-500 mb-2">
            {c.acquired_link_count ?? 0} of {c.target_link_count ?? 0} links acquired · health {((c.health_score ?? 0) * 100).toFixed(0)}%
          </div>

          {/* Progress bar */}
          <div className="h-1.5 bg-surface-darker rounded-full overflow-hidden mb-3">
            <div
              className={`h-full transition-all ${
                status === "failed" ? "bg-red-500" :
                status === "paused" ? "bg-amber-500" :
                "bg-platform-500"
              }`}
              style={{ width: `${percent}%` }}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-3 gap-y-1 text-[11px] font-mono">
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Last action</div>
              <div className="text-slate-300">{c.updated_at ? new Date(c.updated_at).toLocaleString() : "—"}</div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Last failure</div>
              <div className={status === "failed" ? "text-red-300" : "text-slate-300"}>{lastFailureFor(c)}</div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Last success</div>
              <div className="text-slate-300">{c.completed_at ? new Date(c.completed_at).toLocaleString() : "—"}</div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Next action</div>
              <div className="text-slate-300">{nextAction}</div>
            </div>
          </div>

          {lastError && (
            <div className="mt-2 text-[11px] text-red-300 font-mono bg-red-500/10 border border-red-500/20 rounded px-2 py-1">
              Action failed: {lastError}
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex flex-col gap-1.5 flex-shrink-0">
          {status === "active" && (
            <button
              onClick={onPause}
              disabled={pausing}
              className="px-3 py-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs font-mono font-bold hover:bg-amber-500/20 disabled:opacity-50 flex items-center gap-1.5"
            >
              {pausing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Pause className="w-3 h-3" />}
              PAUSE
            </button>
          )}
          {status === "paused" && (
            <button
              onClick={onResume}
              disabled={resuming}
              className="px-3 py-1.5 rounded-md border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs font-mono font-bold hover:bg-emerald-500/20 disabled:opacity-50 flex items-center gap-1.5"
            >
              {resuming ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
              RESUME
            </button>
          )}
          {(status === "paused" || status === "completed" || status === "failed") && (
            <button
              onClick={onArchive}
              disabled={archiving}
              className="px-3 py-1.5 rounded-md border border-surface-border text-slate-400 text-xs font-mono hover:border-slate-500 hover:text-slate-200 disabled:opacity-50 flex items-center gap-1.5"
            >
              {archiving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Archive className="w-3 h-3" />}
              ARCHIVE
            </button>
          )}
          <Link
            href={`/dashboard/campaigns/${c.id}`}
            className="px-3 py-1.5 rounded-md border border-surface-border text-slate-400 text-xs font-mono hover:border-slate-500 hover:text-slate-200 flex items-center gap-1.5"
          >
            DETAILS <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </li>
  );
}
