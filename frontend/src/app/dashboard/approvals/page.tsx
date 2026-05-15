"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X, Clock, ShieldAlert, ArrowRight, Loader2, Activity, Bell, Ban } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { ApprovalRequest } from "@/types/api";
import { useSSE } from "@/hooks/use-sse";

interface SSEApprovalEvent {
  event_type: string;
  channel: string;
  payload: {
    approval_id?: string;
    summary?: string;
    risk_level?: string;
    status?: string;
    category?: string;
  };
}

function useCountdown(deadline: string | null): string {
  const [display, setDisplay] = useState("");

  useEffect(() => {
    if (!deadline) { setDisplay("—"); return; }

    const update = () => {
      const diff = new Date(deadline).getTime() - Date.now();
      if (diff <= 0) { setDisplay("OVERDUE"); return; }
      const hours = Math.floor(diff / 3600000);
      const mins = Math.floor((diff % 3600000) / 60000);
      const secs = Math.floor((diff % 60000) / 1000);
      setDisplay(`${hours.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`);
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [deadline]);

  return display;
}

function getSlaColor(deadline: string | null): string {
  if (!deadline) return "text-slate-500";
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff <= 0) return "text-red-400 animate-pulse";
  if (diff < 3600000) return "text-amber-400";
  return "text-slate-500";
}

const WORKFLOW_COLORS: Record<string, string> = {
  onboarding: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  keyword: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  backlink: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  citation: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  report: "bg-purple-500/10 text-purple-400 border-purple-500/20",
};

function detectWorkflowType(workflowRunId: string): string {
  const lower = workflowRunId.toLowerCase();
  if (lower.includes("onboarding")) return "onboarding";
  if (lower.includes("keyword")) return "keyword";
  if (lower.includes("backlink")) return "backlink";
  if (lower.includes("citation")) return "citation";
  if (lower.includes("report")) return "report";
  return "onboarding";
}

export default function ApprovalsPage() {
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [newApprovalAlert, setNewApprovalAlert] = useState(false);
  const queryClient = useQueryClient();

  const { data: approvals = [], isLoading, isError } = useQuery<ApprovalRequest[]>({
    queryKey: ["approvals"],
    queryFn: () => fetchApi(`/approvals?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 10000,
  });

  const { lastEvent } = useSSE<SSEApprovalEvent>(MOCK_TENANT_ID, "approvals");

  useEffect(() => {
    if (lastEvent?.event_type === "approval_update" && lastEvent?.payload?.status === "pending") {
      setNewApprovalAlert(true);
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      const timer = setTimeout(() => setNewApprovalAlert(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [lastEvent, queryClient]);

  const decideMutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "approved" | "rejected" }) =>
      fetchApi(`/approvals/${id}/decide?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({ decision, decided_by: MOCK_TENANT_ID }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      setSelectedApproval(null);
    },
  });

  const handleDecide = (id: string, decision: "approved" | "rejected") => {
    decideMutation.mutate({ id, decision });
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Approval Queue</h1>
          <p className="text-slate-400 mt-1">Human-in-the-loop gates requiring your attention.</p>
        </div>
        <div className="flex items-center gap-3">
          <AnimatePresence>
            {newApprovalAlert && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="px-3 py-1.5 bg-platform-500/10 border border-platform-500/30 rounded-md text-xs font-mono text-platform-400 flex items-center gap-2"
              >
                <Bell className="w-3.5 h-3.5 animate-pulse" />
                NEW APPROVAL
              </motion.div>
            )}
          </AnimatePresence>
          <div className="px-4 py-2 bg-platform-600/20 border border-platform-500/30 rounded-lg flex items-center gap-2">
            <Clock className="w-4 h-4 text-platform-400" />
            <span className="text-sm font-medium text-platform-300">
              {isLoading ? "..." : approvals.length} Pending
            </span>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : isError ? (
        <div className="glass-panel p-6 border-red-500/20 bg-red-500/5">
          <h3 className="text-red-400 font-medium">Failed to load approvals</h3>
          <p className="text-sm text-slate-400 mt-1">Please ensure the backend is running and the database is accessible.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((approval, index) => (
            <SLAApprovalCard
              key={approval.id}
              approval={approval}
              index={index}
              onDecide={handleDecide}
              onReview={setSelectedApproval}
              isPending={decideMutation.isPending}
            />
          ))}

          {approvals.length === 0 && (
            <div className="glass-panel p-12 text-center flex flex-col items-center justify-center border-dashed">
              <div className="w-16 h-16 bg-platform-900/30 rounded-full flex items-center justify-center mb-4 border border-platform-500/20">
                <Check className="w-8 h-8 text-platform-400" />
              </div>
              <h3 className="text-xl font-medium text-slate-200">All caught up!</h3>
              <p className="text-slate-400 mt-2 max-w-md">
                There are no pending approval requests in the queue right now.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Detail Modal */}
      {selectedApproval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="glass-panel w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
          >
            <div className="p-6 border-b border-surface-border flex justify-between items-center bg-surface-darker/50">
              <div>
                <h2 className="text-xl font-bold text-slate-100">Review Approval Request</h2>
                <p className="text-sm text-slate-400">Context snapshot for deterministic validation.</p>
              </div>
              <button
                onClick={() => setSelectedApproval(null)}
                className="p-2 hover:bg-surface-border rounded-full transition-colors"
              >
                <X className="w-6 h-6 text-slate-400" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
              <div className="space-y-6">
                <section>
                  <h4 className="text-xs font-bold uppercase tracking-widest text-platform-500 mb-2">Metadata</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="p-3 bg-surface-darker/30 rounded border border-surface-border">
                      <span className="block text-slate-500 text-xs mb-1">Workflow ID</span>
                      <code className="text-platform-300 font-mono">{selectedApproval.workflow_run_id}</code>
                    </div>
                    <div className="p-3 bg-surface-darker/30 rounded border border-surface-border">
                      <span className="block text-slate-500 text-xs mb-1">Category</span>
                      <span className="text-slate-200 capitalize">{selectedApproval.category.replace("_", " ")}</span>
                    </div>
                  </div>
                </section>

                <section>
                  <h4 className="text-xs font-bold uppercase tracking-widest text-platform-500 mb-2">Content Snapshot</h4>
                  <pre className="p-4 bg-slate-900 rounded-lg border border-surface-border overflow-x-auto font-mono text-sm text-platform-400 custom-scrollbar">
                    {JSON.stringify(selectedApproval.context_snapshot, null, 2)}
                  </pre>
                </section>

                {selectedApproval.ai_risk_summary && (
                  <section className="p-4 bg-platform-900/10 border border-platform-500/20 rounded-lg">
                    <h4 className="text-xs font-bold uppercase tracking-widest text-platform-500 mb-2 flex items-center gap-2">
                      <ShieldAlert className="w-3 h-3" /> AI Governance Intelligence
                    </h4>
                    <p className="text-slate-300 text-sm leading-relaxed italic">
                      &ldquo;{selectedApproval.ai_risk_summary}&rdquo;
                    </p>
                  </section>
                )}
              </div>
            </div>

            <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
              <button
                onClick={() => handleDecide(selectedApproval.id, "rejected")}
                disabled={decideMutation.isPending}
                className="flex-1 px-4 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 rounded-lg font-semibold transition-all disabled:opacity-50"
              >
                Reject Request
              </button>
              <button
                onClick={() => handleDecide(selectedApproval.id, "approved")}
                disabled={decideMutation.isPending}
                className="flex-1 px-4 py-3 bg-emerald-500/80 hover:bg-emerald-500 text-slate-950 rounded-lg font-bold shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
              >
                {decideMutation.isPending ? "Processing..." : "Approve & Resume"}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}

function SLAApprovalCard({
  approval, index, onDecide, onReview, isPending,
}: {
  approval: ApprovalRequest;
  index: number;
  onDecide: (id: string, decision: "approved" | "rejected") => void;
  onReview: (a: ApprovalRequest) => void;
  isPending: boolean;
}) {
  const slaDisplay = useCountdown(approval.sla_deadline);
  const slaColor = getSlaColor(approval.sla_deadline);
  const wfType = detectWorkflowType(approval.workflow_run_id);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`glass-panel p-6 flex flex-col md:flex-row gap-6 items-start md:items-center border-l-4 ${
        approval.risk_level === "critical" ? "border-l-red-500" :
        approval.risk_level === "high" ? "border-l-amber-500" : "border-l-platform-500"
      }`}
    >
      {/* Risk Indicator */}
      <div className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-surface-darker border border-surface-border">
        {approval.risk_level === "critical" ? (
          <ShieldAlert className="w-6 h-6 text-red-500" />
        ) : approval.risk_level === "high" ? (
          <ShieldAlert className="w-6 h-6 text-amber-500" />
        ) : (
          <ShieldAlert className="w-6 h-6 text-platform-500" />
        )}
      </div>

      {/* Details */}
      <div className="flex-1">
        <div className="flex items-center gap-3 mb-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 bg-surface-darker px-2 py-0.5 rounded">
            {approval.category.replace("_", " ")}
          </span>
          <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded border ${WORKFLOW_COLORS[wfType] || WORKFLOW_COLORS.onboarding}`}>
            {wfType}
          </span>
          {approval.sla_deadline && (
            <span className={`text-xs font-mono flex items-center gap-1 ${slaColor}`}>
              <Clock className="w-3 h-3" /> SLA: {slaDisplay}
            </span>
          )}
        </div>
        <h3 className="text-lg font-semibold text-slate-200">Request: {approval.id.substring(0, 8)}...</h3>
        <p className="text-slate-400 text-sm mt-1">{approval.summary}</p>
        {approval.ai_risk_summary && (
          <p className="text-platform-400 text-xs mt-2 p-2 bg-platform-900/20 rounded border border-platform-500/10">
            <strong>AI Analysis:</strong> {approval.ai_risk_summary}
          </p>
        )}
        {approval.escalation_count > 0 && (
          <p className="text-red-400 text-xs mt-1 flex items-center gap-1">
            <Ban className="w-3 h-3" /> Escalated {approval.escalation_count} time(s)
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
        <button
          onClick={() => onReview(approval)}
          className="w-full sm:w-auto px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2"
        >
          Review Context <ArrowRight className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => onDecide(approval.id, "rejected")}
            disabled={isPending}
            className="flex-1 sm:flex-none p-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-md transition-colors flex justify-center border border-red-500/20 disabled:opacity-50"
            title="Reject"
          >
            <X className="w-5 h-5" />
          </button>
          <button
            onClick={() => onDecide(approval.id, "approved")}
            disabled={isPending}
            className="flex-1 sm:flex-none p-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 rounded-md transition-colors flex justify-center border border-emerald-500/20 disabled:opacity-50"
            title="Approve"
          >
            <Check className="w-5 h-5" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
