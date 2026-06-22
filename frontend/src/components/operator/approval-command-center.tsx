"use client";

/**
 * Approval Command Center — single surface for pending/approved/rejected/expired
 * approvals with inline Approve/Reject actions and risk-aware ordering.
 */

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useState, useMemo } from "react";
import {
  CheckCircle2, XCircle, AlertOctagon, Clock, Shield, Loader2,
  ChevronRight, Search, ShieldAlert, HelpCircle,
} from "lucide-react";
import { fetchApi, ApiError } from "@/lib/api";
import { HealthPill } from "./health-pill";
import { HealthLevel } from "./health";
import { safeArr, safeUpper, safeLower } from "@/lib/safe";

type ApprovalStatus = "pending" | "approved" | "rejected" | "expired" | "unknown";

interface Approval {
  id: string;
  status: string;
  risk_level?: string;
  risk_score?: number;
  summary?: string;
  title?: string;
  reason?: string;
  description?: string;
  action_type?: string;
  resource_type?: string;
  resource_id?: string;
  requested_by?: string;
  approver_id?: string;
  sla_deadline?: string;
  created_at?: string;
  requested_at?: string;
  decided_at?: string;
  expires_at?: string;
}

function deriveStatus(a: Approval): ApprovalStatus {
  const s = (a.status || "").toLowerCase();
  if (s === "pending" || s === "awaiting" || s === "open") return "pending";
  if (s === "approved" || s === "granted") return "approved";
  if (s === "rejected" || s === "denied") return "rejected";
  if (s === "expired") return "expired";
  return "unknown";
}

function statusLevel(s: ApprovalStatus): HealthLevel {
  switch (s) {
    case "pending": return "warning";
    case "approved": return "healthy";
    case "rejected": return "critical";
    case "expired": return "unknown";
    default: return "unknown";
  }
}

function statusLabel(s: ApprovalStatus): string {
  return safeUpper(s);
}

function riskLevel(a: Approval): HealthLevel {
  const r = (a.risk_level || "").toLowerCase();
  if (r === "critical" || r === "high") return "critical";
  if (r === "medium" || r === "moderate") return "warning";
  if (r === "low") return "healthy";
  return "unknown";
}

