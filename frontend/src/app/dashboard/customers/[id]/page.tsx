"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api";
import { ErrorState, LoadingState } from "@/components/ui/error-state";
import { safeNum, safeStr, safeUpper, safeReplace, safeFixed, safeLocale, safeInitials } from "@/lib/safe";
import { CampaignManagementTab } from "./campaigns-tab";
import { CommunicationsTab } from "./communications-tab";
import { OpportunitiesTab } from "./opportunities-tab";
import { ApprovalsTab } from "./approvals-tab";
import { KeywordsTab } from "./keywords-tab";
import { ReportsTab } from "./reports-tab";
import { AutomationsTab } from "./automations-tab";
import { TimelineTab } from "./timeline-tab";
import { AssetsTab } from "./assets-tab";
import { HealthTab } from "./health-tab";
import { RiskTab } from "./risk-tab";
import {
  Activity, GitBranch, Mail, Users, Search, Plus, ArrowLeft, FileText,
  CheckCircle2, TrendingUp, Zap, Shield, AlertTriangle, Layers, FolderOpen
} from "lucide-react";

const TABS = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "campaigns", label: "Campaigns", icon: GitBranch },
  { id: "keywords", label: "Keywords", icon: Search },
  { id: "prospects", label: "Prospects", icon: Users },
  { id: "communications", label: "Communications", icon: Mail },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "approvals", label: "Approvals", icon: CheckCircle2 },
  { id: "automations", label: "Automations", icon: Zap },
  { id: "timeline", label: "Timeline", icon: TrendingUp },
  { id: "assets", label: "Assets", icon: FolderOpen },
  { id: "health", label: "Health", icon: Shield },
  { id: "risk", label: "Risk", icon: AlertTriangle },
];

interface CustomerOverview {
  customer: { id: string; name: string; domain: string };
  metrics: {
    active_campaigns: number; total_campaigns: number;
    keyword_count: number; prospect_count: number;
    approval_count: number; automation_count: number;
    communication_count: number; mrr: number;
  };
  health: { score: number; category: string; trend: string };
}

