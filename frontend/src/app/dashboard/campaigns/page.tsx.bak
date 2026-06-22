"use client";

import { useState, useMemo, Fragment } from "react";
import { motion } from "framer-motion";
import {
  Plus, Search, Loader2, GitBranch,
  TrendingUp, TrendingDown, Activity, Link2,
  Mail, Radio, CheckCircle2, Eye,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { useCommandCenter } from "@/hooks/use-command-center";
import { useRouter } from "next/navigation";
import { CampaignEvolutionPanel } from "@/components/operational/campaign-evolution-panel";
import { CampaignWorkflowStepper } from "@/components/operational/campaign-workflow-stepper";
import { EmailThreadViewer } from "@/components/operational/email-thread-viewer";
import { PageGuide } from "@/components/ui/page-guide";
import type { CampaignIntelligence } from "@/types/business-intelligence";

function getHealthColor(score: number): string {
  if (score >= 0.9) return "text-emerald-400";
  if (score >= 0.7) return "text-amber-400";
  if (score >= 0.5) return "text-orange-400";
  return "text-red-400";
}

function getHealthBarColor(score: number): string {
  if (score >= 0.9) return "bg-emerald-500";
  if (score >= 0.7) return "bg-amber-500";
  if (score >= 0.5) return "bg-orange-500";
  return "bg-red-500";
}

function getMomentumIcon(momentum: number) {
  if (momentum > 0.01) return <TrendingUp className="w-3 h-3 text-emerald-400" />;
  if (momentum < -0.01) return <TrendingDown className="w-3 h-3 text-red-400" />;
  return <Activity className="w-3 h-3 text-slate-500" />;
}

function getMomentumLabel(momentum: number): string {
  if (momentum > 0.05) return "accelerating";
  if (momentum > 0.01) return "improving";
  if (momentum > -0.01) return "stable";
  if (momentum > -0.05) return "declining";
  return "critical";
}

export default function CampaignsPage() {
  const { openCommand } = useCommandCenter();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [healthFilter, setHealthFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"table" | "evolution">("evolution");
  const [expandedEmails, setExpandedEmails] = useState<Set<string>>(new Set());

  const toggleEmails = (campaignId: string) => {
    setExpandedEmails((prev) => {
      const next = new Set(prev);
      if (next.has(campaignId)) next.delete(campaignId);
      else next.add(campaignId);
      return next;
    });
  };

  const { data: campaigns = [], isLoading, isError } = useQuery<CampaignIntelligence[]>({
    queryKey: ["campaigns"],
    queryFn: () => {
      const data = fetchApi<any>("/business-intelligence/intelligence/campaigns");
      return data.then((d) => d?.campaigns ?? []);
    },
    refetchInterval: 10000,
  });

  const filtered = campaigns.filter((c) => {
    const matchesSearch = !searchQuery || 
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.client_name || "").toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesStatus = statusFilter === "all" || c.status === statusFilter;
    
    const matchesHealth = healthFilter === "all" || 
      (healthFilter === "healthy" && c.health_score >= 0.7) ||
      (healthFilter === "at_risk" && c.health_score >= 0.4 && c.health_score < 0.7) ||
      (healthFilter === "critical" && c.health_score < 0.4);
    
    return matchesSearch && matchesStatus && matchesHealth;
  });

  const sorted = useMemo(() =>
    [...filtered].sort((a, b) => b.health_score - a.health_score),
    [filtered],
  );

  const activeCount = campaigns.filter((c) => c.status === "active" || c.status === "monitoring").length;
  const avgHealth = campaigns.length > 0
    ? campaigns.reduce((s, c) => s + c.health_score, 0) / campaigns.length
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Campaigns</h1>
          <p className="text-slate-400 mt-1">Live campaign health evolution tracking.</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search campaigns..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500 w-48"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-xs font-mono text-slate-300 focus:outline-none focus:border-platform-500"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="prospecting">Prospecting</option>
            <option value="active">Active</option>
            <option value="monitoring">Monitoring</option>
            <option value="complete">Complete</option>
            <option value="paused">Paused</option>
          </select>

          {/* Health Filter */}
          <select
            value={healthFilter}
            onChange={(e) => setHealthFilter(e.target.value)}
            className="px-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-xs font-mono text-slate-300 focus:outline-none focus:border-platform-500"
          >
            <option value="all">All Health</option>
            <option value="healthy">Healthy (≥70%)</option>
            <option value="at_risk">At Risk (40-70%)</option>
            <option value="critical">Critical (<40%)</option>
          </select>

          {/* View Mode */}
          <div className="flex items-center gap-1 bg-surface-darker rounded-lg border border-surface-border p-0.5">
            <button
              onClick={() => setViewMode("evolution")}
              className={`px-3 py-1.5 text-[10px] font-mono rounded-md transition-all ${
                viewMode === "evolution"
                  ? "bg-platform-500/10 text-platform-400 border border-platform-500/20"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              EVOLUTION
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`px-3 py-1.5 text-[10px] font-mono rounded-md transition-all ${
                viewMode === "table"
                  ? "bg-platform-500/10 text-platform-400 border border-platform-500/20"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              TABLE
            </button>
          </div>
          <span className="px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-md text-[10px] font-mono text-emerald-400 flex items-center gap-2">
            <GitBranch className="w-3.5 h-3.5" />
            {activeCount} active
          </span>
          <span className="px-3 py-1.5 bg-platform-500/10 border border-platform-500/30 rounded-md text-[10px] font-mono text-platform-400 flex items-center gap-2">
            <Activity className="w-3.5 h-3.5" />
            avg {Math.round(avgHealth * 100)}% health
          </span>
          <button
            onClick={() => openCommand("create_campaign")}
            className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors shadow-lg shadow-platform-900/30 flex items-center gap-2 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            CREATE
          </button>
        </div>
      </div>

      <PageGuide title="About Campaigns">
        <p>Campaigns track your link-building and outreach efforts. Each campaign has a <strong>health score</strong>, <strong>momentum</strong>, and <strong>progress</strong> toward its target link count.</p>
        <p>Switch between <strong>Evolution</strong> view (health trends over time) and <strong>Table</strong> view (detailed metrics per campaign). Create a campaign to get started.</p>
      </PageGuide>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search campaigns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-surface-darker border border-surface-border rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500 focus:ring-1 focus:ring-platform-500 transition-all text-sm"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : isError ? (
        <div className="glass-panel p-6 border-red-500/20 bg-red-500/5">
          <h3 className="text-red-400 font-medium">Failed to load campaigns</h3>
          <p className="text-sm text-slate-400 mt-1">Ensure the backend and database are accessible.</p>
        </div>
      ) : viewMode === "evolution" ? (
        <CampaignEvolutionPanel />
      ) : sorted.length === 0 ? (
        <div className="glass-panel p-12 flex flex-col items-center justify-center text-center">
          <GitBranch className="w-12 h-12 text-slate-700 mb-3" />
          <h3 className="text-lg font-medium text-slate-300">No Campaigns</h3>
          <p className="text-sm text-slate-500 mt-1">Create your first campaign to start tracking.</p>
          <button
            onClick={() => openCommand("create_campaign")}
            className="mt-4 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> CREATE CAMPAIGN
          </button>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-[10px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                <tr>
                  <th className="px-5 py-3 font-mono font-medium">Campaign</th>
                  <th className="px-5 py-3 font-mono font-medium">Status</th>
                  <th className="px-5 py-3 font-mono font-medium text-center">Health</th>
                  <th className="px-5 py-3 font-mono font-medium text-center">Momentum</th>
                  <th className="px-5 py-3 font-mono font-medium text-center">Velocity</th>
                  <th className="px-5 py-3 font-mono font-medium text-right">Links</th>
                  <th className="px-5 py-3 font-mono font-medium text-right">Progress</th>
                  <th className="px-5 py-3 font-mono font-medium text-right">Sent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {sorted.map((c, i) => {
                  const latest = c.trends?.[0];
                  const momentum = latest?.momentum ?? 0;
                  const velocity = latest?.velocity ?? 0;
                  const healthPct = Math.round(c.health_score * 100);
                  const progressPct = Math.round(c.progress * 100);
                  return (
                    <Fragment key={c.id}>
                      <motion.tr
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                        className="hover:bg-surface-border/30 transition-colors group"
                      >
                        <td className="px-5 py-3.5">
                          <button onClick={() => router.push(`/dashboard/campaigns/${c.id}`)} className="font-medium text-slate-200 text-sm hover:text-platform-400 transition-colors text-left">
                            {c.name}
                          </button>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5 capitalize">
                            {c.campaign_type.replace("_", " ")}
                          </div>
                        </td>
                        <td className="px-5 py-3.5">
                          <span className={`px-2 py-0.5 text-[10px] font-mono rounded-full border uppercase ${
                            c.status === "active" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                            c.status === "monitoring" ? "bg-platform-500/10 text-platform-400 border-platform-500/20" :
                            c.status === "draft" ? "bg-slate-500/10 text-slate-400 border-slate-500/20" :
                            "bg-amber-500/10 text-amber-400 border-amber-500/20"
                          }`}>
                            {c.status.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <div className="w-16 h-2 bg-surface-darker rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${healthPct}%` }}
                                transition={{ duration: 0.5, delay: i * 0.05 }}
                                className={`h-full rounded-full ${getHealthBarColor(c.health_score)}`}
                              />
                            </div>
                            <span className={`text-[10px] font-mono font-bold ${getHealthColor(c.health_score)}`}>
                              {healthPct}%
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-center">
                          <div className="flex items-center justify-center gap-1">
                            {getMomentumIcon(momentum)}
                            <span className={`text-[10px] font-mono ${
                              momentum > 0.01 ? "text-emerald-500" :
                              momentum < -0.01 ? "text-red-400" : "text-slate-500"
                            }`}>
                              {getMomentumLabel(momentum)}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-center">
                          <span className="text-[10px] font-mono text-slate-500">
                            {velocity > 0 ? `${velocity.toFixed(3)}/s` : "—"}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-platform-900/30 text-platform-400 font-mono font-bold text-xs border border-platform-500/20">
                            <Link2 className="w-3 h-3" />
                            {c.acquired_link_count}/{c.target_link_count}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <span className={`text-[11px] font-mono font-bold ${
                            progressPct >= 80 ? "text-emerald-400" :
                            progressPct >= 50 ? "text-amber-400" :
                            "text-slate-500"
                          }`}>
                            {progressPct}%
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <button
                            onClick={() => toggleEmails(c.id)}
                            className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-mono transition-colors ${
                              expandedEmails.has(c.id)
                                ? "bg-platform-500/15 text-platform-400 border border-platform-500/30"
                                : "text-slate-500 hover:text-slate-300 hover:bg-surface-border/30"
                            }`}
                          >
                            <Mail className="w-3 h-3" />
                            {c.total_emails_sent}
                            <Eye className={`w-3 h-3 ${expandedEmails.has(c.id) ? "opacity-100" : "opacity-0 group-hover:opacity-50"}`} />
                          </button>
                        </td>
                      </motion.tr>
                      {expandedEmails.has(c.id) && (
                        <motion.tr
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                        >
                          <td colSpan={8} className="px-5 py-3 bg-surface-darker/30">
                            <EmailThreadViewer campaignId={c.id} />
                          </td>
                        </motion.tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Workflow Execution Progress for Active Campaigns */}
      {viewMode === "table" && sorted.filter(c => c.status === "active" || c.status === "monitoring").length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {sorted.filter(c => c.status === "active" || c.status === "monitoring").slice(0, 3).map((campaign) => (
            <div key={campaign.id} className="glass-panel p-4">
              <div className="flex items-center gap-2 mb-3">
                <Radio className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-mono font-bold text-slate-200 truncate">{campaign.name}</span>
                <span className="ml-auto text-[9px] font-mono text-slate-600">phase 2</span>
              </div>
              <CampaignWorkflowStepper activePhase="scoring" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
