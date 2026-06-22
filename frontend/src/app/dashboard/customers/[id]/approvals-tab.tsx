"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { CheckCircle2, XCircle, AlertTriangle, Clock, FileText, TrendingUp } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

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
}

function getRiskBadge(riskLevel: string) {
  const config: Record<string, { color: string; label: string; icon: any }> = {
    critical: { color: "bg-red-500/10 text-red-400 border-red-500/20", label: "CRITICAL", icon: AlertTriangle },
    high: { color: "bg-orange-500/10 text-orange-400 border-orange-500/20", label: "HIGH", icon: AlertTriangle },
    medium: { color: "bg-amber-500/10 text-amber-400 border-amber-500/20", label: "MEDIUM", icon: Clock },
    low: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20", label: "LOW", icon: FileText },
  };
  
  const { color, label, icon: Icon } = config[riskLevel] || config.low;
  
  return (
    <span className={`px-2 py-1 text-[10px] font-mono rounded border ${color} flex items-center gap-1`}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}

function getCategoryBadge(category: string) {
  const config: Record<string, { color: string; icon: any }> = {
    outreach_email: { color: "bg-blue-500/10 text-blue-400 border-blue-500/20", icon: FileText },
    prospect_approval: { color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", icon: CheckCircle2 },
    campaign_launch: { color: "bg-purple-500/10 text-purple-400 border-purple-500/20", icon: TrendingUp },
    default: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20", icon: FileText },
  };
  
  const { color, icon: Icon } = config[category] || config.default;
  
  return (
    <span className={`px-2 py-1 text-[10px] font-mono rounded border ${color} flex items-center gap-1`}>
      <Icon className="w-3 h-3" />
      {safeUpper(safeReplace(category, "_", " "))}
    </span>
  );
}

export function ApprovalsTab({ customerId }: { customerId: string }) {
  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data: approvals = [], isLoading, error } = useQuery<ApprovalRequest[]>({
    queryKey: ["customer", customerId, "approvals"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/approvals?tenant_id=${tenantId}&status=pending`);
      return response?.data || [];
    },
    refetchInterval: 30000,
  });

  // Filter approvals for this customer's campaigns
  const { data: campaigns = [] } = useQuery<any[]>({
    queryKey: ["customer", customerId, "campaigns"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/business-intelligence/intelligence/campaigns?tenant_id=${tenantId}`);
      return (response?.data?.campaigns || []).filter((c: any) => c.client_id === customerId);
    },
  });

  const campaignIds = new Set(safeArr<any>(campaigns).map((c: any) => c.id));
  const filteredApprovals = safeArr<ApprovalRequest>(approvals).filter((a: ApprovalRequest) => {
    const ctx = a.context_snapshot || {};
    return !ctx.campaign_id || campaignIds.has(ctx.campaign_id);
  });

  const stats = {
    total: safeArr<ApprovalRequest>(filteredApprovals).length,
    critical: safeArr<ApprovalRequest>(filteredApprovals).filter((a) => a.risk_level === "critical").length,
    high: safeArr<ApprovalRequest>(filteredApprovals).filter((a) => a.risk_level === "high").length,
    pending: safeArr<ApprovalRequest>(filteredApprovals).filter((a) => a.status === "pending").length,
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center p-8 glass-panel">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Failed to load approvals</h3>
          <p className="text-xs text-slate-500 mb-4">{(error as Error).message}</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-center p-8 glass-panel">
          <CheckCircle2 className="w-12 h-12 text-platform-500 animate-spin mx-auto mb-3" />
          <p className="text-xs font-mono text-slate-500">Loading approvals...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Total
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
        <div className="glass-panel p-4 border-amber-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-amber-500 uppercase mb-2">
            <Clock className="w-3.5 h-3.5" /> Pending
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400">{stats.pending}</p>
        </div>
      </div>

      {/* Approvals List */}
      {safeArr<ApprovalRequest>(filteredApprovals).length === 0 ? (
        <div className="glass-panel p-8 text-center">
          <CheckCircle2 className="w-12 h-12 text-slate-700 mx-auto mb-3" />
          <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Pending Approvals</h3>
          <p className="text-xs text-slate-500">All clear! No approvals waiting for your decision.</p>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="divide-y divide-surface-border">
            {safeArr<ApprovalRequest>(filteredApprovals).map((approval) => (
              <div key={approval.id} className="p-4 hover:bg-surface-border/20 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      {getCategoryBadge(approval.category)}
                      {getRiskBadge(approval.risk_level)}
                      {approval.escalation_count > 0 && (
                        <span className="px-1.5 py-0.5 text-[8px] font-mono rounded border bg-red-500/10 text-red-400 border-red-500/20">
                          {approval.escalation_count} ESCALATION{approval.escalation_count > 1 ? "S" : ""}
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm font-bold font-mono text-slate-200 mb-1">{approval.summary}</h4>
                    {approval.ai_risk_summary && (
                      <p className="text-[10px] text-slate-500 mb-2">{approval.ai_risk_summary}</p>
                    )}
                  </div>
                </div>

                {/* Details */}
                <div className="flex items-center justify-between text-[10px] font-mono text-slate-600">
                  <div className="flex items-center gap-4">
                    <span>Workflow: {safeSlice(approval.workflow_run_id, 0, 8)}...</span>
                    {approval.sla_deadline && (
                      <span className="flex items-center gap-1 text-amber-500">
                        <Clock className="w-3 h-3" />
                        Due: {new Date(approval.sla_deadline).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="px-3 py-1 text-[9px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors">
                      APPROVE
                    </button>
                    <button className="px-3 py-1 text-[9px] font-mono rounded bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors">
                      REJECT
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}