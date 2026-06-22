"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ScrollText,
  Filter,
  ChevronLeft,
  ChevronRight,
  Loader2,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowRightLeft,
  Shield,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuditEntry {
  id: string;
  action_name: string;
  actor_id: string;
  actor_type: string;
  target_type: string;
  target_id: string;
  summary: string;
  decision: string | null;
  risk_level: string;
  ip_address: string | null;
  user_agent: string | null;
  semantic_hash: string;
  immutable_at: string;
  created_at: string;
}

interface AuditResponse {
  success: boolean;
  data: AuditEntry[];
  meta: { total: number; limit: number; offset: number };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ENTITY_TYPES = [
  { value: "", label: "All Entities" },
  { value: "client", label: "Clients" },
  { value: "campaign", label: "Campaigns" },
  { value: "approval", label: "Approvals" },
  { value: "credential", label: "Credentials" },
];

const ACTION_TYPES = [
  { value: "", label: "All Actions" },
  { value: "client.create", label: "Client Create" },
  { value: "client.update", label: "Client Update" },
  { value: "client.archive", label: "Client Archive" },
  { value: "client.restore", label: "Client Restore" },
  { value: "campaign.create", label: "Campaign Create" },
  { value: "campaign.launch", label: "Campaign Launch" },
  { value: "campaign.pause", label: "Campaign Pause" },
  { value: "campaign.resume", label: "Campaign Resume" },
  { value: "campaign.archive", label: "Campaign Archive" },
  { value: "campaign.delete", label: "Campaign Delete" },
  { value: "approval.approved", label: "Approval" },
  { value: "approval.rejected", label: "Rejection" },
  { value: "credential.create", label: "Credential Create" },
  { value: "credential.update", label: "Credential Update" },
  { value: "credential.delete", label: "Credential Delete" },
  { value: "credential.lock", label: "Credential Lock" },
  { value: "credential.unlock", label: "Credential Unlock" },
];

function riskBadge(risk: string) {
  if (risk === "high") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-red-500/10 text-red-400">
        <XCircle size={11} />
        High
      </span>
    );
  }
  if (risk === "medium") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400">
        <AlertTriangle size={11} />
        Medium
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">
      <CheckCircle2 size={11} />
      Low
    </span>
  );
}

function actionIcon(action: string) {
  if (action.includes("create")) return <CheckCircle2 size={14} className="text-emerald-400" />;
  if (action.includes("delete") || action.includes("archive")) return <XCircle size={14} className="text-red-400" />;
  if (action.includes("approve")) return <CheckCircle2 size={14} className="text-emerald-400" />;
  if (action.includes("reject")) return <XCircle size={14} className="text-red-400" />;
  if (action.includes("lock")) return <Shield size={14} className="text-amber-400" />;
  if (action.includes("unlock")) return <Shield size={14} className="text-emerald-400" />;
  return <ArrowRightLeft size={14} className="text-slate-400" />;
}