function timeUntilSLA(a: Approval): string {
  if (!a.sla_deadline) return "no deadline";
  const ms = new Date(a.sla_deadline).getTime() - Date.now();
  if (ms < 0) return "OVERDUE";
  const min = Math.floor(ms / 60000);
  if (min < 60) return `${min}m left`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h left`;
  const days = Math.floor(hr / 24);
  return `${days}d left`;
}

export function ApprovalCommandCenter() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | ApprovalStatus>("pending");

  const q = useQuery<{ data: Approval[]; probe: "ok" | "error" | "unknown" }>({
    queryKey: ["acc-approvals"],
    queryFn: async () => {
      try {
        const data = await fetchApi<any>("/approvals?limit=100");
        return { data: data.data || data || [], probe: "ok" as const };
      } catch (e) {
        if (e instanceof ApiError && e.status === 500) return { data: [], probe: "error" as const };
        return { data: [], probe: "unknown" as const };
      }
    },
    refetchInterval: 10000,
  });

  const approveMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      fetchApi(`/approvals/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ reason: reason || "Approved via operator command center" }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["acc-approvals"] }),
  });

  const rejectMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      fetchApi(`/approvals/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: reason || "Rejected via operator command center" }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["acc-approvals"] }),
  });

  if (q.data?.probe === "error") {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
        <div className="flex items-center gap-2 mb-2">
          <XCircle className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-bold text-slate-100">Approvals endpoint unavailable</h2>
        </div>
        <p className="text-sm text-slate-300 mb-2">
          Cannot load pending approvals. The backend endpoint is returning 500.
        </p>
        <p className="text-xs text-slate-500 font-mono mb-3">
          This blocks operator decision-making. Engineering should investigate immediately.
        </p>
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ["acc-approvals"] })}
          className="px-3 py-1.5 rounded-md border border-surface-border text-sm text-slate-300 hover:border-slate-500"
        >
          Try again
        </button>
      </div>
    );
  }

  const items = q.data?.data || [];
  const filtered = safeArr<Approval>(items).filter((a) => {
    if (statusFilter !== "all" && deriveStatus(a) !== statusFilter) return false;
    if (search && !safeLower(a.summary || a.title, "").includes(safeLower(search, ""))) return false;
    return true;
  });

  // Sort: pending first by risk, then by SLA
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const sa = deriveStatus(a);
      const sb = deriveStatus(b);
      if (sa === "pending" && sb !== "pending") return -1;
      if (sb === "pending" && sa !== "pending") return 1;
      if (sa === "pending" && sb === "pending") {
        const ra = riskLevel(a);
        const rb = riskLevel(b);
        if (ra !== rb) {
          const order = { critical: 0, warning: 1, healthy: 2, unknown: 3 };
          return order[ra] - order[rb];
        }
      }
      return 0;
    });
  }, [filtered]);

  const counts = {
    total: items.length,
    pending: items.filter((a) => deriveStatus(a) === "pending").length,
    approved: items.filter((a) => deriveStatus(a) === "approved").length,
    rejected: items.filter((a) => deriveStatus(a) === "rejected").length,
    expired: items.filter((a) => deriveStatus(a) === "expired").length,
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-surface-border bg-surface-card/80 backdrop-blur-md p-5 shadow-xl shadow-black/20">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-2">
              <Shield className="w-4 h-4 text-platform-400" />
              Approvals
            </h2>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              {counts.total} total · {counts.pending} pending · {counts.approved} approved · {counts.rejected} rejected
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search approvals…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-md border border-surface-border bg-surface-darker text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500"
          />
        </div>
        <div className="flex items-center gap-1 text-[10px] font-mono uppercase">
          {(["pending", "approved", "rejected", "expired", "all"] as const).map((f) => (
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
          <div className="text-xs font-mono">Loading approvals…</div>
        </div>
      ) : sorted.length === 0 ? (
        <div className="rounded-xl border border-surface-border bg-surface-card/80 p-12 text-center">
          <div className="text-sm text-slate-300 font-semibold mb-1">
            {statusFilter === "pending" ? "No pending approvals" : `No ${statusFilter} approvals`}
          </div>
          <div className="text-xs text-slate-500">
            {statusFilter === "pending" ? "The queue is clear." : "Try a different filter."}
          </div>
        </div>
      ) : (
        <ul className="space-y-2">
          {sorted.map((a) => (
            <ApprovalRow
              key={a.id}
              a={a}
              onApprove={(reason) => approveMut.mutate({ id: a.id, reason })}
              onReject={(reason) => rejectMut.mutate({ id: a.id, reason })}
              approving={approveMut.isPending && approveMut.variables?.id === a.id}
              rejecting={rejectMut.isPending && rejectMut.variables?.id === a.id}
              lastError={
                approveMut.error && approveMut.variables?.id === a.id ? String(approveMut.error) :
                rejectMut.error && rejectMut.variables?.id === a.id ? String(rejectMut.error) :
                null
              }
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function ApprovalRow({ a, onApprove, onReject, approving, rejecting, lastError }: {
  a: Approval;
  onApprove: (reason?: string) => void;
  onReject: (reason?: string) => void;
  approving: boolean;
  rejecting: boolean;
  lastError: string | null;
}) {
  const status = deriveStatus(a);
  const level = statusLevel(status);
  const rLevel = riskLevel(a);
  const title = a.summary || a.title || a.description || "Approval awaiting decision";
  const pending = status === "pending";

  return (
    <li className={`rounded-md border p-4 ${
      status === "pending" && rLevel === "critical" ? "border-red-500/30 bg-red-500/5" :
      status === "pending" ? "border-amber-500/30 bg-amber-500/5" :
      "border-surface-border bg-surface-card/40"
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <div className="text-sm font-semibold text-slate-100">{title}</div>
            <HealthPill level={level} size="sm" />
            {pending && rLevel !== "unknown" && (
              <span className={`text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded ${
                rLevel === "critical" ? "bg-red-500/20 text-red-300 border border-red-500/30" :
                "bg-amber-500/20 text-amber-300 border border-amber-500/30"
              }`}>
                <ShieldAlert className="w-2.5 h-2.5 inline mr-0.5" />
                {a.risk_level || "unknown"} risk
              </span>
            )}
            {a.action_type && (
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">· {a.action_type}</span>
            )}
          </div>
          {a.reason && <p className="text-xs text-slate-400 mb-2">{a.reason}</p>}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-3 gap-y-1 text-[11px] font-mono">
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Status</div>
              <div className="text-slate-300">{statusLabel(status)}</div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">SLA</div>
              <div className={timeUntilSLA(a) === "OVERDUE" ? "text-red-300" : "text-slate-300"}>
                {timeUntilSLA(a)}
              </div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Requested</div>
              <div className="text-slate-300">
                {a.requested_at || a.created_at ? new Date(a.requested_at || a.created_at!).toLocaleString() : "—"}
              </div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Decided</div>
              <div className="text-slate-300">
                {a.decided_at ? new Date(a.decided_at).toLocaleString() : "—"}
              </div>
            </div>
          </div>

          {lastError && (
            <div className="mt-2 text-[11px] text-red-300 font-mono bg-red-500/10 border border-red-500/20 rounded px-2 py-1">
              Action failed: {lastError}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1.5 flex-shrink-0">
          {pending && (
            <>
              <button
                onClick={() => onApprove()}
                disabled={approving || rejecting}
                className="px-3 py-1.5 rounded-md border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs font-mono font-bold hover:bg-emerald-500/20 disabled:opacity-50 flex items-center gap-1.5"
              >
                {approving ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                APPROVE
              </button>
              <button
                onClick={() => onReject()}
                disabled={approving || rejecting}
                className="px-3 py-1.5 rounded-md border border-red-500/30 bg-red-500/10 text-red-300 text-xs font-mono font-bold hover:bg-red-500/20 disabled:opacity-50 flex items-center gap-1.5"
              >
                {rejecting ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
                REJECT
              </button>
            </>
          )}
          <Link
            href={`/dashboard/approvals/${a.id}`}
            className="px-3 py-1.5 rounded-md border border-surface-border text-slate-400 text-xs font-mono hover:border-slate-500 hover:text-slate-200 flex items-center gap-1.5"
          >
            DETAILS <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </li>
  );
}
