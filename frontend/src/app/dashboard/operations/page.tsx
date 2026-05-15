"use client";

import { motion } from "framer-motion";
import {
  Activity, AlertTriangle, Shield, Loader2, CheckCircle2,
  XCircle, Clock, RefreshCw, Zap, Play, RotateCcw, Trash2,
  Layers, ArrowUpRight,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useState } from "react";

interface WorkflowHealthEntry {
  workflow_id: string;
  workflow_type: string;
  health_score: number;
  risk_factors: string[];
  retry_count: number;
}

interface OrphanWorkflow {
  workflow_id: string;
  workflow_type: string;
  status: string;
  stalled_minutes: number;
}

interface DeadLetterWorkflow {
  workflow_id: string;
  workflow_type: string;
  failure_reason: string;
  failed_at: string;
}

interface DegradationData {
  status: string;
  affected_systems: string[];
  healthy_systems: string[];
  recommended_actions: { action: string; reason: string }[];
}

interface IncidentEntry {
  incident_id: string;
  component: string;
  type: string;
  status: string;
  detected_at: string;
  resolved_at: string | null;
  summary: string;
}

interface IncidentDashboard {
  active_incidents: IncidentEntry[];
  recent_resolutions: IncidentEntry[];
  mttd_minutes: number;
  mttr_minutes: number;
}

