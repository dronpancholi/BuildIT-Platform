"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { 
  Mail, FileText, Clock, CheckCircle2, AlertTriangle, 
  Send, Edit2, Trash2, Filter, Search, Plus,
  ChevronDown, ChevronUp, Paperclip, Smile, Calendar
} from "lucide-react";

interface EmailThread {
  id: string;
  campaign_id: string;
  campaign_name?: string;
  prospect_domain: string;
  prospect_name?: string;
  to_email: string;
  subject: string;
  body_html: string;
  status: string;
  follow_up_count: number;
  sent_at?: string;
  replied_at?: string;
  created_at: string;
  updated_at: string;
  confidence_score: number;
}

interface Template {
  id: string;
  name: string;
  subject: string;
  body_html: string;
  usage_count: number;
  avg_reply_rate: number;
  created_at: string;
}

export default function CommunicationHub() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"inbox" | "approvals" | "templates" | "drafts">("inbox");
  const [selectedThread, setSelectedThread] = useState<EmailThread | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  // Fetch threads
  const { data: threads = [], isLoading: loadingThreads } = useQuery<EmailThread[]>({
    queryKey: ["communications", "threads"],
    queryFn: () => fetchApi(`/campaigns/threads/all?tenant_id=${tenantId}`),
    refetchInterval: 30000,
  });

  // Fetch templates
  const { data: templates = [], isLoading: loadingTemplates } = useQuery<Template[]>({
    queryKey: ["communications", "templates"],
    queryFn: async () => {
      // Templates would come from a dedicated endpoint - using empty array for now
      return [];
    },
  });

  const filteredThreads = threads.filter(thread => {
    const matchesSearch = !searchQuery || 
      thread.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      thread.prospect_domain.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === "all" || thread.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const stats = {
    total: threads.length,
    draft: threads.filter(t => t.status === "draft").length,
    sent: threads.filter(t => ["sent", "delivered", "opened"].includes(t.status)).length,
    replied: threads.filter(t => t.status === "replied").length,
    linkAcquired: threads.filter(t => t.status === "link_acquired").length,
  };

  const sendMutation = useMutation({
    mutationFn: async (threadId: string) => {
      return fetchApi(`/campaigns/threads/${threadId}/send?tenant_id=${tenantId}`, {
        method: "POST",
        body: JSON.stringify({}),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["communications", "threads"] });
      setSelectedThread(null);
    },
  });

  const getStatusBadge = (status: string) => {
    const config: Record<string, { color: string; label: string; icon: any }> = {
      draft: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20", label: "DRAFT", icon: FileText },
      queued: { color: "bg-blue-500/10 text-blue-400 border-blue-500/20", label: "QUEUED", icon: Clock },
      sent: { color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20", label: "SENT", icon: Send },
      delivered: { color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20", label: "DELIVERED", icon: CheckCircle2 },
      opened: { color: "bg-teal-500/10 text-teal-400 border-teal-500/20", label: "OPENED", icon: Mail },
      replied: { color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", label: "REPLIED", icon: CheckCircle2 },
      link_acquired: { color: "bg-green-500/10 text-green-400 border-green-500/20", label: "LINK ACQUIRED", icon: CheckCircle2 },
      bounced: { color: "bg-red-500/10 text-red-400 border-red-500/20", label: "BOUNCED", icon: AlertTriangle },
    };
    const { color, label, icon: Icon } = config[status] || config.draft;
    return (
      <span className={`px-2 py-1 text-[10px] font-mono rounded border ${color} flex items-center gap-1`}>
        <Icon className="w-3 h-3" />
        {label}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Communication Hub</h1>
          <p className="text-slate-400 mt-1">Unified email management for all outreach activities</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 bg-platform-600/20 border border-platform-500/30 rounded-lg flex items-center gap-2">
            <Mail className="w-4 h-4 text-platform-400" />
            <span className="text-sm font-mono text-platform-300">{stats.total} Threads</span>
          </div>
          <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center gap-2">
            <Plus className="w-4 h-4" /> Compose
          </button>
        </div>
      </div>

      {/* Stats */}
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
            <Send className="w-3.5 h-3.5" /> Sent
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

      {/* Tabs */}
      <div className="glass-panel overflow-hidden">
        <div className="flex items-center gap-1 p-1 bg-surface-darker/50 border-b border-surface-border">
          {[
            { id: "inbox", label: "Inbox", icon: Mail },
            { id: "approvals", label: "Approvals", icon: CheckCircle2 },
            { id: "templates", label: "Templates", icon: FileText },
            { id: "drafts", label: "Drafts", icon: Edit2 },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 text-xs font-mono rounded-md transition-all ${
                  activeTab === tab.id
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

        {/* Filters */}
        <div className="p-4 flex items-center gap-3 border-b border-surface-border">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search threads..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-300 focus:outline-none focus:border-platform-500"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="replied">Replied</option>
            <option value="link_acquired">Link Acquired</option>
          </select>
        </div>

        {/* Content */}
        <div className="p-4">
          {activeTab === "inbox" && (
            <div className="space-y-3">
              {loadingThreads ? (
                <div className="text-center p-8">
                  <Mail className="w-12 h-12 text-platform-500 animate-spin mx-auto mb-3" />
                  <p className="text-xs font-mono text-slate-500">Loading threads...</p>
                </div>
              ) : filteredThreads.length === 0 ? (
                <div className="text-center p-8 glass-panel">
                  <Mail className="w-12 h-12 text-slate-700 mx-auto mb-3" />
                  <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Threads Found</h3>
                  <p className="text-xs text-slate-500">Email threads will appear here once campaigns are launched</p>
                </div>
              ) : (
                filteredThreads.map((thread) => (
                  <div
                    key={thread.id}
                    onClick={() => setSelectedThread(thread)}
                    className="glass-panel p-4 hover:bg-surface-border/20 transition-all cursor-pointer"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-bold font-mono text-slate-200">{thread.subject}</h3>
                          {getStatusBadge(thread.status)}
                        </div>
                        <p className="text-[10px] font-mono text-slate-500">
                          To: {thread.prospect_name || "Contact"}@{thread.prospect_domain}
                        </p>
                      </div>
                      <div className="text-right ml-4 flex-shrink-0">
                        <span className="text-[10px] font-mono text-slate-600">
                          {new Date(thread.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
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
                        <Mail className="w-3 h-3 text-slate-500" />
                        {thread.prospect_domain}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "approvals" && (
            <div className="text-center p-8 glass-panel">
              <CheckCircle2 className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Email Approvals</h3>
              <p className="text-xs text-slate-500 mb-4">Pending email templates requiring approval</p>
              <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors">
                View in Approval Center
              </button>
            </div>
          )}

          {activeTab === "templates" && (
            <div className="text-center p-8 glass-panel">
              <FileText className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Templates Library</h3>
              <p className="text-xs text-slate-500 mb-4">Reusable email templates with performance tracking</p>
              <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors">
                Create Template
              </button>
            </div>
          )}

          {activeTab === "drafts" && (
            <div className="text-center p-8 glass-panel">
              <Edit2 className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Drafts</h3>
              <p className="text-xs text-slate-500 mb-4">Unsent email drafts</p>
              <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors">
                Compose Draft
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Thread Detail Modal */}
      {selectedThread && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-surface-border bg-surface-darker/50">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-100">{selectedThread.subject}</h2>
                  <p className="text-sm text-slate-400">
                    To: {selectedThread.prospect_name || "Contact"}@{selectedThread.prospect_domain}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedThread(null)}
                  className="p-2 hover:bg-surface-border rounded-lg transition-colors"
                >
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              {/* Thread Status */}
              <div className="mb-4 flex items-center gap-2">
                {getStatusBadge(selectedThread.status)}
                {selectedThread.sent_at && (
                  <span className="text-[10px] font-mono text-slate-600">
                    Sent: {new Date(selectedThread.sent_at).toLocaleString()}
                  </span>
                )}
                {selectedThread.replied_at && (
                  <span className="text-[10px] font-mono text-emerald-600">
                    Replied: {new Date(selectedThread.replied_at).toLocaleString()}
                  </span>
                )}
              </div>

              {/* Email Content */}
              <div className="glass-panel p-4 mb-4">
                <div 
                  className="prose prose-invert prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: selectedThread.body_html }}
                />
              </div>

              {/* Quick Actions */}
              <div className="flex items-center gap-2">
                {selectedThread.status === "draft" && (
                  <button
                    onClick={() => sendMutation.mutate(selectedThread.id)}
                    disabled={sendMutation.isPending}
                    className="px-4 py-2 bg-emerald-600/80 hover:bg-emerald-600 text-white rounded-lg text-xs font-bold font-mono transition-colors disabled:opacity-50"
                  >
                    {sendMutation.isPending ? "Sending..." : "Send Email"}
                  </button>
                )}
                <button className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors">
                  Edit Draft
                </button>
                <button className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors">
                  Follow-up
                </button>
                {selectedThread.status === "sent" && (
                  <button className="px-4 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-500/20 rounded-lg text-xs font-mono transition-colors">
                    Mark Link Acquired
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}