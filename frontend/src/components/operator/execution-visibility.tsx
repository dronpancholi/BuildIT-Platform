"use client";

/**
 * Execution Visibility — running/queued/completed/failed/stuck executions.
 * STUCK = running >1h with no progress.
 * Honest about /executions endpoint failures (P0: action_executions table missing).
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, useMemo } from "react";
import {
  Activity, Loader2, AlertOctagon, CheckCircle2, XCircle, Clock,
  Pause, Play, ChevronRight, Search, Zap,
} from "lucide-react";
import { fetchApi, ApiError } from "@/lib/api";
import { HealthPill } from "./health-pill";
import { HealthLevel } from "./health";
import { safeArr, safeLower } from "@/lib/safe";

type ExecStatus = "running" | "queued" | "completed" | "failed" | "stuck" | "unknown";

interface Execution {
  id: string;
  status: string;
  action_type?: string;
  resource_type?: string;
  resource_id?: string;
  progress_pct?: number;
  started_at?: string;
  completed_at?: string;
  last_progress_at?: string;
  updated_at?: string;
  error?: string;
  duration_ms?: number;
  campaign_id?: string;
  client_id?: string;
  result_summary?: string;
}

const STUCK_THRESHOLD_MS = 60 * 60 * 1000; // 1 hour

function deriveStatus(e: Execution): ExecStatus {
  const s = (e.status || "").toLowerCase();
  if (s === "running" || s === "in_progress" || s === "executing") {
    // Check if stuck
    const ref = e.last_progress_at || e.started_at;
    if (ref) {
      const age = Date.now() - new Date(ref).getTime();
      if (age > STUCK_THRESHOLD_MS) return "stuck";
    }
    return "running";
  }
  if (s === "queued" || s === "pending") return "queued";
  if (["completed", "complete", "success", "succeeded"].includes(s)) return "completed";
  if (["failed", "error", "cancelled"].includes(s)) return "failed";
  return "unknown";
}

function statusLevel(s: ExecStatus): HealthLevel {
  switch (s) {
    case "running": return "healthy";
    case "queued": return "warning";
    case "completed": return "healthy";
    case "failed": return "critical";
    case "stuck": return "critical";
    default: return "unknown";
  }
}

function statusLabel(s: ExecStatus): string {
  switch (s) {
    case "running": return "RUNNING";
    case "queued": return "QUEUED";
    case "completed": return "COMPLETED";
    case "failed": return "FAILED";
    case "stuck": return "STUCK";
    default: return "UNKNOWN";
  }
}

function formatDuration(ms?: number): string {
  if (!ms) return "—";
  if (ms < 1000) return `${ms}ms`;
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ${sec % 60}s`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ${min % 60}m`;
  const days = Math.floor(hr / 24);
  return `${days}d ${hr % 24}h`;
}

export function ExecutionVisibility() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | ExecStatus>("all");

  const q = useQuery<{ data: Execution[]; probe: "ok" | "error" | "unknown" }>({
    queryKey: ["exec-visibility"],
    queryFn: async () => {
      try {
        const data = await fetchApi<any>("/executions?limit=100");
        return { data: data.data || data || [], probe: "ok" as const };
      } catch (e) {
        if (e instanceof ApiError && e.status === 500) return { data: [], probe: "error" as const };
        return { data: [], probe: "unknown" as const };
      }
    },
    refetchInterval: 10000,
  });

  if (q.data?.probe === "error") {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
        <div className="flex items-center gap-2 mb-2">
          <AlertOctagon className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-bold text-slate-100">Executions endpoint unavailable</h2>
        </div>
        <p className="text-sm text-slate-300 mb-2">
          The platform cannot list executions. The backend endpoint is returning 500, which usually means the
          <code className="px-1 mx-1 rounded bg-slate-800 text-slate-200 font-mono text-xs">action_executions</code>
          table is missing or unreadable.
        </p>
        <p className="text-xs text-slate-500 font-mono mb-3">
          This blocks operator visibility into what is currently running. Engineering should investigate immediately.
        </p>
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ["exec-visibility"] })}
          className="px-3 py-1.5 rounded-md border border-surface-border text-sm text-slate-300 hover:border-slate-500"
        >
          Try again
        </button>
      </div>
    );
  }

  const items = q.data?.data || [];
  const filtered = safeArr<Execution>(items).filter((e) => {
    if (statusFilter !== "all" && deriveStatus(e) !== statusFilter) return false;
    if (search) {
      const s = safeLower(search, "");
      if (!safeLower(e.action_type, "").includes(s) && !safeLower(e.id, "").includes(s)) {
        return false;
      }
    }
    return true;
  });

  const counts = {
    total: items.length,
    running: items.filter((e) => deriveStatus(e) === "running").length,
    queued: items.filter((e) => deriveStatus(e) === "queued").length,
    completed: items.filter((e) => deriveStatus(e) === "completed").length,
    failed: items.filter((e) => deriveStatus(e) === "failed").length,
    stuck: items.filter((e) => deriveStatus(e) === "stuck").length,
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-surface-border bg-surface-card/80 backdrop-blur-md p-5 shadow-xl shadow-black/20">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-2">
              <Activity className="w-4 h-4 text-platform-400" />
              Executions
            </h2>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              {counts.total} total · {counts.running} running · {counts.queued} queued · {counts.completed} completed · {counts.failed} failed · {counts.stuck} stuck
            </p>
          </div>
        </div>
        {counts.stuck > 0 && (
          <div className="mt-3 px-3 py-2 rounded-md border border-red-500/30 bg-red-500/10 flex items-start gap-2">
            <AlertOctagon className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-red-200">
              <strong className="font-bold">{counts.stuck} execution(s) stuck.</strong> An execution is "stuck" when it has been
              running for over 1 hour with no progress. These usually indicate a crashed worker or hung downstream call.
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search executions…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-md border border-surface-border bg-surface-darker text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500"
          />
        </div>
        <div className="flex items-center gap-1 text-[10px] font-mono uppercase">
          {(["all", "running", "queued", "stuck", "failed", "completed"] as const).map((f) => (
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

      {q.isLoading ? (
        <div className="text-center py-12 text-slate-500">
          <Loader2 className="w-6 h-6 mx-auto animate-spin mb-2" />
          <div className="text-xs font-mono">Loading executions…</div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-surface-border bg-surface-card/80 p-12 text-center">
          <div className="text-sm text-slate-300 font-semibold mb-1">No executions</div>
          <div className="text-xs text-slate-500">No executions match your filters.</div>
        </div>
      ) : (
        <ul className="space-y-2">
          {filtered.map((e) => (
            <ExecutionRow key={e.id} e={e} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ExecutionRow({ e }: { e: Execution }) {
  const status = deriveStatus(e);
  const level = statusLevel(status);
  const title = e.action_type || `Execution ${e.id?.slice(0, 8)}`;

  return (
    <li className={`rounded-md border p-4 ${
      status === "stuck" ? "border-red-500/30 bg-red-500/5" :
      status === "failed" ? "border-red-500/30 bg-red-500/5" :
      status === "running" ? "border-emerald-500/30 bg-emerald-500/5" :
      status === "queued" ? "border-amber-500/30 bg-amber-500/5" :
      "border-surface-border bg-surface-card/40"
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <div className="text-sm font-semibold text-slate-100">{title}</div>
            <HealthPill level={level} size="sm" />
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">{statusLabel(status)}</span>
            {e.resource_type && (
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">· {e.resource_type}</span>
            )}
          </div>
          {e.error && <p className="text-xs text-red-300 mb-2 font-mono">{e.error}</p>}
          {e.result_summary && <p className="text-xs text-slate-400 mb-2">{e.result_summary}</p>}

          {/* Progress bar for running/queued */}
          {(status === "running" || status === "queued" || status === "stuck") && typeof e.progress_pct === "number" && (
            <div className="h-1.5 bg-surface-darker rounded-full overflow-hidden mb-2">
              <div
                className={`h-full transition-all ${
                  status === "stuck" ? "bg-red-500" :
                  status === "queued" ? "bg-amber-500" :
                  "bg-platform-500"
                }`}
                style={{ width: `${e.progress_pct}%` }}
              />
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-3 gap-y-1 text-[11px] font-mono">
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Started</div>
              <div className="text-slate-300">
                {e.started_at ? new Date(e.started_at).toLocaleString() : "—"}
              </div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Duration</div>
              <div className="text-slate-300">
                {formatDuration(e.duration_ms)}
              </div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Progress</div>
              <div className="text-slate-300">
                {typeof e.progress_pct === "number" ? `${e.progress_pct}%` : "—"}
              </div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Last update</div>
              <div className="text-slate-300">
                {e.last_progress_at ? new Date(e.last_progress_at).toLocaleString() :
                 e.updated_at ? new Date(e.updated_at).toLocaleString() : "—"}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-1.5 flex-shrink-0">
          <Link
            href={`/dashboard/executions/${e.id}`}
            className="px-3 py-1.5 rounded-md border border-surface-border text-slate-400 text-xs font-mono hover:border-slate-500 hover:text-slate-200 flex items-center gap-1.5"
          >
            DETAILS <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </li>
  );
}
