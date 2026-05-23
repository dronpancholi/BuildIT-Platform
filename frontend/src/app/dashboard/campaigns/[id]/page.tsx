"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft, GitBranch, Target, Link2, TrendingUp, Activity,
  Save, Loader2, Edit3, X, CheckCircle2, Clock, AlertTriangle,
  Mail, Users, FileText, Reply, Calendar,
} from "lucide-react";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { CampaignWorkflowStepper } from "@/components/operational/campaign-workflow-stepper";
import { CampaignTimeline } from "@/components/operational/campaign-timeline";
import { useCommandCenter } from "@/hooks/use-command-center";
import type { CampaignIntelligence } from "@/types/business-intelligence";

interface CampaignDetail {
  id: string;
  client_id: string;
  client_name: string | null;
  name: string;
  campaign_type: string;
  status: string;
  target_link_count: number;
  acquired_link_count: number;
  health_score: number;
  workflow_run_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  total_prospects?: number;
}

const CAMPAIGN_TYPES = [
  "guest_post", "resource_page", "niche_edit",
  "broken_link", "skyscraper", "haro",
];

function getStatusColor(s: string) {
  if (s === "active" || s === "monitoring") return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  if (s === "draft") return "bg-slate-500/10 text-slate-400 border-slate-500/20";
  return "bg-amber-500/10 text-amber-400 border-amber-500/20";
}

function HealthBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.7 ? "bg-emerald-500" : score >= 0.4 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-surface-darker rounded-full overflow-hidden">
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} className={`h-full rounded-full ${color}`} />
      </div>
      <span className="text-xs font-mono font-bold text-slate-300">{pct}%</span>
    </div>
  );
}

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { openCommand } = useCommandCenter();
  const campaignId = params.id as string;

  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, string>>({});

  const { data: campaign, isLoading, isError } = useQuery<CampaignDetail>({
    queryKey: ["campaign", campaignId],
    queryFn: () => fetchApi(`/campaigns/${campaignId}?tenant_id=${MOCK_TENANT_ID}`),
    enabled: !!campaignId,
  });

  const { data: intelligence } = useQuery<CampaignIntelligence[]>({
    queryKey: ["campaigns-intelligence"],
    queryFn: () => fetchApi<any>("/business-intelligence/intelligence/campaigns")
      .then((d) => d?.campaigns ?? []),
    enabled: !!campaignId,
    select: (data) => data.filter((c: CampaignIntelligence) => c.id === campaignId),
  });

  const { data: campaignThreads } = useQuery<any[]>({
    queryKey: ["campaign-threads", campaignId],
    queryFn: () => fetchApi(`/campaigns/${campaignId}/threads?tenant_id=${MOCK_TENANT_ID}`),
    enabled: !!campaignId,
  });

  const threadMetrics = campaignThreads ? (() => {
    const threads = campaignThreads ?? [];
    const total = threads.length;
    const sent = threads.filter((t: any) => t.status === "sent").length;
    const replied = threads.filter((t: any) => t.status === "replied").length;
    const linkAcquired = threads.filter((t: any) => t.status === "link_acquired").length;
    const draft = threads.filter((t: any) => t.status === "draft").length;
    const followUps = threads.reduce((sum: number, t: any) => sum + (t.follow_up_count || 0), 0);
    const outreachComplete = sent + replied + linkAcquired;
    return {
      total, sent, replied, linkAcquired, draft, followUps,
      replyRate: outreachComplete > 0 ? replied / outreachComplete : 0,
      acquisitionRate: (total - draft) > 0 ? linkAcquired / (total - draft) : 0,
    };
  })() : null;

  const campaignIntel = intelligence?.[0];

  const updateMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      fetchApi(`/campaigns/${campaignId}?tenant_id=${MOCK_TENANT_ID}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] });
      queryClient.invalidateQueries({ queryKey: ["campaigns-intelligence"] });
      setEditing(false);
    },
  });

  const handleEdit = () => {
    if (!campaign) return;
    setEditForm({
      name: campaign.name,
      campaign_type: campaign.campaign_type,
      target_link_count: String(campaign.target_link_count),
    });
    setEditing(true);
  };

  const handleSave = () => {
    updateMutation.mutate({
      name: editForm.name,
      campaign_type: editForm.campaign_type,
      target_link_count: parseInt(editForm.target_link_count) || 10,
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
      </div>
    );
  }

  if (isError || !campaign) {
    return (
      <div className="glass-panel p-8 border-red-500/20 bg-red-500/5">
        <h3 className="text-red-400 font-medium">Campaign not found</h3>
        <p className="text-sm text-slate-400 mt-1">This campaign may have been deleted or you don't have access.</p>
        <button onClick={() => router.push("/dashboard/campaigns")} className="mt-4 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-mono">
          ← Back to campaigns
        </button>
      </div>
    );
  }

  const progress = campaign.target_link_count > 0
    ? Math.round((campaign.acquired_link_count / campaign.target_link_count) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard/campaigns")} className="p-2 rounded-lg hover:bg-surface-border/30 text-slate-400 hover:text-slate-200 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              {editing ? (
                <input
                  value={editForm.name}
                  onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                  className="text-2xl font-bold bg-surface-darker border border-platform-500 rounded px-2 py-1 text-slate-100"
                />
              ) : (
                <h1 className="text-2xl font-bold text-slate-100">{campaign.name}</h1>
              )}
              <span className={`px-2.5 py-0.5 text-[10px] font-mono rounded-full border uppercase ${getStatusColor(campaign.status)}`}>
                {campaign.status.replace("_", " ")}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {campaign.client_name && `${campaign.client_name} · `}
              {campaign.campaign_type.replace("_", " ")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <button onClick={() => setEditing(false)} className="px-3 py-1.5 text-xs font-mono rounded-md border border-surface-border text-slate-400 hover:text-slate-200 flex items-center gap-1.5">
                <X className="w-3.5 h-3.5" /> Cancel
              </button>
              <button onClick={handleSave} disabled={updateMutation.isPending} className="px-3 py-1.5 text-xs font-mono rounded-md bg-platform-600 hover:bg-platform-500 text-white flex items-center gap-1.5">
                {updateMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save
              </button>
            </>
          ) : (
            <button onClick={handleEdit} className="px-3 py-1.5 text-xs font-mono rounded-md border border-surface-border text-slate-400 hover:text-slate-200 flex items-center gap-1.5">
              <Edit3 className="w-3.5 h-3.5" /> Edit
            </button>
          )}
        </div>
      </div>

      {updateMutation.isError && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
          Failed to save: {(updateMutation.error as Error)?.message || "Unknown error"}
        </div>
      )}
      {updateMutation.isSuccess && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" /> Campaign updated successfully.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <div className="glass-panel p-4">
            <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider mb-3">Campaign Details</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-mono text-slate-600 uppercase">Campaign Type</label>
                {editing ? (
                  <select
                    value={editForm.campaign_type}
                    onChange={(e) => setEditForm((f) => ({ ...f, campaign_type: e.target.value }))}
                    className="w-full mt-1 bg-surface-darker border border-surface-border rounded px-2 py-1 text-xs text-slate-200"
                  >
                    {CAMPAIGN_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
                  </select>
                ) : (
                  <p className="text-sm text-slate-200 mt-1 capitalize">{campaign.campaign_type.replace("_", " ")}</p>
                )}
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-600 uppercase">Status</label>
                <p className="text-sm text-slate-200 mt-1 capitalize">{campaign.status.replace("_", " ")}</p>
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-600 uppercase">Target Link Count</label>
                {editing ? (
                  <input
                    type="number"
                    value={editForm.target_link_count}
                    onChange={(e) => setEditForm((f) => ({ ...f, target_link_count: e.target.value }))}
                    className="w-full mt-1 bg-surface-darker border border-surface-border rounded px-2 py-1 text-xs text-slate-200"
                    min={1} max={500}
                  />
                ) : (
                  <p className="text-sm text-slate-200 mt-1">{campaign.target_link_count}</p>
                )}
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-600 uppercase">Acquired Links</label>
                <p className="text-sm text-slate-200 mt-1">{campaign.acquired_link_count}</p>
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-600 uppercase">Client</label>
                <p className="text-sm text-slate-200 mt-1">{campaign.client_name || campaign.client_id}</p>
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-600 uppercase">Workflow</label>
                <p className="text-sm text-slate-200 mt-1 font-mono">{campaign.workflow_run_id || "Not started"}</p>
              </div>
            </div>
            {campaign.created_at && (
              <div className="mt-4 pt-3 border-t border-surface-border/50 flex gap-4 text-[10px] font-mono text-slate-600">
                <span>Created: {new Date(campaign.created_at).toLocaleString()}</span>
                {campaign.updated_at && <span>Updated: {new Date(campaign.updated_at).toLocaleString()}</span>}
              </div>
            )}
          </div>

          {campaign.status === "draft" && (
            <div className="glass-panel p-4">
              <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider mb-3">Launch Campaign</h3>
              <p className="text-xs text-slate-500 mb-3">Launch this campaign to begin prospect discovery and automated outreach.</p>
              <button
                onClick={() => openCommand("keyword_discovery")}
                className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono"
              >
                Launch Campaign
              </button>
            </div>
          )}

          {(campaignIntel || threadMetrics) && (
            <div className="glass-panel p-4">
              <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider mb-3">Health & Performance</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Activity className="w-3 h-3" /> Health
                  </div>
                  <HealthBar score={campaignIntel?.health_score ?? campaign.health_score} />
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Link2 className="w-3 h-3" /> Progress
                  </div>
                  <p className="text-lg font-bold text-slate-200">{progress}%</p>
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Target className="w-3 h-3" /> Links
                  </div>
                  <p className="text-lg font-bold text-slate-200">{campaign.acquired_link_count}/{campaign.target_link_count}</p>
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <TrendingUp className="w-3 h-3" /> Acq. Rate
                  </div>
                  <p className="text-lg font-bold text-emerald-400">
                    {((threadMetrics?.acquisitionRate ?? campaignIntel?.acquisition_rate ?? 0) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Mail className="w-3 h-3" /> Emails Sent
                  </div>
                  <p className="text-lg font-bold text-slate-200">{threadMetrics?.sent ?? campaignIntel?.total_emails_sent ?? 0}</p>
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Users className="w-3 h-3" /> Prospects
                  </div>
                  <p className="text-lg font-bold text-slate-200">{campaignIntel?.total_prospects ?? campaign.total_prospects ?? 0}</p>
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Reply className="w-3 h-3" /> Replies
                  </div>
                  <p className="text-lg font-bold text-blue-400">{threadMetrics?.replied ?? 0}</p>
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <TrendingUp className="w-3 h-3" /> Reply Rate
                  </div>
                  <p className="text-lg font-bold text-slate-200">
                    {((threadMetrics?.replyRate ?? campaignIntel?.reply_rate ?? 0) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Calendar className="w-3 h-3" /> Follow-Ups
                  </div>
                  <p className="text-lg font-bold text-amber-400">{threadMetrics?.followUps ?? 0}</p>
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Link2 className="w-3 h-3" /> Links Acquired
                  </div>
                  <p className="text-lg font-bold text-purple-400">{threadMetrics?.linkAcquired ?? campaign.acquired_link_count}</p>
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Mail className="w-3 h-3" /> Drafts
                  </div>
                  <p className="text-lg font-bold text-slate-400">{threadMetrics?.draft ?? 0}</p>
                </div>
                <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 mb-1">
                    <Activity className="w-3 h-3" /> Total Threads
                  </div>
                  <p className="text-lg font-bold text-slate-200">{threadMetrics?.total ?? 0}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="glass-panel p-4">
            <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider mb-3">Actions</h3>
            <div className="space-y-2">
              <button
                onClick={() => openCommand("keyword_discovery")}
                className="w-full px-3 py-2 text-xs font-mono bg-surface-darker border border-surface-border rounded-lg text-slate-300 hover:border-platform-500/30 transition-colors flex items-center gap-2"
              >
                <GitBranch className="w-3.5 h-3.5" /> Keyword Research
              </button>
              <button
                onClick={() => openCommand("generate_report")}
                className="w-full px-3 py-2 text-xs font-mono bg-surface-darker border border-surface-border rounded-lg text-slate-300 hover:border-platform-500/30 transition-colors flex items-center gap-2"
              >
                <FileText className="w-3.5 h-3.5" /> Generate Report
              </button>
            </div>
          </div>

          <div className="glass-panel p-4">
            <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider mb-3">Timeline</h3>
            <CampaignTimeline campaignId={campaignId} />
          </div>
        </div>
      </div>
    </div>
  );
}
