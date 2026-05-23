"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api";
import { PageGuide } from "@/components/ui/page-guide";
import { ErrorState, LoadingState } from "@/components/ui/error-state";
import { 
  TrendingUp, Activity, GitBranch, Mail, Users, 
  Search, Plus, ArrowLeft, FileText, Lightbulb,
  CheckCircle2, AlertTriangle
} from "lucide-react";

interface CustomerHealthData {
  id: string;
  name: string;
  domain: string;
  niche: string;
  business_type: string | null;
  health_score: number;
  active_campaigns: number;
  total_keywords: number;
  links_acquired: number;
  reply_rate: number;
  status: "healthy" | "at_risk" | "critical";
}

interface CampaignStats {
  total: number;
  active: number;
  draft: number;
  complete: number;
  avg_health: number;
}

export default function CustomerWorkspace() {
  const params = useParams();
  const router = useRouter();
  const customerId = params.id as string;
  
  const [activeTab, setActiveTab] = useState<"overview" | "campaigns" | "communications" | "opportunities">("overview");

  // Fetch customer data
  const { data: customer, isLoading: loadingCustomer, error: customerError } = useQuery<CustomerHealthData>({
    queryKey: ["customer", customerId],
    queryFn: async () => {
      const clientsResponse = await fetchApi<any>(`/clients?tenant_id=${process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001"}`);
      const clients = clientsResponse?.data || [];
      const client = clients.find((c: any) => c.id === customerId);
      
      if (!client) {
        throw new Error("Customer not found");
      }

      // Fetch campaign data for this client
      const campaignsResponse = await fetchApi<any>(`/business-intelligence/intelligence/campaigns?tenant_id=${process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001"}`);
      const campaigns = campaignsResponse?.data?.campaigns || [];
      
      const clientCampaigns = campaigns.filter((c: any) => c.client_id === customerId);
      const activeCampaigns = clientCampaigns.filter((c: any) => c.status === "active" || c.status === "monitoring");
      const avgHealth = clientCampaigns.length > 0 
        ? clientCampaigns.reduce((sum: number, c: any) => sum + c.health_score, 0) / clientCampaigns.length
        : 0;

      return {
        id: client.id,
        name: client.name,
        domain: client.domain,
        niche: client.niche || "Not specified",
        business_type: client.business_type,
        health_score: avgHealth,
        active_campaigns: activeCampaigns.length,
        total_keywords: client.keyword_count || 0,
        links_acquired: clientCampaigns.reduce((sum: number, c: any) => sum + c.acquired_link_count, 0),
        reply_rate: 0.18,
        status: avgHealth >= 0.7 ? "healthy" : avgHealth >= 0.4 ? "at_risk" : "critical",
      };
    },
    refetchInterval: 60000,
  });

  // Fetch campaign stats
  const { data: campaignStats } = useQuery<CampaignStats>({
    queryKey: ["customer", customerId, "campaigns", "stats"],
    queryFn: async () => {
      const campaignsResponse = await fetchApi<any>(`/business-intelligence/intelligence/campaigns?tenant_id=${process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001"}`);
      const campaigns = campaignsResponse?.data?.campaigns || [];
      const clientCampaigns = campaigns.filter((c: any) => c.client_id === customerId);
      
      return {
        total: clientCampaigns.length,
        active: clientCampaigns.filter((c: any) => c.status === "active" || c.status === "monitoring").length,
        draft: clientCampaigns.filter((c: any) => c.status === "draft").length,
        complete: clientCampaigns.filter((c: any) => c.status === "complete").length,
        avg_health: clientCampaigns.length > 0 
          ? clientCampaigns.reduce((sum: number, c: any) => sum + c.health_score, 0) / clientCampaigns.length
          : 0,
      };
    },
    enabled: !!customerId,
  });

  if (customerError) {
    return (
      <div className="p-6">
        <button 
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-2 text-slate-500 hover:text-slate-300 mb-4"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>
        <ErrorState 
          error={customerError} 
          message="Failed to load customer workspace"
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  if (loadingCustomer || !customer) {
    return (
      <div className="p-6">
        <LoadingState message="Loading customer workspace..." size="lg" />
      </div>
    );
  }

  const getHealthColor = (score: number) => {
    if (score >= 0.7) return "text-emerald-400";
    if (score >= 0.4) return "text-amber-400";
    return "text-red-400";
  };

  const getHealthBg = (score: number) => {
    if (score >= 0.7) return "bg-emerald-500";
    if (score >= 0.4) return "bg-amber-500";
    return "bg-red-500";
  };

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "campaigns", label: "Campaigns", icon: GitBranch },
    { id: "communications", label: "Communications", icon: Mail },
    { id: "opportunities", label: "Opportunities", icon: Lightbulb },
  ];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.push("/dashboard")}
            className="p-2 hover:bg-surface-border rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </button>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-lg">
              {customer.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">{customer.name}</h1>
              <p className="text-slate-500 text-sm">
                {customer.domain} · {customer.niche}
                {customer.business_type && (
                  <>
                    <span className="mx-2">·</span>
                    <span className="text-slate-400">{customer.business_type}</span>
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" /> New Campaign
          </button>
          <button className="px-3 py-1.5 bg-surface-darker border border-surface-border text-slate-300 hover:text-slate-200 rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-1.5">
            <Search className="w-3.5 h-3.5" /> Discover Keywords
          </button>
        </div>
      </div>

      {/* Health Score Banner */}
      <div className="glass-panel p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-bold font-mono text-slate-200 uppercase">Customer Health</h2>
          </div>
          <span className={`px-2 py-1 text-[10px] font-mono rounded-full border ${
            customer.status === "healthy" 
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
              : customer.status === "at_risk"
              ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
              : "bg-red-500/10 text-red-400 border-red-500/20"
          }`}>
            {customer.status.toUpperCase().replace("_", " ")}
          </span>
        </div>
        <div className="flex items-end gap-3 mb-2">
          <span className={`text-4xl font-bold font-mono ${getHealthColor(customer.health_score)}`}>
            {(customer.health_score * 100).toFixed(0)}%
          </span>
          <span className="text-sm text-slate-500 mb-1">health score</span>
        </div>
        <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
          <div 
            className={`h-full rounded-full transition-all ${getHealthBg(customer.health_score)}`}
            style={{ width: `${customer.health_score * 100}%` }}
          />
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <GitBranch className="w-3.5 h-3.5 text-emerald-400" /> Active Campaigns
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{customer.active_campaigns}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Search className="w-3.5 h-3.5 text-platform-400" /> Keywords
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{customer.total_keywords}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Users className="w-3.5 h-3.5 text-amber-400" /> Links Acquired
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{customer.links_acquired}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Mail className="w-3.5 h-3.5 text-blue-400" /> Reply Rate
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{(customer.reply_rate * 100).toFixed(1)}%</p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="glass-panel overflow-hidden">
        <div className="flex items-center gap-1 p-1 bg-surface-darker/50 border-b border-surface-border">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 text-xs font-mono rounded-md transition-all ${
                  isActive 
                    ? "bg-platform-600 text-white" 
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-border"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === "overview" && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-mono text-slate-400">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Overview tab ready for content
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="glass-panel p-4">
                  <h3 className="text-xs font-bold font-mono text-slate-300 mb-2">Campaign Summary</h3>
                  {campaignStats ? (
                    <div className="space-y-2 text-[10px] font-mono">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Total:</span>
                        <span className="text-slate-200">{campaignStats.total}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Active:</span>
                        <span className="text-emerald-400">{campaignStats.active}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Draft:</span>
                        <span className="text-slate-300">{campaignStats.draft}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Complete:</span>
                        <span className="text-slate-300">{campaignStats.complete}</span>
                      </div>
                    </div>
                  ) : (
                    <LoadingState message="Loading stats..." size="sm" />
                  )}
                </div>
                <div className="glass-panel p-4">
                  <h3 className="text-xs font-bold font-mono text-slate-300 mb-2">Recent Activity</h3>
                  <div className="text-[10px] font-mono text-slate-500">
                    No recent activity
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "campaigns" && (
            <div className="text-center p-8">
              <GitBranch className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Campaign Management</h3>
              <p className="text-xs text-slate-500 mb-4">Campaign tab - Wave 2B</p>
              <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors">
                Launch Wave 2B
              </button>
            </div>
          )}

          {activeTab === "communications" && (
            <div className="text-center p-8">
              <Mail className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Communications</h3>
              <p className="text-xs text-slate-500 mb-4">Communications tab - Wave 2C</p>
              <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors">
                Launch Wave 2C
              </button>
            </div>
          )}

          {activeTab === "opportunities" && (
            <div className="text-center p-8">
              <Lightbulb className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Opportunities</h3>
              <p className="text-xs text-slate-500 mb-4">Opportunities tab - Wave 2D</p>
              <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors">
                Launch Wave 2D
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}