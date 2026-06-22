"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Mail, CheckCircle2, AlertTriangle, Clock, FileText, Users } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface Thread {
  id: string;
  campaign_id: string;
  campaign_name?: string;
  prospect_domain: string;
  prospect_name?: string;
  to_email: string;
  subject: string;
  status: string;
  follow_up_count: number;
  sent_at?: string;
  replied_at?: string;
  created_at?: string;
}

function getStatusBadge(status: string) {
  const statusConfig: Record<string, { color: string; label: string; icon: any }> = {
    draft: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20", label: "DRAFT", icon: FileText },
    queued: { color: "bg-blue-500/10 text-blue-400 border-blue-500/20", label: "QUEUED", icon: Clock },
    sent: { color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20", label: "SENT", icon: Mail },
    delivered: { color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20", label: "DELIVERED", icon: CheckCircle2 },
    opened: { color: "bg-teal-500/10 text-teal-400 border-teal-500/20", label: "OPENED", icon: Mail },
    replied: { color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", label: "REPLIED", icon: CheckCircle2 },
    "link_acquired": { color: "bg-green-500/10 text-green-400 border-green-500/20", label: "LINK ACQUIRED", icon: CheckCircle2 },
    bounced: { color: "bg-red-500/10 text-red-400 border-red-500/20", label: "BOUNCED", icon: AlertTriangle },
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

export function CommunicationsTab({ customerId }: { customerId: string }) {
  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data: threads = [], isLoading, error } = useQuery<Thread[]>({
    queryKey: ["customer", customerId, "communications"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/campaigns/threads/all?tenant_id=${tenantId}`);
      const allThreads = response?.data || [];
      
      // Fetch campaigns to filter by client
      const campaignsResponse = await fetchApi<any>(`/business-intelligence/intelligence/campaigns?tenant_id=${tenantId}`);
      const campaigns = campaignsResponse?.data?.campaigns || [];
      const clientCampaignIds = new Set(
        safeArr<any>(campaigns).filter((c: any) => c.client_id === customerId).map((c: any) => c.id)
      );

      return safeArr<Thread>(allThreads).filter((t: Thread) => clientCampaignIds.has(t.campaign_id));
    },
    refetchInterval: 30000,
  });

  const stats = {
    total: safeArr<Thread>(threads).length,
    draft: safeArr<Thread>(threads).filter((t) => t.status === "draft").length,
    sent: safeArr<Thread>(threads).filter((t) => ["sent", "delivered", "opened"].includes(t.status)).length,
    replied: safeArr<Thread>(threads).filter((t) => t.status === "replied").length,
    linkAcquired: safeArr<Thread>(threads).filter((t) => t.status === "link_acquired").length,
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center p-8 glass-panel">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Failed to load communications</h3>
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
          <Mail className="w-12 h-12 text-platform-500 animate-spin mx-auto mb-3" />
          <p className="text-xs font-mono text-slate-500">Loading communications...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Mail className="w-3.5 h-3.5" /> Total
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{stats.total}</p>
        </div>
        <div className="glass-panel p-4 border-slate-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Draft
          </div>
          <p className="text-2xl font-bold font-mono text-slate-300">{stats.draft}</p>
        </div>
        <div className="glass-panel p-4 border-indigo-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-indigo-500 uppercase mb-2">
            <Mail className="w-3.5 h-3.5" /> Sent
          </div>
          <p className="text-2xl font-bold font-mono text-indigo-400">{stats.sent}</p>
        </div>
        <div className="glass-panel p-4 border-emerald-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-500 uppercase mb-2">
            <CheckCircle2 className="w-3.5 h-3.5" /> Replied
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">{stats.replied}</p>
        </div>
        <div className="glass-panel p-4 border-green-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-green-500 uppercase mb-2">
            <CheckCircle2 className="w-3.5 h-3.5" /> Links
          </div>
          <p className="text-2xl font-bold font-mono text-green-400">{stats.linkAcquired}</p>
        </div>
      </div>

      {/* Reply Rate */}
      {stats.sent > 0 && (
        <div className="glass-panel p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-platform-400" />
              <span className="text-xs font-bold font-mono text-slate-200 uppercase">Reply Rate</span>
            </div>
            <span className="text-lg font-bold font-mono text-emerald-400">
              {((stats.replied / stats.sent) * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      )}

      {/* Threads List */}
      {safeArr<Thread>(threads).length === 0 ? (
        <div className="glass-panel p-8 text-center">
          <Mail className="w-12 h-12 text-slate-700 mx-auto mb-3" />
          <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Communications Yet</h3>
          <p className="text-xs text-slate-500 mb-4">Emails will appear here once campaigns are launched</p>
        </div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="divide-y divide-surface-border">
            {safeArr<Thread>(threads).map((thread) => (
              <div key={thread.id} className="p-4 hover:bg-surface-border/20 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-bold font-mono text-slate-200 truncate">{thread.subject}</h3>
                      {getStatusBadge(thread.status)}
                    </div>
                    <p className="text-[10px] font-mono text-slate-500">
                      To: {thread.prospect_name || "Contact"}@{thread.prospect_domain}
                    </p>
                  </div>
                  <div className="text-right ml-4 flex-shrink-0">
                    {thread.sent_at && (
                      <div className="text-[10px] font-mono text-slate-600">
                        Sent: {new Date(thread.sent_at).toLocaleDateString()}
                      </div>
                    )}
                    {thread.replied_at && (
                      <div className="text-[10px] font-mono text-emerald-600">
                        Replied: {new Date(thread.replied_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>

                {/* Thread metadata */}
                <div className="flex items-center gap-4 text-[10px] font-mono text-slate-600">
                  {thread.campaign_name && (
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3 text-platform-500" />
                      {thread.campaign_name}
                    </span>
                  )}
                  {thread.follow_up_count > 0 && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-amber-500" />
                      {thread.follow_up_count} follow-up{thread.follow_up_count > 1 ? "s" : ""}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Users className="w-3 h-3 text-slate-500" />
                    {thread.prospect_domain}
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