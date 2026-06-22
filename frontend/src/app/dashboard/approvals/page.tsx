"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Check,
  X,
  Clock,
  ShieldAlert,
  Loader2,
  AlertTriangle,
  ArrowUpCircle,
  Ban,
  Eye,
  EyeOff,
  ListChecks,
  Sparkles,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { ApprovalRequest } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/utils";

type FilterTab = "all" | "pending" | "approved" | "rejected";

interface ApprovalDashboardData {
  total_pending: number;
  total_approved: number;
  total_rejected: number;
  total_escalated: number;
  by_type: Record<string, number>;
  by_risk: Record<string, number>;
  overdue_count: number;
  recent_decisions: ApprovalRequest[];
}

interface AnalyticsData {
  approval_rate: number;
  rejection_rate: number;
  average_time_to_decision_hours: number;
  by_requester: Record<string, number>;
  rejection_reasons: { reason: string; count: number }[];
  total_decisions: number;
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
      setDisplay(`${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`);
    };
    update();
    const iv = setInterval(update, 1000);
    return () => clearInterval(iv);
  }, [deadline]);
  return display;
}

function useTimeAgo(dateStr: string): string {
  const [display, setDisplay] = useState("");
  useEffect(() => {
    const update = () => {
      const diff = Date.now() - new Date(dateStr).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 1) return setDisplay("just now");
      if (mins < 60) return setDisplay(`${mins}m ago`);
      const hours = Math.floor(mins / 60);
      if (hours < 24) return setDisplay(`${hours}h ago`);
      const days = Math.floor(hours / 24);
      setDisplay(`${days}d ago`);
    };
    update();
    const iv = setInterval(update, 60000);
    return () => clearInterval(iv);
  }, [dateStr]);
  return display;
}

function getRiskBadgeVariant(level?: string): "default" | "destructive" | "warning" | "success" | "secondary" {
  switch (level) {
    case "critical": return "destructive";
    case "high": return "warning";
    case "medium": return "default";
    case "low": return "success";
    default: return "secondary";
  }
}

function getRiskBorderColor(level?: string): string {
  switch (level) {
    case "critical": return "border-l-red-500";
    case "high": return "border-l-amber-500";
    case "medium": return "border-l-platform-500";
    case "low": return "border-l-emerald-500";
    default: return "border-l-slate-500";
  }
}

function getSlaColor(deadline: string | null): string {
  if (!deadline) return "text-slate-500";
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff <= 0) return "text-red-400 animate-pulse";
  if (diff < 3600000) return "text-amber-400";
  return "text-slate-500";
}

