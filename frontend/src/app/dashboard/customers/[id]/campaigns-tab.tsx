"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { GitBranch, TrendingUp, AlertTriangle, CheckCircle2, Play, Pause, FileText } from "lucide-react";
import { useRouter } from "next/navigation";

interface Campaign {
  id: string;
  name: string;
  status: string;
  campaign_type: string;
  health_score: number;
  target_link_count: number;
  acquired_link_count: number;
  total_prospects: number;
  created_at: string;
  client_name?: string;
}

function getStatusBadge(status: string) {
  const statusConfig: Record<string, { color: string; label: string; icon: any }> = {
    draft: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20", label: "DRAFT", icon: FileText },
    prospecting: { color: "bg-blue-500/10 text-blue-400 border-blue-500/20", label: "PROSPECTING", icon: TrendingUp },
    active: { color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", label: "ACTIVE", icon: Play },
    monitoring: { color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20", label: "MONITORING", icon: CheckCircle2 },
    complete: { color: "bg-green-500/10 text-green-400 border-green-500/20", label: "COMPLETE", icon: CheckCircle2 },
    paused: { color: "bg-amber-500/10 text-amber-400 border-amber-500/20", label: "PAUSED", icon: Pause },
    stalled: { color: "bg-red-500/10 text-red-400 border-red-500/20", label: "STALLED", icon: AlertTriangle },
  };
  
  const config = statusConfig[status] || statusConfig.draft;
  const Icon = config.icon;
  
  return (
    <span className={`px-2 py-1 text-[10px] font-mono rounded border ${config.color} flex items-center gap-1`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
}

function getHealthColor(score: number) {
  if (score >= 0.7) return "text-emerald-400";
  if (score >= 0.4) return "text-amber-400";
  return "text-red-400";
}

function getHealthBg(score: number) {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

export function CampaignManagementTab({ customerId }: { customerId: string }) {
  const router = useRouter();
  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data: campaigns = [], isLoading, error } = useQuery<Campaign[]>({
    queryKey: ["customer", customerId, "campaigns"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/business-intelligence/intelligence/campaigns?tenant_id=${tenantId}`);
      const allCampaigns = response?.data?.campaigns || [];
      return allCampaigns.filter((c: Campaign) => c.client_id === customerId);
    },
    refetchInterval: 30000,
  });

  const stats = {
    total: campaigns.length,
    active: campaigns.filter((c) => c.status === "active" || c.status === "monitoring").length,
    draft: campaigns.filter((c) => c.status === "draft").length,
    complete: campaigns.filter((c) => c.status === "complete").length,
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center p-8 glass-panel">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Failed to load campaigns</h3>
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
          <GitBranch className="w-12 h-12 text-platform-500 animate-spin mx-auto mb-3" />
          <p className="text-xs font-mono text-slate-500">Loading campaigns...</p>
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
            <GitBranch className="w-3.5 h-3.5" /> Total
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{stats.total}</p>
        </div>
        <div className="glass-panel p-4 border-emerald-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-500 uppercase mb-2">
            <Play className="w-3.5 h-3.5" /> Active
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">{stats.active}</p>
        </div>
        <div className="glass-panel p-4 border-slate-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Draft
          </div>
          <p className="text-2xl font-bold font-mono text-slate-300">{stats.draft}</p>
        </div>
        <div className="glass-panel p-4 border-green-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-green-500 uppercase mb-2">
            <CheckCircle2 className="w-3.5 h-3.5" /> Complete
          </div>
          <p className="text-2xl font-bold font-mono text-green-400">{stats.complete}</p>
        </div>
      </div>

      {/* Campaigns List */}
      {campaigns.length === 0 ? (
        <div className="glass-panel p-8 text-center">
          <GitBranch className="w-12 h-12 text-slate-700 mx-auto mb-3" />
          <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Campaigns Yet</h3>
          <p className="text-xs text-slate-500 mb-4">Create your first campaign to start acquiring backlinks</p>
          <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors">
            Create Campaign
          </button>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="divide-y divide-surface-border">
            {campaigns.map((campaign) => (
              <div 
                key={campaign.id}
                className="p-4 hover:bg-surface-border/20 transition-colors cursor-pointer"
                onClick={() => router.push(`/dashboard/campaigns/${campaign.id}`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-bold font-mono text-slate-200">{campaign.name}</h3>
                      {getStatusBadge(campaign.status)}
                    </div>
                    <p className="text-[10px] font-mono text-slate-500">
                      {campaign.campaign_type.replace("_", " ").toUpperCase()}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-mono text-slate-500 mb-1">Health</div>
                    <div className={`text-sm font-bold font-mono ${getHealthColor(campaign.health_score)}`}>
                      {(campaign.health_score * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>

                {/* Progress */}
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex-1 h-2 bg-surface-darker rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${getHealthBg(campaign.health_score)}`}
                          style={{ width: `${(campaign.acquired_link_count / Math.max(campaign.target_link_count, 1)) * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">
                        {campaign.acquired_link_count} / {campaign.target_link_count} links
                      </span>
                    </div>
                  </div>
                </div>

                {/* Metrics */}
                <div className="flex items-center gap-4 text-[10px] font-mono text-slate-600">
                  <span className="flex items-center gap-1">
                    <GitBranch className="w-3 h-3 text-platform-500" />
                    {campaign.total_prospects} prospects
                  </span>
                  <span className="flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                    {(campaign.acquired_link_count / Math.max(campaign.total_prospects, 1) * 100).toFixed(1)}% conversion
                  </span>
                  <span className="text-slate-500">
                    Created: {new Date(campaign.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}