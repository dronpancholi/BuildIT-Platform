"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { Filter, CheckCircle2, XCircle, Clock, AlertTriangle, FileEdit, History } from "lucide-react";

interface ApprovalRequest {
  id: string;
  workflow_run_id: string;
  category: string;
  risk_level: string;
  status: string;
  summary: string;
  ai_risk_summary: string;
  sla_deadline?: string;
  escalation_count: number;
  context_snapshot: any;
  created_at: string;
  decided_by?: string;
  decided_at?: string;
  decision_reason?: string;
}

interface AuditEntry {
  id: string;
  approval_id: string;
  action: string;
  decided_by: string;
  reason?: string;
  created_at: string;
}

export default function ApprovalCenter() {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [showAuditHistory, setShowAuditHistory] = useState(false);
  const [editData, setEditData] = useState<any>(null);

  const { data: approvals = [], isLoading } = useQuery<ApprovalRequest[]>({
    queryKey: ["approvals", "pending"],
    queryFn: () => fetchApi(`/approvals?tenant_id=${MOCK_TENANT_ID}&status=pending`),
    refetchInterval: 30000,
  });

  const categories = ["all", ...Array.from(new Set(approvals.map(a => a.category)))];

  const filteredApprovals = selectedCategory === "all" 
    ? approvals 
    : approvals.filter(a => a.category === selectedCategory);

  const stats = {
    total: approvals.length,
    critical: approvals.filter(a => a.risk_level === "critical").length,
    high: approvals.filter(a => a.risk_level === "high").length,
    byCategory: categories.filter(c => c !== "all").reduce((acc, cat) => {
      acc[cat] = approvals.filter(a => a.category === cat).length;
      return acc;
    }, {} as Record<string, number>),
  };

  const decideMutation = useMutation({
    mutationFn: async ({ id, decision, reason, modifications }: { 
      id: string; 
      decision: "approved" | "rejected" | "modification_requested";
      reason?: string;
      modifications?: any;
    }) => {
      const response = await fetchApi(`/approvals/${id}/decide?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          decided_by: MOCK_TENANT_ID,
          reason: reason || "",
          modifications: modifications || {},
        }),
      });
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      setSelectedApproval(null);
      setEditData(null);
    },
  });

  const handleDecision = (decision: "approved" | "rejected" | "modification_requested") => {
    if (!selectedApproval) return;
    decideMutation.mutate({
      id: selectedApproval.id,
      decision,
      reason: editData?.reason || "",
      modifications: editData?.modifications || {},
    });
  };

  const getRiskBadge = (riskLevel: string) => {
    const config: Record<string, { color: string; icon: any; label: string }> = {
      critical: { color: "bg-red-500/10 text-red-400 border-red-500/20", icon: AlertTriangle, label: "CRITICAL" },
      high: { color: "bg-orange-500/10 text-orange-400 border-orange-500/20", icon: AlertTriangle, label: "HIGH" },
      medium: { color: "bg-amber-500/10 text-amber-400 border-amber-500/20", icon: Clock, label: "MEDIUM" },
      low: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20", icon: CheckCircle2, label: "LOW" },
    };
    const { color, icon: Icon, label } = config[riskLevel] || config.low;
    return (
      <span className={`px-2 py-1 text-[10px] font-mono rounded border ${color} flex items-center gap-1`}>
        <Icon className="w-3 h-3" />
        {label}
      </span>
    );
  };

  const getCategoryBadge = (category: string) => {
    const config: Record<string, { color: string }> = {
      outreach_email: { color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
      prospect_approval: { color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
      campaign_launch: { color: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
      report_generation: { color: "bg-pink-500/10 text-pink-400 border-pink-500/20" },
      keyword_cluster: { color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" },
      default: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20" },
    };
    const { color } = config[category] || config.default;
    return (
      <span className={`px-2 py-1 text-[10px] font-mono rounded border ${color}`}>
        {category.replace("_", " ").toUpperCase()}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Approval Center</h1>
          <p className="text-slate-400 mt-1">Unified approval management for all workflows</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="px-4 py-2 bg-platform-600/20 border border-platform-500/30 rounded-lg flex items-center gap-2">
            <Clock className="w-4 h-4 text-platform-400" />
            <span className="text-sm font-mono text-platform-300">{stats.total} Pending</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileEdit className="w-3.5 h-3.5" /> Total
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{stats.total}</p>
        </div>
        <div className="glass-panel p-4 border-red-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-red-500 uppercase mb-2">
            <AlertTriangle className="w-3.5 h-3.5" /> Critical
          </div>
          <p className="text-2xl font-bold font-mono text-red-400">{stats.critical}</p>
        </div>
        <div className="glass-panel p-4 border-orange-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-orange-500 uppercase mb-2">
            <AlertTriangle className="w-3.5 h-3.5" /> High
          </div>
          <p className="text-2xl font-bold font-mono text-orange-400">{stats.high}</p>
        </div>
        <div className="glass-panel p-4 border-platform-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-platform-500 uppercase mb-2">
            <History className="w-3.5 h-3.5" /> Categories
          </div>
          <p className="text-2xl font-bold font-mono text-platform-400">{categories.length - 1}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50 flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-mono text-slate-400 uppercase">Filter by Category</span>
        </div>
        <div className="p-2 flex flex-wrap gap-2">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`px-3 py-1.5 text-xs font-mono rounded transition-colors ${
                selectedCategory === category
                  ? "bg-platform-600 text-white"
                  : "bg-surface-darker text-slate-400 hover:text-slate-200 border border-surface-border"
              }`}
            >
              {category === "all" ? "ALL" : category.replace("_", " ").toUpperCase()}
              {category !== "all" && stats.byCategory[category] > 0 && (
                <span className="ml-1 text-[10px] opacity-70">({stats.byCategory[category]})</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Approval List */}
      {isLoading ? (
        <div className="glass-panel p-12 text-center">
          <Clock className="w-12 h-12 text-platform-500 animate-spin mx-auto mb-3" />
          <p className="text-xs font-mono text-slate-500">Loading approvals...</p>
        </div>
      ) : filteredApprovals.length === 0 ? (
        <div className="glass-panel p-12 text-center">
          <CheckCircle2 className="w-12 h-12 text-slate-700 mx-auto mb-3" />
          <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Pending Approvals</h3>
          <p className="text-xs text-slate-500">All clear! No approvals waiting for your decision.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredApprovals.map((approval) => (
            <div
              key={approval.id}
              className="glass-panel p-4 border-l-4 hover:bg-surface-border/20 transition-all cursor-pointer"
              style={{ borderLeftColor: 
                approval.risk_level === "critical" ? "#ef4444" :
                approval.risk_level === "high" ? "#f97316" : "#6366f1"
              }}
              onClick={() => setSelectedApproval(approval)}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  {getCategoryBadge(approval.category)}
                  {getRiskBadge(approval.risk_level)}
                  {approval.escalation_count > 0 && (
                    <span className="px-2 py-1 text-[10px] font-mono rounded border bg-red-500/10 text-red-400 border-red-500/20">
                      {approval.escalation_count} ESCALATION{approval.escalation_count > 1 ? "S" : ""}
                    </span>
                  )}
                </div>
                <span className="text-[10px] font-mono text-slate-600">
                  {new Date(approval.created_at).toLocaleString()}
                </span>
              </div>
              <h3 className="text-sm font-bold font-mono text-slate-200 mb-1">{approval.summary}</h3>
              {approval.ai_risk_summary && (
                <p className="text-[10px] text-platform-400 mb-2">{approval.ai_risk_summary}</p>
              )}
              <div className="flex items-center gap-4 text-[10px] font-mono text-slate-600">
                <span>Workflow: {approval.workflow_run_id.slice(0, 12)}...</span>
                {approval.sla_deadline && (
                  <span className="text-amber-500">SLA: {new Date(approval.sla_deadline).toLocaleString()}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedApproval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-surface-border bg-surface-darker/50">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-100">Approval Request</h2>
                  <p className="text-sm text-slate-400">{selectedApproval.summary}</p>
                </div>
                <button
                  onClick={() => { setSelectedApproval(null); setEditData(null); }}
                  className="p-2 hover:bg-surface-border rounded-lg transition-colors"
                >
                  <XCircle className="w-5 h-5 text-slate-400" />
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <div className="space-y-4">
                {/* Context */}
                <div className="glass-panel p-4">
                  <h4 className="text-xs font-bold font-mono text-slate-400 uppercase mb-2">Request Context</h4>
                  <pre className="text-[10px] font-mono text-slate-300 bg-slate-900 p-3 rounded overflow-x-auto">
                    {JSON.stringify(selectedApproval.context_snapshot, null, 2)}
                  </pre>
                </div>

                {/* AI Analysis */}
                {selectedApproval.ai_risk_summary && (
                  <div className="glass-panel p-4 border-platform-500/20">
                    <h4 className="text-xs font-bold font-mono text-platform-400 uppercase mb-2">AI Risk Analysis</h4>
                    <p className="text-sm text-slate-300">{selectedApproval.ai_risk_summary}</p>
                  </div>
                )}

                {/* Edit Mode */}
                {editData && (
                  <div className="glass-panel p-4 border-amber-500/20">
                    <h4 className="text-xs font-bold font-mono text-amber-400 uppercase mb-2">Edit Before Approval</h4>
                    <textarea
                      value={editData.reason || ""}
                      onChange={(e) => setEditData({ ...editData, reason: e.target.value })}
                      placeholder="Add reason for modification request..."
                      className="w-full p-3 bg-slate-900 border border-surface-border rounded text-sm text-slate-200 font-mono focus:border-platform-500 focus:outline-none"
                      rows={3}
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
              <button
                onClick={() => setShowAuditHistory(!showAuditHistory)}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-mono transition-colors flex items-center gap-2"
              >
                <History className="w-4 h-4" /> Audit History
              </button>
              <button
                onClick={() => setEditData({ reason: "", modifications: {} })}
                className="px-4 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-500/20 rounded-lg text-xs font-mono transition-colors flex items-center gap-2"
              >
                <FileEdit className="w-4 h-4" /> Edit & Request Modification
              </button>
              <button
                onClick={() => handleDecision("rejected")}
                disabled={decideMutation.isPending}
                className="flex-1 px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/20 rounded-lg text-xs font-mono transition-colors disabled:opacity-50"
              >
                Reject
              </button>
              <button
                onClick={() => handleDecision("approved")}
                disabled={decideMutation.isPending}
                className="flex-1 px-4 py-2 bg-emerald-600/80 hover:bg-emerald-600 text-slate-100 rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
              >
                {decideMutation.isPending ? "Processing..." : "Approve"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}