function formatTimestamp(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function truncateId(id: string) {
  return id.slice(0, 8);
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 25;

  // Filters
  const [entityFilter, setEntityFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [sinceDate, setSinceDate] = useState("");
  const [untilDate, setUntilDate] = useState("");

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      params.set("offset", String(offset));
      if (entityFilter) params.set("target_type", entityFilter);
      if (actionFilter) params.set("action_name", actionFilter);
      if (sinceDate) params.set("since", new Date(sinceDate).toISOString());
      if (untilDate) params.set("until", new Date(untilDate + "T23:59:59").toISOString());

      const qs = params.toString();
      const result = await fetchApi<AuditResponse>(`/audit/ledger?${qs}`);
      setEntries(Array.isArray(result.data) ? result.data : []);
      setTotal(result.meta?.total ?? 0);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load audit log";
      setError(msg);
      toast.error("Audit log error", { description: msg });
    } finally {
      setLoading(false);
    }
  }, [offset, entityFilter, actionFilter, sinceDate, untilDate]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const resetFilters = () => {
    setEntityFilter("");
    setActionFilter("");
    setSinceDate("");
    setUntilDate("");
    setOffset(0);
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight flex items-center gap-3">
            <ScrollText className="w-8 h-8 text-platform-400" />
            Audit Log
          </h1>
          <p className="text-slate-400 mt-1">Immutable record of all platform actions for compliance and forensics.</p>
        </div>
        <button
          onClick={() => fetchEntries()}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-surface-card border border-surface-border rounded-md text-sm text-slate-300 hover:text-slate-100 hover:bg-surface-darker transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="glass-panel p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter size={16} className="text-slate-400" />
          <span className="text-sm font-medium text-slate-300">Filters</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <select
            value={entityFilter}
            onChange={(e) => { setEntityFilter(e.target.value); setOffset(0); }}
            className="bg-surface-darker border border-surface-border rounded-md py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-platform-500/50"
          >
            {ENTITY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>

          <select
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value); setOffset(0); }}
            className="bg-surface-darker border border-surface-border rounded-md py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-platform-500/50"
          >
            {ACTION_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>

          <input
            type="date"
            value={sinceDate}
            onChange={(e) => { setSinceDate(e.target.value); setOffset(0); }}
            placeholder="Since"
            className="bg-surface-darker border border-surface-border rounded-md py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-platform-500/50"
          />

          <input
            type="date"
            value={untilDate}
            onChange={(e) => { setUntilDate(e.target.value); setOffset(0); }}
            placeholder="Until"
            className="bg-surface-darker border border-surface-border rounded-md py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-platform-500/50"
          />

          <button
            onClick={resetFilters}
            className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 border border-surface-border rounded-md hover:bg-surface-darker transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="glass-panel overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-platform-400" />
            <span className="ml-3 text-sm text-slate-400">Loading audit entries...</span>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-16">
            <AlertTriangle className="w-6 h-6 text-red-400" />
            <span className="ml-3 text-sm text-red-400">{error}</span>
          </div>
        ) : entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <ScrollText className="w-10 h-10 mb-3 opacity-40" />
            <p className="text-sm">No audit entries found.</p>
            <p className="text-xs mt-1">Actions performed on the platform will appear here.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="text-left px-4 py-3 font-medium text-slate-400 text-xs uppercase tracking-wider">Timestamp</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-400 text-xs uppercase tracking-wider">Actor</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-400 text-xs uppercase tracking-wider">Action</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-400 text-xs uppercase tracking-wider">Entity</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-400 text-xs uppercase tracking-wider">Risk</th>
                  <th className="text-left px-4 py-3 font-medium text-slate-400 text-xs uppercase tracking-wider">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-surface-darker/50 transition-colors">
                    <td className="px-4 py-3 text-slate-300 whitespace-nowrap font-mono text-xs">
                      {formatTimestamp(entry.immutable_at)}
                    </td>
                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-surface-border flex items-center justify-center text-[10px] font-medium text-slate-300">
                          {entry.actor_type === "system" ? "SYS" : truncateId(entry.actor_id)}
                        </span>
                        <span className="text-xs">{entry.actor_type}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {actionIcon(entry.action_name)}
                        <span className="text-slate-200 font-medium">{entry.action_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                      <span className="text-xs">{entry.target_type}</span>
                      <span className="text-slate-600 mx-1">/</span>
                      <span className="font-mono text-xs">{truncateId(entry.target_id)}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {riskBadge(entry.risk_level)}
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate text-xs">
                      {entry.summary}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > limit && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-surface-border">
            <span className="text-xs text-slate-500">
              Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setOffset((o) => Math.max(0, o - limit))}
                disabled={offset === 0}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-surface-darker disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-xs text-slate-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setOffset((o) => Math.min((totalPages - 1) * limit, o + limit))}
                disabled={currentPage >= totalPages}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-surface-darker disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
