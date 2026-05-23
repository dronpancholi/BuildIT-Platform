"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useCommandCenter } from "@/hooks/use-command-center";
import { useClient } from "@/hooks/use-client";
import { WorkQueue } from "@/components/unified/work-queue";
import { CustomerHealthOverview } from "@/components/unified/customer-health-overview";
import { PageGuide } from "@/components/ui/page-guide";
import { Rocket, Plus, Sparkles, GitBranch, AlertTriangle, TrendingUp, Link2, Users } from "lucide-react";

export default function UnifiedDashboard() {
  const { openCommand } = useCommandCenter();
  const client = useClient();
  const [showSetup, setShowSetup] = useState(false);

  const { data: overview } = useQuery<any>({
    queryKey: ["bi-overview"],
    queryFn: () => fetchApi("/business-intelligence/intelligence/overview"),
    refetchInterval: 60000,
  });

  const stats = overview?.campaigns || {};
  const activeCampaigns = stats.active ?? 0;
  const totalKeywords = overview?.keywords?.total ?? 0;
  const totalLinks = stats.total_links_acquired ?? 0;
  const avgHealth = stats.avg_health ?? 0;
  const events24h = overview?.intelligence?.events_24h ?? 0;

  const hasData = activeCampaigns > 0 || totalKeywords > 0 || totalLinks > 0;

  return (
    <div className="space-y-4">
      {/* Page Guide */}
      <PageGuide title="About Unified Dashboard" defaultOpen={!hasData}>
        <p><strong>Unified Dashboard</strong> is your single operational workspace for managing all customers and campaigns. It shows:</p>
        <ul className="list-disc list-inside space-y-1 mt-2 text-slate-400">
          <li>Work Queue - All pending approvals, follow-ups, and alerts in one place</li>
          <li>Customer Health - Portfolio overview with health scores and key metrics</li>
          <li>Quick Actions - Create campaigns, discover keywords, add customers</li>
        </ul>
        <p className="mt-2">This replaces the old fragmented dashboard with a unified view designed for managing 100+ customers efficiently.</p>
      </PageGuide>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-sm">
              {client.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">{client.name}</h1>
              <p className="text-slate-500 text-sm">
                {client.niche} · {client.domain}
                {hasData && (
                  <>
                    <span className="mx-2">·</span>
                    <span className="flex items-center gap-1">
                      <TrendingUp className="w-3 h-3 text-emerald-400" />
                      Health <span className="text-emerald-400 font-mono">{(avgHealth * 100).toFixed(0)}%</span>
                    </span>
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!hasData && (
            <button 
              onClick={() => setShowSetup(true)} 
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-bold font-mono transition-all flex items-center gap-2"
            >
              <Rocket className="w-3.5 h-3.5" /> Guided Setup
            </button>
          )}
          <button 
            onClick={() => openCommand("keyword_discovery")} 
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" /> Discover Keywords
          </button>
          <button 
            onClick={() => openCommand("create_campaign")} 
            className="px-3 py-1.5 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-1.5"
          >
            <GitBranch className="w-3.5 h-3.5" /> New Campaign
          </button>
          <button 
            onClick={() => openCommand("add_client")} 
            className="px-3 py-1.5 bg-surface-darker border border-surface-border text-slate-300 hover:text-slate-200 rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> Add Customer
          </button>
        </div>
      </div>

      {/* Welcome Banner for Empty State */}
      {!hasData && (
        <div className="glass-panel border-emerald-500/20 bg-emerald-500/5 p-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <Rocket className="w-6 h-6 text-emerald-400" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-bold text-slate-100 mb-1">Welcome to BuildIT</h2>
              <p className="text-sm text-slate-400 mb-4">
                Your unified operational workspace for managing SEO campaigns at scale.
              </p>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => setShowSetup(true)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold font-mono transition-all flex items-center gap-2"
                >
                  <Rocket className="w-4 h-4" /> Guided Setup
                </button>
                <button
                  onClick={() => openCommand("add_client")}
                  className="px-4 py-2 bg-surface-darker border border-surface-border text-slate-300 hover:text-slate-200 rounded-lg text-xs font-bold font-mono transition-all flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" /> Add Customer Manually
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Left Column - Work Queue */}
        <div className="xl:col-span-2">
          <WorkQueue />
        </div>

        {/* Right Column - Customer Health */}
        <div>
          <CustomerHealthOverview />
        </div>
      </div>

      {/* Quick Stats Row */}
      {hasData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="glass-panel p-4">
            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
              <GitBranch className="w-3.5 h-3.5 text-emerald-400" /> Active Campaigns
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{activeCampaigns}</p>
          </div>
          <div className="glass-panel p-4">
            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
              <Sparkles className="w-3.5 h-3.5 text-platform-400" /> Keywords Tracked
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{totalKeywords}</p>
          </div>
          <div className="glass-panel p-4">
            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Opportunities
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{events24h}</p>
          </div>
          <div className="glass-panel p-4">
            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
              <Users className="w-3.5 h-3.5 text-indigo-400" /> Links Acquired
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{totalLinks}</p>
          </div>
        </div>
      )}
    </div>
  );
}