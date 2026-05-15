"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Filter, Activity, Loader2, X, Clock, ChevronDown, ChevronRight,
  Play, CheckCircle2, XCircle, AlertCircle,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface TracePhase {
  name: string;
  status: string;
  started_at: string;
  duration_ms: number;
}

interface TraceEntry {
  workflow_id: string;
  type: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_ms: number;
  task_queue: string;
  phases: TracePhase[];
}

const WORKFLOW_TYPES = [
  "OnboardingWorkflow",
  "KeywordResearchWorkflow",
  "BacklinkCampaignWorkflow",
  "CitationSubmissionWorkflow",
  "ReportGenerationWorkflow",
];

const STATUS_OPTIONS = ["running", "completed", "failed"];

const STATUS_BADGE: Record<string, string> = {
  running: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
};

const PHASE_ICONS: Record<string, React.ReactNode> = {
  running: <Play className="w-3 h-3 text-blue-400" />,
  completed: <CheckCircle2 className="w-3 h-3 text-emerald-400" />,
  failed: <XCircle className="w-3 h-3 text-red-400" />,
  waiting: <AlertCircle className="w-3 h-3 text-amber-400" />,
};

function getDurationColor(ms: number): string {
  if (ms < 10000) return "bg-emerald-500";
  if (ms < 60000) return "bg-amber-500";
  return "bg-red-500";
}