export default function CustomerWorkspace() {
  const params = useParams();
  const router = useRouter();
  const customerId = params.id as string;
  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const [activeTab, setActiveTab] = useState("overview");

  const { data: overview, isLoading, error } = useQuery<CustomerOverview>({
    queryKey: ["customer", customerId, "overview"],
    queryFn: async () => {
      const res = await fetchApi<any>(`/customers/${customerId}/overview?tenant_id=${tid}`);
      return res;
    },
    refetchInterval: 60000,
  });

  if (error) {
    return (
      <div className="p-6">
        <button onClick={() => router.push("/dashboard")} className="flex items-center gap-2 text-slate-500 hover:text-slate-300 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>
        <ErrorState error={error} message="Failed to load customer workspace" onRetry={() => window.location.reload()} />
      </div>
    );
  }

  if (isLoading || !overview) {
    return (
      <div className="p-6">
        <LoadingState message="Loading customer workspace..." size="lg" />
      </div>
    );
  }

  const { customer, metrics, health } = overview;
  const score = health.score || 0;

  const getScoreColor = (s: number) => {
    if (s >= 0.7) return "text-emerald-400";
    if (s >= 0.4) return "text-amber-400";
    return "text-red-400";
  };
  const getScoreBg = (s: number) => {
    if (s >= 0.7) return "bg-emerald-500";
    if (s >= 0.4) return "bg-amber-500";
    return "bg-red-500";
  };
  const statusCls = health.category === "healthy" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
    : health.category === "at_risk" ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
    : "bg-red-500/10 text-red-400 border-red-500/20";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push("/dashboard")} className="p-2 hover:bg-surface-border rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </button>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-lg">
              {safeInitials(customer.name, 2)}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">{customer.name}</h1>
              <p className="text-slate-500 text-sm">{customer.domain}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 text-[10px] font-mono rounded-full border ${statusCls}`}>
            {safeUpper(safeReplace(health.category, "_", " "), "UNKNOWN")}
          </span>
          <button className="px-3 py-1.5 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" /> New Campaign
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 md:grid-cols-8 gap-3">
        <div className="glass-panel p-3">
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Health</div>
          <p className={`text-xl font-bold font-mono ${getScoreColor(score)}`}>{safeFixed(safeNum(score) * 100, 0)}%</p>
        </div>
        <div className="glass-panel p-3">
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Campaigns</div>
          <p className="text-xl font-bold font-mono text-slate-100">{safeNum(metrics.active_campaigns)}/{safeNum(metrics.total_campaigns)}</p>
        </div>
        <div className="glass-panel p-3">
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Keywords</div>
          <p className="text-xl font-bold font-mono text-slate-100">{safeNum(metrics.keyword_count)}</p>
        </div>
        <div className="glass-panel p-3">
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Prospects</div>
          <p className="text-xl font-bold font-mono text-slate-100">{safeNum(metrics.prospect_count)}</p>
        </div>
        <div className="glass-panel p-3">
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Automations</div>
          <p className="text-xl font-bold font-mono text-slate-100">{safeNum(metrics.automation_count)}</p>
        </div>
        <div className="glass-panel p-3">
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Approvals</div>
          <p className="text-xl font-bold font-mono text-slate-100">{safeNum(metrics.approval_count)}</p>
        </div>
        <div className="glass-panel p-3">
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Comms</div>
          <p className="text-xl font-bold font-mono text-slate-100">{safeNum(metrics.communication_count)}</p>
        </div>
        <div className="glass-panel p-3">
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">MRR</div>
          <p className="text-xl font-bold font-mono text-emerald-400">${safeLocale(metrics.mrr)}</p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="glass-panel overflow-hidden">
        <div className="flex items-center gap-1 p-1 bg-surface-darker/50 border-b border-surface-border overflow-x-auto">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 text-xs font-mono rounded-md transition-all whitespace-nowrap ${
                  isActive ? "bg-platform-600 text-white" : "text-slate-400 hover:text-slate-200 hover:bg-surface-border"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="p-6">
          {activeTab === "overview" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="glass-panel p-4">
                  <h3 className="text-xs font-bold font-mono text-slate-300 mb-3">Campaign Summary</h3>
                  <div className="space-y-2 text-[10px] font-mono">
                    <div className="flex justify-between"><span className="text-slate-500">Total:</span><span className="text-slate-200">{safeNum(metrics.total_campaigns)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Active:</span><span className="text-emerald-400">{safeNum(metrics.active_campaigns)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Keywords:</span><span className="text-platform-400">{safeNum(metrics.keyword_count)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Prospects:</span><span className="text-slate-200">{safeNum(metrics.prospect_count)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">MRR:</span><span className="text-emerald-400">${safeLocale(metrics.mrr)}</span></div>
                  </div>
                </div>
                <div className="glass-panel p-4">
                  <h3 className="text-xs font-bold font-mono text-slate-300 mb-3">Health Score</h3>
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`text-3xl font-bold font-mono ${getScoreColor(score)}`}>{safeFixed(safeNum(score) * 100, 0)}%</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${statusCls}`}>
                      {safeUpper(safeReplace(health.category, "_", " "))}
                    </span>
                  </div>
                  <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${getScoreBg(score)}`} style={{ width: `${score * 100}%` }} />
                  </div>
                  <p className="text-[10px] font-mono text-slate-500 mt-2">Trend: {safeStr(health.trend, "stable")}</p>
                </div>
              </div>
              <div className="glass-panel p-4">
                <h3 className="text-xs font-bold font-mono text-slate-300 mb-3">Quick Actions</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  <button className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border hover:border-platform-500/50 transition-colors text-left">
                    <GitBranch className="w-4 h-4 text-emerald-400 mb-1" />
                    <p className="text-xs font-mono text-slate-300">New Campaign</p>
                    <p className="text-[9px] text-slate-600">Launch a backlink campaign</p>
                  </button>
                  <button className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border hover:border-platform-500/50 transition-colors text-left">
                    <Search className="w-4 h-4 text-platform-400 mb-1" />
                    <p className="text-xs font-mono text-slate-300">Research Keywords</p>
                    <p className="text-[9px] text-slate-600">Discover new opportunities</p>
                  </button>
                  <button className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border hover:border-platform-500/50 transition-colors text-left">
                    <Mail className="w-4 h-4 text-blue-400 mb-1" />
                    <p className="text-xs font-mono text-slate-300">Compose Email</p>
                    <p className="text-[9px] text-slate-600">Send outreach to prospects</p>
                  </button>
                  <button className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border hover:border-platform-500/50 transition-colors text-left">
                    <Zap className="w-4 h-4 text-purple-400 mb-1" />
                    <p className="text-xs font-mono text-slate-300">Create Rule</p>
                    <p className="text-[9px] text-slate-600">Add an automation rule</p>
                  </button>
                </div>
              </div>
            </div>
          )}
          {activeTab === "campaigns" && <CampaignManagementTab customerId={customerId} />}
          {activeTab === "keywords" && <KeywordsTab customerId={customerId} />}
          {activeTab === "prospects" && <OpportunitiesTab customerId={customerId} />}
          {activeTab === "communications" && <CommunicationsTab customerId={customerId} />}
          {activeTab === "reports" && <ReportsTab customerId={customerId} />}
          {activeTab === "approvals" && <ApprovalsTab customerId={customerId} />}
          {activeTab === "automations" && <AutomationsTab customerId={customerId} />}
          {activeTab === "timeline" && <TimelineTab customerId={customerId} />}
          {activeTab === "assets" && <AssetsTab customerId={customerId} />}
          {activeTab === "health" && <HealthTab customerId={customerId} />}
          {activeTab === "risk" && <RiskTab customerId={customerId} />}
        </div>
      </div>
    </div>
  );
}
