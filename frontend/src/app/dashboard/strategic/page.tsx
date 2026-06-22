"use client";

import { motion } from "framer-motion";
import {
  FileText, BrainCircuit, Building2, ListChecks, AlertTriangle,
  Loader2, Shield,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { safeArr, safeNum, safeStr, safeUpper, safeReplace, safeObj } from "@/lib/safe";

interface KeyMetrics {
  total_campaigns?: number;
  active_workflows?: number;
  active_workers?: number;
  total_workers?: number;
  failed_workflows?: number;
  time_window_hours?: number;
  [key: string]: number | undefined;
}

interface OperationalSummary {
  key_metrics: KeyMetrics;
  notable_events: Array<string | Record<string, unknown>>;
  recommended_focus: string[];
  narrative?: string;
}

interface StrategicAction {
  action: string;
  impact?: string;
  priority: string;
  category?: string;
}

interface StrategicContext {
  active_campaigns: Array<{ id: string; name: string; status: string; acquired_links: number; target_links: number; health_score: number }> | number;
  pending_approvals: Array<{ id: string; type: string; summary: string }> | number;
  infra_health: { overall_status: string; congested_queues?: unknown[]; degraded_components?: unknown[] };
  ongoing_anomalies?: unknown[];
  strategic_actions: StrategicAction[];
}

interface CampaignPerformance {
  name: string;
  campaign?: string;  // legacy alias
  score?: number;
  completion_pct?: number;
  trend?: string;
  reply_rate?: number;
  acquired_links?: number;
  target_links?: number;
}

interface WorkflowReliability {
  workflow?: string;
  queue?: string;
  reliability?: number;
  congestion_level?: string;
  depth?: number;
  worker_count?: number;
}

interface OrganizationIntelligence {
  campaign_performance: CampaignPerformance[];
  workflow_reliability: WorkflowReliability[];
}

interface PrioritizedAction {
  priority: string;
  action: string;
  category: string;
  impact: string;
}

interface PredictiveAlert {
  id: string;
  type: string;
  severity: string;
  component: string;
  message: string;
  probability: number;
  predicted_at: string;
}

interface PredictiveDashboard {
  predicted_anomalies: PredictiveAlert[];
}

const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.4 },
};

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const PRIORITY_BADGE: Record<string, string> = {
  P0: "bg-red-500/10 text-red-400 border-red-500/20",
  P1: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  P2: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  P3: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  low: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

function probColor(p: number): string {
  const n = safeNum(p);
  if (n >= 0.7) return "bg-emerald-500";
  if (n >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

function probTextColor(p: number): string {
  const n = safeNum(p);
  if (n >= 0.7) return "text-emerald-400";
  if (n >= 0.4) return "text-amber-400";
  return "text-red-400";
}

export default function StrategicPage() {
  const { data: summary, isLoading: loadingSummary, isError: errorSummary } = useQuery<OperationalSummary>({
    queryKey: ["strategic-summary"],
    queryFn: () => fetchApi(`/enterprise-cognition/summary?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: strategicContext, isLoading: loadingContext, isError: errorContext } = useQuery<StrategicContext>({
    queryKey: ["strategic-context"],
    queryFn: () => fetchApi(`/enterprise-cognition/strategic-context?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: orgIntelligence, isLoading: loadingOrg, isError: errorOrg } = useQuery<OrganizationIntelligence>({
    queryKey: ["strategic-org-intel", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/enterprise-cognition/organization-intelligence?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: prioritized, isLoading: loadingActions, isError: errorActions } = useQuery<PrioritizedAction[]>({
    queryKey: ["strategic-prioritized", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/operational-assistant/prioritize?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: predictiveDashboard, isLoading: loadingPredictive, isError: errorPredictive } = useQuery<PredictiveDashboard>({
    queryKey: ["predictive-dashboard"],
    queryFn: () => fetchApi("/anomaly-prediction/dashboard"),
    refetchInterval: 15000,
  });

  const actions = safeArr<PrioritizedAction>(prioritized);
  const sortedActions = [...actions].sort((a, b) => safeStr(a.priority).localeCompare(safeStr(b.priority)));
  const anomalies = safeArr<PredictiveAlert>(predictiveDashboard?.predicted_anomalies);
  const criticalCount = anomalies.filter(a => a.severity === "critical").length;

  return (
    <div className="space-y-6">
      <motion.div className="flex items-center justify-between" {...fadeIn}>
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">STRATEGIC</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Strategic Intelligence Command Center</p>
        </div>
        <div className="flex items-center gap-3">
          {criticalCount > 0 && (
            <span className="px-3 py-1.5 rounded-md bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {criticalCount} CRITICAL
            </span>
          )}
          <span className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400">
            {anomalies.length} ALERTS
          </span>
          <span className="px-3 py-1.5 rounded-md bg-platform-500/10 border border-platform-500/30 text-xs font-mono text-platform-400 flex items-center gap-2">
            <BrainCircuit className="w-4 h-4" />
            LIVE
          </span>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div className="glass-panel p-6" {...slideUp}>
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">OPERATIONAL_SUMMARY</h3>
          </div>
          {loadingSummary ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : errorSummary ? (
            <div className="text-xs font-mono text-red-400 py-10 text-center">Failed to load operational summary</div>
          ) : summary ? (
            <div className="space-y-4">
              {summary.key_metrics && (
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(summary.key_metrics).map(([key, val]) => (
                    <div key={key} className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                      <p className="text-[10px] font-mono text-slate-500 uppercase">{safeReplace(key, /_/g, " ")}</p>
                      <p className="text-lg font-bold font-mono text-slate-200 mt-1">{typeof val === "number" ? val : safeStr(val)}</p>
                    </div>
                  ))}
                </div>
              )}
              {summary.notable_events && summary.notable_events.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-amber-400 uppercase mb-2">Notable Events</p>
                  <div className="space-y-1">
                    {summary.notable_events.map((evt, i) => {
                      const obj = safeObj(evt);
                      const label = typeof evt === "string" ? evt :
                        (obj.message as string) ||
                        (obj.type as string) ||
                        safeStr(evt);
                      return (
                        <div key={i} className="flex items-center gap-2 text-xs font-mono text-slate-300">
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0" />
                          {label}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {summary.recommended_focus && summary.recommended_focus.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-emerald-400 uppercase mb-2">Recommended Focus</p>
                  <div className="flex flex-wrap gap-1">
                    {summary.recommended_focus.map((f, i) => (
                      <span key={i} className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs font-mono text-slate-500 py-10 text-center">No operational summary data</div>
          )}
        </motion.div>

        <motion.div className="glass-panel p-6" {...slideUp} transition={{ delay: 0.1 }}>
          <div className="flex items-center gap-2 mb-4">
            <BrainCircuit className="w-5 h-5 text-purple-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">STRATEGIC_CONTEXT</h3>
          </div>
          {loadingContext ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : errorContext ? (
            <div className="text-xs font-mono text-red-400 py-10 text-center">Failed to load strategic context</div>
          ) : strategicContext ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Campaigns</p>
                  <p className="text-xl font-bold font-mono text-slate-200">
                    {Array.isArray(strategicContext.active_campaigns) ? strategicContext.active_campaigns.length : safeStr(strategicContext.active_campaigns)}
                  </p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Approvals</p>
                  <p className="text-xl font-bold font-mono text-amber-400">
                    {Array.isArray(strategicContext.pending_approvals) ? strategicContext.pending_approvals.length : safeStr(strategicContext.pending_approvals)}
                  </p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Infra</p>
                  <p className={`text-xl font-bold font-mono ${
                    (typeof strategicContext.infra_health === 'object' ? strategicContext.infra_health.overall_status : strategicContext.infra_health) === "healthy"
                      ? "text-emerald-400" : "text-amber-400"
                  }`}>
                    {safeUpper(typeof strategicContext.infra_health === 'object'
                      ? strategicContext.infra_health.overall_status
                      : strategicContext.infra_health)}
                  </p>
                </div>
              </div>
              {strategicContext.strategic_actions && strategicContext.strategic_actions.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-platform-400 uppercase mb-2">Strategic Actions</p>
                  <div className="space-y-2">
                    {strategicContext.strategic_actions.map((a, i) => (
                      <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/30 border border-surface-border/30">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-bold ${PRIORITY_BADGE[a.priority] || PRIORITY_BADGE.P3}`}>{a.priority}</span>
                          <span className="text-xs font-mono text-slate-300">{a.action}</span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">{safeStr(a.impact)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs font-mono text-slate-500 py-10 text-center">No strategic context data</div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div className="glass-panel p-6" {...slideUp} transition={{ delay: 0.2 }}>
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="w-5 h-5 text-cyan-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">ORG_INTELLIGENCE</h3>
          </div>
          {loadingOrg ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : errorOrg ? (
            <div className="text-xs font-mono text-red-400 py-10 text-center">Failed to load organization intelligence</div>
          ) : orgIntelligence ? (
            <div className="space-y-4">
              {orgIntelligence.campaign_performance && orgIntelligence.campaign_performance.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Campaign Performance</p>
                  <div className="space-y-2">
                    {orgIntelligence.campaign_performance.map((c, i) => {
                      const score = safeNum(c.score ?? c.completion_pct ?? (c.reply_rate != null ? c.reply_rate * 100 : 0));
                      const campaignName = c.name || c.campaign || `Campaign ${i + 1}`;
                      const trend = c.trend || (score > 50 ? "up" : score > 20 ? "stable" : "down");
                      return (
                        <div key={i} className="space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-mono text-slate-300 truncate pr-2">{campaignName}</span>
                            <span className={`text-[10px] font-mono flex-shrink-0 ${trend === "up" ? "text-emerald-400" : trend === "down" ? "text-red-400" : "text-slate-500"}`}>
                              {Math.round(score)}% {trend === "up" ? "↑" : trend === "down" ? "↓" : "→"}
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${Math.min(score, 100)}%` }}
                              className={`h-full rounded-full ${score >= 70 ? "bg-emerald-500" : score >= 40 ? "bg-amber-500" : "bg-red-500"}`}
                              transition={{ duration: 0.5 }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {orgIntelligence.workflow_reliability && orgIntelligence.workflow_reliability.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2 mt-4">Queue Reliability</p>
                  <div className="space-y-2">
                    {orgIntelligence.workflow_reliability.map((w, i) => {
                      const label = w.workflow || w.queue || `Queue ${i + 1}`;
                      const level = w.congestion_level || "none";
                      const reliability = safeNum(w.reliability ?? (level === "none" ? 100 : level === "low" ? 80 : level === "high" ? 40 : 60));
                      return (
                        <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/30 border border-surface-border/30">
                          <span className="text-xs font-mono text-slate-300 truncate pr-2">{label}</span>
                          <span className={`text-xs font-mono font-bold flex-shrink-0 ${reliability >= 80 ? "text-emerald-400" : reliability >= 50 ? "text-amber-400" : "text-red-400"}`}>
                            {Math.round(reliability)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs font-mono text-slate-500 py-10 text-center">No organization intelligence data</div>
          )}
        </motion.div>

        <motion.div className="glass-panel p-6" {...slideUp} transition={{ delay: 0.3 }}>
          <div className="flex items-center gap-2 mb-4">
            <ListChecks className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">PRIORITIZED_ACTIONS</h3>
            <span className="ml-auto text-xs font-mono text-slate-500">{sortedActions.length} total</span>
          </div>
          {loadingActions ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : errorActions ? (
            <div className="text-xs font-mono text-red-400 py-10 text-center">Failed to load prioritized actions</div>
          ) : sortedActions.length === 0 ? (
            <div className="text-xs font-mono text-slate-500 py-10 text-center">No prioritized actions</div>
          ) : (
            <div className="space-y-2 max-h-[350px] overflow-auto custom-scrollbar">
              {sortedActions.map((a, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-bold ${PRIORITY_BADGE[a.priority] || PRIORITY_BADGE.P3}`}>
                      {a.priority}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500 uppercase">{a.category}</span>
                  </div>
                  <p className="text-xs font-mono text-slate-300">{a.action}</p>
                  <p className="text-[10px] font-mono text-slate-600 mt-1">Impact: {safeStr(a.impact)}</p>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      <motion.div className="glass-panel p-6" {...slideUp} transition={{ delay: 0.4 }}>
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h3 className="text-lg font-medium text-slate-200 font-mono">PREDICTIVE_ALERTS</h3>
          {anomalies.length > 0 && (
            <span className="ml-auto px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-400">
              {anomalies.length} PREDICTED
            </span>
          )}
        </div>
        {loadingPredictive ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
          </div>
        ) : errorPredictive ? (
          <div className="text-xs font-mono text-red-400 py-10 text-center">Failed to load predictive alerts</div>
        ) : anomalies.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10">
            <Shield className="w-8 h-8 text-emerald-500 mb-2" />
            <p className="text-xs font-mono text-slate-500">No predicted anomalies</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {anomalies.map((a, i) => (
              <motion.div
                key={a.id || i}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-bold ${SEVERITY_BADGE[a.severity] || SEVERITY_BADGE.low}`}>
                    {safeUpper(a.severity)}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 uppercase">{a.component}</span>
                </div>
                <p className="text-xs font-mono text-slate-300 mb-3">{a.message}</p>
                <div>
                  <div className="flex justify-between text-[10px] font-mono mb-1">
                    <span className="text-slate-500">Probability</span>
                    <span className={probTextColor(a.probability)}>{Math.round(safeNum(a.probability) * 100)}%</span>
                  </div>
                  <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${safeNum(a.probability) * 100}%` }}
                      className={`h-full rounded-full ${probColor(a.probability)}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