function getDurationTextColor(ms: number): string {
  if (ms < 10000) return "text-emerald-400";
  if (ms < 60000) return "text-amber-400";
  return "text-red-400";
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

export default function TracesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const { data: traces = [], isLoading } = useQuery<TraceEntry[]>({
    queryKey: ["workflow-traces", MOCK_TENANT_ID],
    queryFn: async () => {
      const data = await fetchApi<{ workflows: TraceEntry[] }>(`/realtime/workflows/${MOCK_TENANT_ID}`);
      return data.workflows ?? [];
    },
    refetchInterval: 5000,
  });

  const filteredTraces = useMemo(() => {
    return traces.filter((t) => {
      if (searchQuery && !t.workflow_id.toLowerCase().includes(searchQuery.toLowerCase()) && !t.type.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (typeFilter !== "all" && t.type !== typeFilter) return false;
      if (statusFilter !== "all" && t.status !== statusFilter) return false;
      return true;
    });
  }, [traces, searchQuery, typeFilter, statusFilter]);

  const maxDuration = useMemo(() => {
    return Math.max(...traces.map((t) => t.duration_ms), 1);
  }, [traces]);

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">TRACE_EXPLORER</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Distributed Workflow Execution Traces</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 font-mono">{traces.length} traces</span>
          <div className="flex gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search trace ID or type..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-56 pl-10 pr-4 py-2 bg-surface-darker border border-surface-border rounded-lg text-slate-200 placeholder-slate-500 text-sm font-mono focus:outline-none focus:border-platform-500"
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-2 border rounded-lg text-sm font-mono flex items-center gap-2 transition-colors ${
                showFilters || typeFilter !== "all" || statusFilter !== "all"
                  ? "bg-platform-500/10 border-platform-500/30 text-platform-400"
                  : "bg-surface-darker border-surface-border text-slate-400"
              }`}
            >
              <Filter className="w-4 h-4" />
              FILTERS
              {(typeFilter !== "all" || statusFilter !== "all") && (
                <span className="w-2 h-2 rounded-full bg-platform-500"></span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Filter Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="glass-panel p-4 flex flex-wrap items-center gap-6">
              <div>
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1.5">Workflow Type</label>
                <div className="flex gap-2">
                  {["all", ...WORKFLOW_TYPES].map((type) => (
                    <button
                      key={type}
                      onClick={() => setTypeFilter(type)}
                      className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                        typeFilter === type
                          ? "bg-platform-500/10 border-platform-500/30 text-platform-400"
                          : "bg-surface-darker border-surface-border text-slate-500 hover:text-slate-300"
                      }`}
                    >
                      {type === "all" ? "ALL" : type.replace("Workflow", "").replace(/([A-Z])/g, " $1").trim().toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1.5">Status</label>
                <div className="flex gap-2">
                  {["all", ...STATUS_OPTIONS].map((s) => (
                    <button
                      key={s}
                      onClick={() => setStatusFilter(s)}
                      className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                        statusFilter === s
                          ? "bg-platform-500/10 border-platform-500/30 text-platform-400"
                          : "bg-surface-darker border-surface-border text-slate-500 hover:text-slate-300"
                      }`}
                    >
                      {s.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Traces Table */}
      <div className="flex-1 glass-panel overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left font-mono">
            <thead className="text-xs text-slate-400 bg-surface-darker border-b border-surface-border sticky top-0">
              <tr>
                <th className="px-6 py-4 font-medium uppercase tracking-wider w-8"></th>
                <th className="px-6 py-4 font-medium uppercase tracking-wider">Workflow ID</th>
                <th className="px-6 py-4 font-medium uppercase tracking-wider">Type</th>
                <th className="px-6 py-4 font-medium uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 font-medium uppercase tracking-wider">Started</th>
                <th className="px-6 py-4 font-medium uppercase tracking-wider text-right">Duration</th>
                <th className="px-6 py-4 font-medium uppercase tracking-wider">Timeline</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-16 text-center">
                    <Loader2 className="w-8 h-8 text-platform-500 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : filteredTraces.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-4">
                        <Activity className="text-slate-600" size={32} />
                      </div>
                      <h3 className="text-lg font-medium text-slate-300 font-mono">No Traces Found</h3>
                      <p className="text-sm text-slate-500 mt-2">Try adjusting your filters or wait for workflow executions.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredTraces.map((trace) => {
                  const isExpanded = expandedTrace === trace.workflow_id;
                  return (
                    <tr key={trace.workflow_id}>
                      <td className="px-6 py-3">
                        <button
                          onClick={() => setExpandedTrace(isExpanded ? null : trace.workflow_id)}
                          className="text-slate-500 hover:text-slate-300"
                        >
                          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </button>
                      </td>
                      <td className="px-6 py-3">
                        <span className="text-platform-400 text-xs">{trace.workflow_id.slice(0, 12)}...</span>
                      </td>
                      <td className="px-6 py-3">
                        <span className="text-slate-200 text-xs">{trace.type.replace("Workflow", "").replace(/([A-Z])/g, " $1").trim()}</span>
                      </td>
                      <td className="px-6 py-3">
                        <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded border ${STATUS_BADGE[trace.status] || "bg-slate-500/10 text-slate-400 border-slate-500/20"}`}>
                          {trace.status}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-xs text-slate-500">
                        {new Date(trace.started_at).toLocaleTimeString()}
                      </td>
                      <td className={`px-6 py-3 text-right text-xs font-bold font-mono ${getDurationTextColor(trace.duration_ms)}`}>
                        {formatDuration(trace.duration_ms)}
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex items-center gap-1">
                          <div className="w-32 h-2 bg-surface-darker rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(trace.duration_ms / Math.max(maxDuration, 1)) * 100}%` }}
                              className={`h-full rounded-full ${getDurationColor(trace.duration_ms)}`}
                              transition={{ duration: 0.5 }}
                            />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Expanded phase details */}
        <AnimatePresence>
          {expandedTrace && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="border-t border-surface-border overflow-hidden"
            >
              <div className="p-6 bg-surface-darker/30">
                {(() => {
                  const trace = traces.find((t) => t.workflow_id === expandedTrace);
                  if (!trace) return null;
                  const maxPhaseDuration = Math.max(...trace.phases.map((p) => p.duration_ms), 1);
                  return (
                    <div className="space-y-3">
                      <h4 className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-3">PHASE WATERFALL</h4>
                      {trace.phases.map((phase, i) => (
                        <div key={phase.name} className="flex items-center gap-4">
                          <div className="flex items-center gap-2 w-40">
                            {PHASE_ICONS[phase.status] || <Clock className="w-3 h-3 text-slate-500" />}
                            <span className="text-xs text-slate-400 truncate">{phase.name.replace(/_/g, " ")}</span>
                          </div>
                          <div className="flex-1 h-5 bg-surface-darker rounded overflow-hidden flex items-center">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${(phase.duration_ms / Math.max(maxPhaseDuration, 1)) * 100}%` }}
                              className={`h-full rounded ${getDurationColor(phase.duration_ms)} opacity-80`}
                              transition={{ duration: 0.5, delay: i * 0.05 }}
                            />
                          </div>
                          <span className={`text-[10px] font-mono w-16 text-right ${getDurationTextColor(phase.duration_ms)}`}>
                            {formatDuration(phase.duration_ms)}
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Duration legend */}
      <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> &lt;10s</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-500"></span> 10-60s</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-500"></span> &gt;60s</span>
      </div>
    </div>
  );
}