function ApprovalCard({
  approval, index, onApprove, onReject, onEscalate, isPending, selected, onSelectChange,
}: {
  approval: ApprovalRequest;
  index: number;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEscalate: (id: string) => void;
  isPending: boolean;
  selected: boolean;
  onSelectChange: (id: string, checked: boolean) => void;
}) {
  const slaDisplay = useCountdown(approval.sla_deadline ?? null);
  const slaColor = getSlaColor(approval.sla_deadline ?? null);
  const timeAgo = useTimeAgo(approval.created_at);
  const [confirmAction, setConfirmAction] = useState<"approve" | "reject" | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const ctx = approval.context_snapshot ?? {};
  const ctxEntries = Object.entries(ctx).filter(([, v]) => v !== null && v !== undefined && v !== "" && !(typeof v === "object" && v !== null && Object.keys(v).length === 0));

  const handleAction = (action: "approve" | "reject") => {
    if (confirmAction === action) {
      if (action === "approve") onApprove(approval.id); else onReject(approval.id);
      setConfirmAction(null);
    } else {
      setConfirmAction(action);
      setTimeout(() => setConfirmAction(null), 3000);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}
      className={cn("glass-panel p-5 border-l-4 transition-all hover:bg-surface-border/10", getRiskBorderColor(approval.risk_level))}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-surface-darker border border-surface-border flex items-center justify-center">
            <ShieldAlert className={cn("w-5 h-5", approval.risk_level === "critical" ? "text-red-500" : approval.risk_level === "high" ? "text-amber-500" : "text-platform-500")} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-slate-500 uppercase">{approval.entity_type || approval.category}</span>
              <span className="text-slate-600">·</span>
              <span className="text-[10px] font-mono text-platform-400 uppercase">{approval.action || approval.summary?.slice(0, 40)}</span>
            </div>
            <p className="text-sm text-slate-200 font-medium mt-0.5">{approval.summary || `${approval.entity_type || approval.category} ${approval.action || ""}`}</p>
          </div>
        </div>
        <Badge variant={getRiskBadgeVariant(approval.risk_level)}>{(approval.risk_level ?? "unknown").toUpperCase()}</Badge>
      </div>

      {approval.ai_risk_summary && (
        <div className="mb-3 p-3 bg-platform-900/10 border border-platform-500/10 rounded-lg">
          <p className="text-[9px] font-mono text-platform-500 uppercase mb-1 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> AI Risk Summary</p>
          <p className="text-xs text-slate-300 leading-relaxed italic">&ldquo;{approval.ai_risk_summary}&rdquo;</p>
        </div>
      )}

      <div className="flex items-center gap-2 mb-3">
        {approval.status === "pending" && (
          <label className="flex items-center gap-1.5 cursor-pointer text-[10px] font-mono text-slate-400 hover:text-slate-200 select-none">
            <input type="checkbox" checked={selected} onChange={(e) => onSelectChange(approval.id, e.target.checked)} className="w-3.5 h-3.5 rounded border-surface-border bg-surface-darker text-platform-500 focus:ring-platform-500/30" />
            Select
          </label>
        )}
        <Button size="sm" variant="ghost" onClick={() => setShowPreview((v) => !v)} className="text-slate-400 hover:text-slate-100 px-2">
          {showPreview ? <EyeOff className="w-3.5 h-3.5 mr-1" /> : <Eye className="w-3.5 h-3.5 mr-1" />}
          {showPreview ? "Hide" : "Context"}
        </Button>
      </div>

      <AnimatePresence initial={false}>
        {showPreview && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.18 }} className="mb-3 overflow-hidden">
            {ctxEntries.length > 0 && (
              <div className="p-3 bg-surface-darker/60 border border-surface-border rounded-lg">
                <p className="text-[9px] font-mono text-slate-500 uppercase mb-2 flex items-center gap-1"><ListChecks className="w-3 h-3" /> Context Snapshot</p>
                <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-[11px]">
                  {ctxEntries.map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="font-mono text-slate-500 uppercase text-[10px] pt-0.5">{k.replace(/_/g, " ")}</dt>
                      <dd className="text-slate-300 break-words font-mono text-[10px]">{typeof v === "object" ? JSON.stringify(v) : String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500 mb-3">
        <span>{timeAgo}</span>
        {approval.sla_deadline && <span className={cn("flex items-center gap-1", slaColor)}><Clock className="w-3 h-3" /> SLA: {slaDisplay}</span>}
        {(approval.escalation_count ?? 0) > 0 && <span className="text-red-400 flex items-center gap-1"><Ban className="w-3 h-3" /> Escalated {approval.escalation_count}x</span>}
      </div>

      {approval.status === "pending" && (
        <div className="flex items-center gap-2 pt-3 border-t border-surface-border/50">
          <Button size="sm" variant={confirmAction === "approve" ? "default" : "outline"} className={cn("flex-1", confirmAction === "approve" && "bg-emerald-600 hover:bg-emerald-500 text-white")} onClick={() => handleAction("approve")} disabled={isPending}>
            {isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <Check className="w-3.5 h-3.5 mr-1" />}
            {confirmAction === "approve" ? "Confirm?" : "Approve"}
          </Button>
          <Button size="sm" variant={confirmAction === "reject" ? "destructive" : "outline"} className="flex-1" onClick={() => handleAction("reject")} disabled={isPending}>
            <X className="w-3.5 h-3.5 mr-1" />
            {confirmAction === "reject" ? "Confirm?" : "Reject"}
          </Button>
          <Button size="sm" variant="outline" className="text-amber-400 border-amber-500/20 hover:bg-amber-500/10" onClick={() => onEscalate(approval.id)} disabled={isPending}>
            <ArrowUpCircle className="w-3.5 h-3.5 mr-1" /> Escalate
          </Button>
        </div>
      )}
      {approval.status !== "pending" && (
        <div className="pt-3 border-t border-surface-border/50">
          <Badge variant={approval.status === "approved" ? "success" : "destructive"}>{approval.status.toUpperCase()}</Badge>
        </div>
      )}
    </motion.div>
  );
}

export default function ApprovalCenterPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [bulkConfirm, setBulkConfirm] = useState<"approve" | "reject" | null>(null);

  const { data: dashboard } = useQuery<ApprovalDashboardData>({
    queryKey: ["approval-workflow-dashboard"],
    queryFn: () => fetchApi(`/approval-workflow/dashboard?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: approvals = [], isLoading } = useQuery<ApprovalRequest[]>({
    queryKey: ["approval-workflow-pending"],
    queryFn: () => fetchApi(`/approvals?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 10000,
  });

  const { data: analytics } = useQuery<AnalyticsData>({
    queryKey: ["approval-workflow-analytics"],
    queryFn: () => fetchApi(`/approval-workflow/analytics?tenant_id=${MOCK_TENANT_ID}`),
    enabled: showAnalytics,
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      fetchApi(`/approval-workflow/${id}/approve?tenant_id=${MOCK_TENANT_ID}`, { method: "POST", body: JSON.stringify({ notes: notes || "" }) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["approval-workflow-dashboard"] }); queryClient.invalidateQueries({ queryKey: ["approval-workflow-pending"] }); queryClient.invalidateQueries({ queryKey: ["approval-workflow-analytics"] }); },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      fetchApi(`/approval-workflow/${id}/reject?tenant_id=${MOCK_TENANT_ID}`, { method: "POST", body: JSON.stringify({ reason }) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["approval-workflow-dashboard"] }); queryClient.invalidateQueries({ queryKey: ["approval-workflow-pending"] }); queryClient.invalidateQueries({ queryKey: ["approval-workflow-analytics"] }); },
  });

  const escalateMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      fetchApi(`/approval-workflow/${id}/escalate?tenant_id=${MOCK_TENANT_ID}`, { method: "POST", body: JSON.stringify({ reason }) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["approval-workflow-dashboard"] }); queryClient.invalidateQueries({ queryKey: ["approval-workflow-pending"] }); },
  });

  const bulkApproveMutation = useMutation({
    mutationFn: ({ ids, notes }: { ids: string[]; notes: string }) =>
      fetchApi(`/approval-workflow/bulk-approve?tenant_id=${MOCK_TENANT_ID}`, { method: "POST", body: JSON.stringify({ approval_ids: ids, notes }) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["approval-workflow-dashboard"] }); queryClient.invalidateQueries({ queryKey: ["approval-workflow-pending"] }); setSelectedIds(new Set()); setBulkConfirm(null); },
  });

  const filteredApprovals = (approvals as ApprovalRequest[]).filter((a) => activeTab === "all" ? true : a.status === activeTab);
  const pendingCount = dashboard?.total_pending ?? (approvals as ApprovalRequest[]).filter((a) => a.status === "pending").length;
  const pendingIds = filteredApprovals.filter((a) => a.status === "pending").map((a) => a.id);
  const allPendingSelected = pendingIds.length > 0 && pendingIds.every((id) => selectedIds.has(id));

  const handleSelectAll = () => { allPendingSelected ? setSelectedIds(new Set()) : setSelectedIds(new Set(pendingIds)); };
  const handleBulkApprove = () => { if (bulkConfirm === "approve") { bulkApproveMutation.mutate({ ids: Array.from(selectedIds), notes: "Bulk approved" }); } else { setBulkConfirm("approve"); setTimeout(() => setBulkConfirm(null), 3000); } };

  const tabs: { key: FilterTab; label: string; count: number }[] = [
    { key: "all", label: "All", count: approvals.length },
    { key: "pending", label: "Pending", count: pendingCount },
    { key: "approved", label: "Approved", count: dashboard?.total_approved ?? 0 },
    { key: "rejected", label: "Rejected", count: dashboard?.total_rejected ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Approvals</h1>
          <p className="text-slate-400 mt-1 text-sm">Review, approve, or reject pending actions.</p>
        </div>
        <div className="flex items-center gap-3">
          {(dashboard?.overdue_count ?? 0) > 0 && <Badge variant="destructive"><AlertTriangle className="w-3 h-3 mr-1" />{dashboard!.overdue_count} overdue</Badge>}
          {pendingCount > 0 && <Badge variant="warning">{pendingCount} pending</Badge>}
          <Button size="sm" variant="outline" onClick={() => setShowAnalytics(!showAnalytics)}>
            <Sparkles className="w-3.5 h-3.5 mr-1" />{showAnalytics ? "Hide" : "Show"} Analytics
          </Button>
        </div>
      </div>

      {dashboard && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[{ label: "Pending", count: dashboard.total_pending, icon: Clock, color: "text-amber-400" },
            { label: "Approved", count: dashboard.total_approved, icon: Check, color: "text-emerald-400" },
            { label: "Rejected", count: dashboard.total_rejected, icon: X, color: "text-red-400" },
            { label: "Overdue", count: dashboard.overdue_count, icon: AlertTriangle, color: "text-slate-100" },
          ].map((s) => (
            <div key={s.label} className="glass-panel p-4 rounded-xl border border-surface-border">
              <div className="flex items-center gap-2 mb-2"><s.icon className={cn("w-4 h-4", s.color)} /><span className="text-[10px] font-mono text-slate-500 uppercase">{s.label}</span></div>
              <p className={cn("text-2xl font-bold font-mono", s.color)}>{s.count}</p>
            </div>
          ))}
        </div>
      )}

      <AnimatePresence>
        {showAnalytics && analytics && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
            <div className="glass-panel p-5 rounded-xl border border-surface-border">
              <h3 className="text-sm font-mono text-slate-400 uppercase mb-4 flex items-center gap-2"><Sparkles className="w-4 h-4 text-platform-400" /> Approval Analytics</h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div><p className="text-[10px] font-mono text-slate-500 uppercase">Approval Rate</p><p className="text-xl font-bold text-emerald-400">{analytics.approval_rate}%</p></div>
                <div><p className="text-[10px] font-mono text-slate-500 uppercase">Rejection Rate</p><p className="text-xl font-bold text-red-400">{analytics.rejection_rate}%</p></div>
                <div><p className="text-[10px] font-mono text-slate-500 uppercase">Avg Time to Decision</p><p className="text-xl font-bold text-platform-400">{analytics.average_time_to_decision_hours}h</p></div>
                <div><p className="text-[10px] font-mono text-slate-500 uppercase">Total Decisions</p><p className="text-xl font-bold text-slate-100">{analytics.total_decisions}</p></div>
              </div>
              {analytics.rejection_reasons.length > 0 && (
                <div className="mt-4 pt-4 border-t border-surface-border">
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Top Rejection Reasons</p>
                  <div className="flex flex-wrap gap-2">{analytics.rejection_reasons.map((r, i) => (<span key={i} className="px-2 py-1 bg-red-500/10 border border-red-500/20 rounded text-[10px] font-mono text-red-300">{r.reason} ({r.count})</span>))}</div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {selectedIds.size > 0 && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="glass-panel p-3 flex items-center justify-between border-platform-500/30">
            <span className="text-xs font-mono text-platform-400 uppercase">{selectedIds.size} selected</span>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => setSelectedIds(new Set())}>Clear</Button>
              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-500 text-white" onClick={handleBulkApprove} disabled={bulkApproveMutation.isPending}>
                <Check className="w-3.5 h-3.5 mr-1" />{bulkConfirm === "approve" ? "Confirm?" : "Approve All"}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 bg-surface-darker/50 border border-surface-border rounded-lg p-1 w-fit">
          {tabs.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} className={cn("px-4 py-2 rounded-md text-xs font-mono transition-all", activeTab === tab.key ? "bg-platform-600 text-white shadow-lg shadow-platform-900/20" : "text-slate-400 hover:text-slate-200 hover:bg-surface-border/30")}>
              {tab.label}{tab.count > 0 && <span className={cn("ml-1.5 px-1.5 py-0.5 rounded-full text-[9px] font-bold", activeTab === tab.key ? "bg-white/20" : "bg-surface-border text-slate-500")}>{tab.count}</span>}
            </button>
          ))}
        </div>
        {pendingIds.length > 0 && (
          <label className="flex items-center gap-2 cursor-pointer text-[10px] font-mono text-slate-400 hover:text-slate-200 select-none">
            <input type="checkbox" checked={allPendingSelected} onChange={handleSelectAll} className="w-3.5 h-3.5 rounded border-surface-border bg-surface-darker text-platform-500 focus:ring-platform-500/30" />
            Select all pending
          </label>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 text-platform-500 animate-spin" /></div>
      ) : filteredApprovals.length === 0 ? (
        <EmptyState icon={<Check className="w-8 h-8" />} title={activeTab === "pending" ? "No pending approvals" : "No approvals found"} description="All caught up!" />
      ) : (
        <div className="space-y-3">
          {filteredApprovals.map((approval, index) => (
            <ApprovalCard key={approval.id} approval={approval} index={index}
              onApprove={(id) => approveMutation.mutate({ id, notes: "" })}
              onReject={(id) => rejectMutation.mutate({ id, reason: "Rejected from dashboard" })}
              onEscalate={(id) => escalateMutation.mutate({ id, reason: "Escalated from dashboard" })}
              isPending={approveMutation.isPending || rejectMutation.isPending || escalateMutation.isPending}
              selected={selectedIds.has(approval.id)}
              onSelectChange={(id, checked) => setSelectedIds((prev) => { const next = new Set(prev); checked ? next.add(id) : next.delete(id); return next; })}
            />
          ))}
        </div>
      )}
    </div>
  );
}
