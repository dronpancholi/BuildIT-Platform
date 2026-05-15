"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Radio, CheckCircle2, AlertCircle, Clock, Play,
  ArrowRight, Loader2,
} from "lucide-react";
import { useRealtimeStore, type WorkflowState } from "@/hooks/use-realtime";

const WORKFLOW_STATUS_CONFIG: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
  running: { color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20", icon: <Radio className="w-3 h-3" /> },
  active: { color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20", icon: <Play className="w-3 h-3" /> },
  started: { color: "text-platform-400", bg: "bg-platform-500/10 border-platform-500/20", icon: <Play className="w-3 h-3" /> },
  completed: { color: "text-slate-500", bg: "bg-slate-500/10 border-slate-500/20", icon: <CheckCircle2 className="w-3 h-3" /> },
  failed: { color: "text-red-400", bg: "bg-red-500/10 border-red-500/20", icon: <AlertCircle className="w-3 h-3" /> },
  timed_out: { color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20", icon: <Clock className="w-3 h-3" /> },
};

const TASK_QUEUES = ["ONBOARDING", "SEO_INTELLIGENCE", "BACKLINK_ENGINE", "COMMUNICATION", "REPORTING", "AI_ORCHESTRATION"];

export function WorkflowVisualization() {
  const workflows = useRealtimeStore((s) => s.workflows);
  const queues = useRealtimeStore((s) => s.queues);

  const activeWorkflows = useMemo(() =>
    workflows.filter((w) => w.status === "running" || w.status === "active" || w.status === "started"),
    [workflows],
  );

  const recentCompleted = useMemo(() =>
    workflows.filter((w) => w.status === "completed").slice(0, 5),
    [workflows],
  );

  const queueEntries = useMemo(() =>
    TASK_QUEUES.map((name) => ({
      name,
      depth: (queues[name] as number) || 0,
      count: activeWorkflows.filter((w) => w.task_queue === name).length,
    })),
    [queues, activeWorkflows],
  );

  return (
    <div className="glass-panel overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border bg-surface-darker/50">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
            Orchestration Pulse
          </h3>
          <span className="text-[9px] font-mono text-slate-600">
            {activeWorkflows.length} active · {workflows.length} total
          </span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Queue Activity Grid */}
        <div className="grid grid-cols-3 gap-2">
          {queueEntries.map((q) => (
            <motion.div
              key={q.name}
              animate={q.count > 0 ? { scale: [1, 1.02, 1] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
              className={`p-2 rounded-lg border text-center ${
                q.count > 0
                  ? "bg-emerald-500/5 border-emerald-500/20"
                  : q.depth > 0
                    ? "bg-amber-500/5 border-amber-500/20"
                    : "bg-surface-darker/50 border-surface-border/50"
              }`}
            >
              <span className="text-[8px] font-mono text-slate-500 uppercase block truncate">
                {q.name.replace(/_/g, " ")}
              </span>
              <span className={`text-sm font-bold font-mono ${
                q.count > 0 ? "text-emerald-400" : q.depth > 0 ? "text-amber-400" : "text-slate-600"
              }`}>
                {q.count || q.depth || "0"}
              </span>
            </motion.div>
          ))}
        </div>

        {/* Active Workflows */}
        {activeWorkflows.length > 0 && (
          <div>
            <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-2">Active Executions</p>
            <div className="space-y-1.5">
              <AnimatePresence>
                {activeWorkflows.slice(0, 6).map((wf) => {
                  const config = WORKFLOW_STATUS_CONFIG[wf.status] || WORKFLOW_STATUS_CONFIG.running;
                  return (
                    <motion.div
                      key={wf.workflow_id}
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="flex items-center gap-2 p-2 rounded bg-surface-darker/50 border border-surface-border/50"
                    >
                      <motion.div
                        animate={{ rotate: wf.status === "running" ? 360 : 0 }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                      >
                        {config.icon}
                      </motion.div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-mono text-slate-300 truncate">
                          {wf.type || wf.workflow_id.slice(0, 12)}...
                        </p>
                        <p className="text-[8px] font-mono text-slate-600">
                          {wf.task_queue || "default"} · {new Date(wf.started_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-mono font-bold border ${config.bg} ${config.color}`}>
                        {wf.status}
                      </span>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          </div>
        )}

        {/* Recent Completions */}
        {recentCompleted.length > 0 && (
          <div>
            <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-2">Recent Completions</p>
            <div className="space-y-1">
              {recentCompleted.map((wf) => (
                <div key={wf.workflow_id} className="flex items-center gap-2 text-[9px] font-mono text-slate-600">
                  <CheckCircle2 className="w-2.5 h-2.5 text-emerald-500/50" />
                  <span className="truncate">{wf.type || wf.workflow_id.slice(0, 12)}...</span>
                  <span className="ml-auto">{new Date(wf.started_at).toLocaleTimeString()}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeWorkflows.length === 0 && recentCompleted.length === 0 && (
          <div className="text-center py-6">
            <Radio className="w-6 h-6 text-slate-700 mx-auto mb-2" />
            <p className="text-[10px] font-mono text-slate-600">No active orchestration activity</p>
          </div>
        )}
      </div>
    </div>
  );
}
