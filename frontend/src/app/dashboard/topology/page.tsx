"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, Server, Database, Cpu, Network, Loader2, X, Clock, GitBranch,
  Play, CheckCircle2, XCircle, AlertCircle, ArrowRight, Layers,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface Phase {
  name: string;
  status: "running" | "completed" | "failed" | "waiting";
  started_at?: string;
  duration_ms?: number;
}

interface WorkflowNode {
  workflow_id: string;
  type: string;
  label: string;
  status: "running" | "completed" | "failed" | "waiting";
  phases: Phase[];
  task_queue: string;
  started_at: string;
  dependencies: string[];
}

interface WorkflowHistoryEntry {
  workflow_id: string;
  type: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

interface RealtimeState {
  workflows: WorkflowNode[];
  heartbeat: string;
}

const WORKFLOW_DEFS = [
  {
    type: "OperationalLoopEngine", label: "Operational Loop", task_queue: "seo-platform-ai-orchestration",
    phases: ["pulse", "scan_campaigns", "check_health", "generate_events", "sleep"],
    dependencies: [],
  },
  {
    type: "ContinuousIntelligenceLoop", label: "Intelligence Loop", task_queue: "seo-platform-ai-orchestration",
    phases: ["monitor_serp", "verify_citations", "analyze_rankings", "generate_recommendations", "sleep"],
    dependencies: [],
  },
  {
    type: "AutonomousDiscovery", label: "Auto Discovery", task_queue: "seo-platform-backlink-engine",
    phases: ["scan_opportunities", "generate_recommendations", "log_discovery", "complete"],
    dependencies: ["OperationalLoopEngine"],
  },
  {
    type: "KeywordResearchWorkflow", label: "Keyword Research", task_queue: "seo-platform-ai-orchestration",
    phases: ["generate_seeds", "expand_keywords", "enrich_keywords", "cluster_keywords", "persist"],
    dependencies: [],
  },
  {
    type: "BacklinkCampaignWorkflow", label: "Backlink Campaign", task_queue: "seo-platform-backlink-engine",
    phases: ["discover_prospects", "score_prospects", "find_contacts", "generate_emails", "launch"],
    dependencies: ["KeywordResearchWorkflow"],
  },
];

const PHASE_LABELS: Record<string, string> = {
  pulse: "Pulse",
  scan_campaigns: "Scan Campaigns",
  check_health: "Check Health",
  generate_events: "Generate Events",
  sleep: "Sleep",
  monitor_serp: "Monitor SERP",
  verify_citations: "Verify Citations",
  analyze_rankings: "Analyze Rankings",
  generate_recommendations: "Gen Recommendations",
  scan_opportunities: "Scan Opportunities",
  log_discovery: "Log Discovery",
  generate_seeds: "Generate Seeds",
  expand_keywords: "Expand Keywords",
  enrich_keywords: "Enrich Keywords",
  cluster_keywords: "Cluster Keywords",
  persist: "Persist",
  discover_prospects: "Discover Prospects",
  score_prospects: "Score Prospects",
  find_contacts: "Find Contacts",
  generate_emails: "Generate Emails",
  launch: "Launch",
  complete: "Complete",
};

const STATUS_COLORS: Record<string, { dot: string; bg: string; border: string; text: string }> = {
  running: { dot: "bg-blue-500", bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400" },
  completed: { dot: "bg-emerald-500", bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400" },
  failed: { dot: "bg-red-500", bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400" },
  waiting: { dot: "bg-amber-500", bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400" },
};

const PHASE_ICONS: Record<string, React.ReactNode> = {
  running: <Play className="w-3 h-3 text-blue-400" />,
  completed: <CheckCircle2 className="w-3 h-3 text-emerald-400" />,
  failed: <XCircle className="w-3 h-3 text-red-400" />,
  waiting: <AlertCircle className="w-3 h-3 text-amber-400" />,
};

export default function TopologyPage() {
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [selectedHistory, setSelectedHistory] = useState<WorkflowHistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const { data: stateData, isLoading } = useQuery<RealtimeState>({
    queryKey: ["realtime-state", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/realtime/state/${MOCK_TENANT_ID}`),
    refetchInterval: 5000,
  });

  const { data: historyData } = useQuery<WorkflowHistoryEntry[]>({
    queryKey: ["workflow-history", MOCK_TENANT_ID, selectedWorkflow],
    queryFn: () => fetchApi(`/workflows/${selectedWorkflow}/history?tenant_id=${MOCK_TENANT_ID}`),
    enabled: !!selectedWorkflow,
  });

  const getWorkflowStatus = (type: string): WorkflowNode["status"] => {
    if (!stateData?.workflows) return "waiting";
    const match = stateData.workflows.find((w) => w.type === type);
    return match ? match.status : "waiting";
  };

  const getWorkflowPhases = (type: string): Phase[] => {
    const def = WORKFLOW_DEFS.find((w) => w.type === type);
    const defaultPhases = def ? def.phases.map((p) => ({ name: p, status: "waiting" as const })) : [];
    if (!stateData?.workflows) return defaultPhases;
    const match = stateData.workflows.find((w) => w.type === type);
    if (match && match.phases && match.phases.length > 0) return match.phases;
    return defaultPhases;
  };

  const handleNodeClick = (type: string) => {
    setSelectedWorkflow(type);
    setShowHistory(true);
  };

  const hasDependency = (type: string, dep: string) => {
    const def = WORKFLOW_DEFS.find((w) => w.type === type);
    return def?.dependencies.includes(dep) || false;
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">WORKFLOW_TOPOLOGY</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Live Workflow Execution DAG</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 ${
            isLoading ? "bg-surface-darker border-surface-border text-slate-400" : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
          }`}>
            <span className={`w-2 h-2 rounded-full ${isLoading ? "bg-slate-600" : "bg-emerald-500 animate-pulse"}`}></span>
            {isLoading ? "SYNCING..." : "LIVE"}
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : (
        <>
          <div className="relative flex-1 glass-panel p-8 overflow-auto">
            <div className="flex flex-col items-center gap-16">
              {/* Row 1: Onboarding */}
              <div className="flex justify-center w-full">
                <WorkflowNodeCard
                  def={WORKFLOW_DEFS[0]}
                  status={getWorkflowStatus("OnboardingWorkflow")}
                  phases={getWorkflowPhases("OnboardingWorkflow")}
                  onClick={handleNodeClick}
                  layer={0}
                />
              </div>

              {/* Arrow from Onboarding to KeywordResearch */}
              <div className="flex justify-center w-full">
                <div className="flex items-center gap-2 text-slate-600">
                  <div className="h-px w-16 bg-gradient-to-r from-transparent via-slate-600 to-transparent"></div>
                  <ArrowRight className="w-4 h-4" />
                  <div className="h-px w-16 bg-gradient-to-r from-slate-600 to-transparent"></div>
                </div>
              </div>

              {/* Row 2: KeywordResearch */}
              <div className="flex justify-center w-full">
                <WorkflowNodeCard
                  def={WORKFLOW_DEFS[1]}
                  status={getWorkflowStatus("KeywordResearchWorkflow")}
                  phases={getWorkflowPhases("KeywordResearchWorkflow")}
                  onClick={handleNodeClick}
                  layer={1}
                />
              </div>

              {/* Fork arrows */}
              <div className="flex justify-center w-full">
                <div className="flex items-center gap-24">
                  <div className="flex items-center gap-2 text-slate-600">
                    <div className="h-px w-12 bg-gradient-to-r from-transparent via-slate-600 to-transparent"></div>
                    <ArrowRight className="w-4 h-4" />
                    <div className="h-px w-12 bg-gradient-to-r from-slate-600 to-transparent"></div>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <div className="h-px w-12 bg-gradient-to-r from-transparent via-slate-600 to-transparent"></div>
                    <ArrowRight className="w-4 h-4" />
                    <div className="h-px w-12 bg-gradient-to-r from-slate-600 to-transparent"></div>
                  </div>
                </div>
              </div>

              {/* Row 3: BacklinkCampaign | CitationSubmission (parallel) */}
              <div className="grid grid-cols-2 gap-24 w-full max-w-4xl mx-auto">
                <WorkflowNodeCard
                  def={WORKFLOW_DEFS[2]}
                  status={getWorkflowStatus("BacklinkCampaignWorkflow")}
                  phases={getWorkflowPhases("BacklinkCampaignWorkflow")}
                  onClick={handleNodeClick}
                  layer={2}
                />
                <WorkflowNodeCard
                  def={WORKFLOW_DEFS[3]}
                  status={getWorkflowStatus("CitationSubmissionWorkflow")}
                  phases={getWorkflowPhases("CitationSubmissionWorkflow")}
                  onClick={handleNodeClick}
                  layer={2}
                />
              </div>

              {/* Join arrows */}
              <div className="flex justify-center w-full">
                <div className="flex items-center gap-24">
                  <div className="flex items-center gap-2 text-slate-600">
                    <div className="h-px w-12 bg-gradient-to-r from-transparent via-slate-600 to-transparent"></div>
                    <ArrowRight className="w-4 h-4" />
                    <div className="h-px w-12 bg-gradient-to-r from-slate-600 to-transparent"></div>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600">
                    <div className="h-px w-12 bg-gradient-to-r from-transparent via-slate-600 to-transparent"></div>
                    <ArrowRight className="w-4 h-4" />
                    <div className="h-px w-12 bg-gradient-to-r from-slate-600 to-transparent"></div>
                  </div>
                </div>
              </div>

              {/* Row 4: ReportGeneration */}
              <div className="flex justify-center w-full">
                <WorkflowNodeCard
                  def={WORKFLOW_DEFS[4]}
                  status={getWorkflowStatus("ReportGenerationWorkflow")}
                  phases={getWorkflowPhases("ReportGenerationWorkflow")}
                  onClick={handleNodeClick}
                  layer={3}
                />
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-6 px-2 text-xs font-mono text-slate-500">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Running</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Completed</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-500"></span> Failed</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-500"></span> Waiting</span>
          </div>
        </>
      )}

      {/* History Modal */}
      <AnimatePresence>
        {showHistory && selectedWorkflow && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-panel w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
            >
              <div className="p-6 border-b border-surface-border flex justify-between items-center bg-surface-darker/50">
                <div>
                  <h2 className="text-xl font-bold text-slate-100 font-mono">{WORKFLOW_DEFS.find(w => w.type === selectedWorkflow)?.label}</h2>
                  <p className="text-sm text-slate-400">Execution History</p>
                </div>
                <button onClick={() => { setShowHistory(false); setSelectedWorkflow(null); }} className="p-2 hover:bg-surface-border rounded-full">
                  <X className="w-6 h-6 text-slate-400" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                {!historyData || historyData.length === 0 ? (
                  <div className="text-center py-12 text-slate-500 font-mono">No execution history available</div>
                ) : (
                  <div className="space-y-3">
                    {historyData.map((entry) => (
                      <div key={entry.workflow_id} className="p-4 bg-surface-darker/50 rounded-lg border border-surface-border flex items-center justify-between">
                        <div>
                          <div className="text-sm font-mono text-slate-200">{entry.workflow_id.slice(0, 12)}...</div>
                          <div className="text-xs text-slate-500 mt-1">
                            {new Date(entry.started_at).toLocaleString()}
                            {entry.duration_ms && `  \u00b7 ${(entry.duration_ms / 1000).toFixed(1)}s`}
                          </div>
                        </div>
                        <span className={`px-2 py-1 text-xs font-mono rounded border uppercase ${
                          entry.status === "completed" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                          entry.status === "failed" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                          "bg-blue-500/10 text-blue-400 border-blue-500/20"
                        }`}>{entry.status}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function WorkflowNodeCard({
  def, status, phases, onClick, layer,
}: {
  def: typeof WORKFLOW_DEFS[0];
  status: WorkflowNode["status"];
  phases: Phase[];
  onClick: (type: string) => void;
  layer: number;
}) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.waiting;
  const completedCount = phases.filter((p) => p.status === "completed").length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: layer * 0.1 }}
      onClick={() => onClick(def.type)}
      className={`glass-panel p-5 border ${colors.border} cursor-pointer hover:shadow-lg hover:shadow-black/30 transition-all min-w-[320px]`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg ${colors.bg} border ${colors.border} flex items-center justify-center`}>
            <GitBranch className={`w-5 h-5 ${colors.text}`} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-200">{def.label}</h3>
            <span className="text-xs font-mono text-slate-500">queue: {def.task_queue}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${colors.dot} ${status === "running" ? "animate-pulse" : ""}`}></span>
          <span className={`text-xs font-mono font-bold uppercase ${colors.text}`}>{status}</span>
        </div>
      </div>

      {/* Phase progression */}
      <div className="space-y-1.5 mb-3">
        {phases.length > 0 ? (
          phases.map((phase) => {
            const phaseColors = STATUS_COLORS[phase.status] || STATUS_COLORS.waiting;
            return (
              <div key={phase.name} className="flex items-center gap-3 text-xs">
                <div className="flex-shrink-0 w-4">{PHASE_ICONS[phase.status] || PHASE_ICONS.waiting}</div>
                <span className="text-slate-400">{PHASE_LABELS[phase.name] || phase.name}</span>
                {phase.duration_ms && <span className="text-slate-600 font-mono ml-auto">{(phase.duration_ms / 1000).toFixed(1)}s</span>}
              </div>
            );
          })
        ) : (
          <div className="text-xs text-slate-600 py-2 text-center font-mono">Awaiting execution</div>
        )}
      </div>

      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-surface-darker rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${phases.length > 0 ? (completedCount / phases.length) * 100 : 0}%` }}
            className={`h-full rounded-full ${status === "failed" ? "bg-red-500" : status === "completed" ? "bg-emerald-500" : status === "running" ? "bg-blue-500" : "bg-amber-500/50"}`}
            transition={{ duration: 0.5 }}
          />
        </div>
        <span className="text-xs font-mono text-slate-500">{completedCount}/{phases.length}</span>
      </div>

      {/* Dependencies */}
      {def.dependencies.length > 0 && (
        <div className="mt-3 pt-3 border-t border-surface-border flex items-center gap-2 text-[10px] text-slate-600 font-mono">
          <Layers className="w-3 h-3" />
          <span>Depends on: {def.dependencies.map(d => WORKFLOW_DEFS.find(w => w.type === d)?.label || d).join(", ")}</span>
        </div>
      )}
    </motion.div>
  );
}