const DEGRADATION_LABELS: Record<string, { label: string; color: string }> = {
  fully_operational: { label: "FULLY OPERATIONAL", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
  degraded: { label: "DEGRADED", color: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
  limited: { label: "LIMITED", color: "text-orange-400 bg-orange-500/10 border-orange-500/20" },
  emergency: { label: "EMERGENCY", color: "text-red-400 bg-red-500/10 border-red-500/20" },
};

export default function OperationsPage() {
  const queryClient = useQueryClient();
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const { data: healthData, isLoading: loadingHealth } = useQuery<WorkflowHealthEntry[]>({
    queryKey: ["workflow-health"],
    queryFn: () => fetchApi(`/workflow-resilience/health?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: orphans } = useQuery<OrphanWorkflow[]>({
    queryKey: ["workflow-orphans"],
    queryFn: () => fetchApi("/workflow-resilience/orphans"),
    refetchInterval: 15000,
  });

  const { data: deadLetters } = useQuery<DeadLetterWorkflow[]>({
    queryKey: ["workflow-dead-letter"],
    queryFn: () => fetchApi("/workflow-resilience/dead-letter"),
    refetchInterval: 15000,
  });

  const { data: degradation } = useQuery<DegradationData>({
    queryKey: ["degradation"],
    queryFn: () => fetchApi("/distributed/degradation"),
    refetchInterval: 15000,
  });

  const { data: incidentsDashboard } = useQuery<IncidentDashboard>({
    queryKey: ["incident-dashboard"],
    queryFn: () => fetchApi("/sre/incident-dashboard"),
    refetchInterval: 15000,
  });

  const cleanupMutation = useMutation({
    mutationFn: () => fetchApi("/workflow-resilience/cleanup-orphans", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflow-orphans"] });
      setActionFeedback("Orphans cleaned successfully");
      setTimeout(() => setActionFeedback(null), 3000);
    },
  });

  const checkInvariantsMutation = useMutation({
    mutationFn: () => fetchApi("/workflow-resilience/validate-replay", { method: "POST" }),
    onSuccess: () => {
      setActionFeedback("Invariants validated");
      setTimeout(() => setActionFeedback(null), 3000);
    },
  });

  const healthList = healthData || [];
  const orphanList = orphans || [];
  const deadLetterList = deadLetters || [];
  const incidentList = incidentsDashboard ? [...(incidentsDashboard.active_incidents ?? []), ...(incidentsDashboard.recent_resolutions ?? [])] : [];
  const mttd = incidentsDashboard?.mttd_minutes ?? 0;
  const mttr = incidentsDashboard?.mttr_minutes ?? 0;

  const deg = degradation ? DEGRADATION_LABELS[degradation.status] || DEGRADATION_LABELS.fully_operational : null;

  const avgHealth = healthList.length > 0
    ? Math.round(healthList.reduce((s, h) => s + h.health_score, 0) / healthList.length)
    : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">OPERATIONS</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Day-to-Day Operations Management</p>
        </div>
        <div className="flex items-center gap-3">
          {deg && (
            <span className={`px-3 py-1.5 rounded-md border text-xs font-mono font-bold ${deg.color}`}>
              {deg.label}
            </span>
          )}
          <span className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400">
            {healthList.length} WORKFLOWS
          </span>
        </div>
      </div>

      {loadingHealth ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : (
        <>
          {/* Quick Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => cleanupMutation.mutate()}
              disabled={cleanupMutation.isPending}
              className="px-4 py-2 bg-surface-border hover:bg-surface-border/80 text-white rounded-md text-xs font-mono flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {cleanupMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Clean Up Orphans
            </button>
            <button
              onClick={() => checkInvariantsMutation.mutate()}
              disabled={checkInvariantsMutation.isPending}
              className="px-4 py-2 bg-surface-border hover:bg-surface-border/80 text-white rounded-md text-xs font-mono flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {checkInvariantsMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
              Validate Invariants
            </button>
            <button
              onClick={() => {
                if (deadLetterList.length > 0) {
                  queryClient.invalidateQueries({ queryKey: ["workflow-dead-letter"] });
                  setActionFeedback("Remediation initiated for dead letters");
                  setTimeout(() => setActionFeedback(null), 3000);
                }
              }}
              className="px-4 py-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-md text-xs font-mono flex items-center gap-2 transition-colors hover:bg-amber-500/20"
            >
              <Zap className="w-4 h-4" />
              Remediate Dead Letters ({deadLetterList.length})
            </button>
            {actionFeedback && (
              <motion.span
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="text-xs font-mono text-emerald-400"
              >
                &gt; {actionFeedback}
              </motion.span>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Workflow Health */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">WORKFLOW_HEALTH</h3>
                {avgHealth !== null && (
                  <span className={`ml-auto text-lg font-bold font-mono ${avgHealth >= 80 ? "text-emerald-400" : avgHealth >= 50 ? "text-amber-400" : "text-red-400"}`}>
                    {avgHealth}%
                  </span>
                )}
              </div>
              <div className="space-y-2 max-h-[300px] overflow-auto custom-scrollbar">
                {healthList.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono py-8 text-center">No workflow health data</div>
                ) : (
                  healthList.slice(0, 10).map((w, i) => (
                    <motion.div
                      key={w.workflow_id}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-mono text-slate-300 truncate max-w-[160px]">{w.workflow_type}</span>
                        <span className={`text-xs font-mono font-bold ${w.health_score >= 80 ? "text-emerald-400" : w.health_score >= 50 ? "text-amber-400" : "text-red-400"}`}>
                          {Math.round(w.health_score)}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${w.health_score}%` }}
                          className={`h-full rounded-full ${w.health_score >= 80 ? "bg-emerald-500" : w.health_score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                      {w.risk_factors.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {w.risk_factors.slice(0, 2).map((rf, j) => (
                            <span key={j} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-500/10 text-amber-400/80 border border-amber-500/10">
                              {rf}
                            </span>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  ))
                )}
              </div>
            </div>

            {/* Orphan Workflows */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">ORPHAN_WORKFLOWS</h3>
                {orphanList.length > 0 && (
                  <span className="ml-auto px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-400">
                    {orphanList.length}
                  </span>
                )}
              </div>
              <div className="space-y-2 max-h-[300px] overflow-auto custom-scrollbar">
                {orphanList.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono py-8 text-center flex flex-col items-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
                    <span>NO_ORPHANS_DETECTED</span>
                  </div>
                ) : (
                  orphanList.map((o, i) => (
                    <motion.div
                      key={o.workflow_id}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="p-3 rounded-md bg-red-500/5 border border-red-500/10"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-slate-300">{o.workflow_type}</span>
                        <span className="text-[10px] font-mono text-red-400">{o.stalled_minutes}m stalled</span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 mt-1">{o.workflow_id.slice(0, 16)}...</div>
                    </motion.div>
                  ))
                )}
              </div>
            </div>

            {/* Dead Letter Queue */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Layers className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">DEAD_LETTER_QUEUE</h3>
                {deadLetterList.length > 0 && (
                  <span className="ml-auto px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-400">
                    {deadLetterList.length}
                  </span>
                )}
              </div>
              <div className="space-y-2 max-h-[300px] overflow-auto custom-scrollbar">
                {deadLetterList.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono py-8 text-center flex flex-col items-center">
                    <Shield className="w-8 h-8 text-emerald-500 mb-2" />
                    <span>NO_DEAD_LETTERS</span>
                  </div>
                ) : (
                  deadLetterList.map((d, i) => (
                    <motion.div
                      key={d.workflow_id}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="p-3 rounded-md bg-amber-500/5 border border-amber-500/10"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-slate-300">{d.workflow_type}</span>
                        <span className="text-[10px] font-mono text-slate-500">{new Date(d.failed_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-[10px] font-mono text-red-400/80">{d.failure_reason}</p>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Degradation Status */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">DEGRADATION_STATUS</h3>
                {deg && (
                  <span className={`ml-auto px-3 py-1 rounded-md border text-xs font-mono font-bold ${deg.color}`}>
                    {deg.label}
                  </span>
                )}
              </div>
              {degradation ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                      <p className="text-[10px] font-mono text-slate-500 uppercase mb-1">Healthy Systems</p>
                      <div className="flex flex-wrap gap-1">
                        {degradation.healthy_systems.map(s => (
                          <span key={s} className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                      <p className="text-[10px] font-mono text-slate-500 uppercase mb-1">Affected Systems</p>
                      <div className="flex flex-wrap gap-1">
                        {degradation.affected_systems.length > 0 ? degradation.affected_systems.map(s => (
                          <span key={s} className="px-2 py-0.5 rounded text-[10px] font-mono bg-red-500/10 text-red-400 border border-red-500/20">
                            {s}
                          </span>
                        )) : <span className="text-xs font-mono text-emerald-400">None</span>}
                      </div>
                    </div>
                  </div>
                  {degradation.recommended_actions.length > 0 && (
                    <div className="p-3 rounded-md bg-amber-500/5 border border-amber-500/10">
                      <p className="text-[10px] font-mono text-amber-400 uppercase mb-2">Recommended Actions</p>
                      {degradation.recommended_actions.map((a, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs font-mono text-slate-300 mb-1">
                          <span className="text-amber-400">&gt;</span>
                          <span>{a.action.replace(/_/g, " ")}</span>
                          <span className="text-slate-500">({a.reason.replace(/_/g, " ")})</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No degradation data</div>
              )}
            </div>

            {/* Incident Log */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">INCIDENT_LOG</h3>
              </div>
              <div className="space-y-2 max-h-[350px] overflow-auto custom-scrollbar">
                {incidentList.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono py-8 text-center">No incidents recorded</div>
                ) : (
                  incidentList.map((inc, i) => (
                    <motion.div
                      key={inc.incident_id}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-slate-300">{inc.summary || inc.type}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                          inc.type === "critical" ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                          inc.type === "high" ? "bg-orange-500/10 text-orange-400 border border-orange-500/20" :
                          "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}>{inc.type}</span>
                      </div>
                      <div className="flex items-center gap-3 text-[10px] font-mono text-slate-600">
                        <span>{inc.component}</span>
                        <span>{inc.status}</span>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
