"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Mail, Loader2, AlertCircle, Clock, User, Building2, CheckCircle2,
  Search, ArrowRight, Edit3, Send, Reply, Link2, Calendar, Save, X,
  Bell, Plus, Edit, Trash2
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import type { ThreadData } from "@/components/operational/email-thread-viewer";

function statusColor(s: string): string {
  const map: Record<string, string> = {
    sent: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    delivered: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    opened: "bg-platform-500/10 text-platform-400 border-platform-500/20",
    replied: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    link_acquired: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    bounced: "bg-red-500/10 text-red-400 border-red-500/20",
    draft: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  };
  return map[s] || "bg-slate-500/10 text-slate-400 border-slate-500/20";
}

export default function OutboxPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [showFollowUp, setShowFollowUp] = useState(false);
  const [followUpBody, setFollowUpBody] = useState("");
  const [showLinkAcquired, setShowLinkAcquired] = useState(false);
  const [acquiredUrl, setAcquiredUrl] = useState("");
  const [acquiredAnchor, setAcquiredAnchor] = useState("");
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    threadIds: [] as string[],
    scheduledAt: "",
    timezone: "UTC",
  });

  const { data: threads = [], isLoading, isError } = useQuery<ThreadData[]>({
    queryKey: ["all-threads"],
    queryFn: () => fetchApi(`/campaigns/threads/all?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 10000,
  });

  const filtered = threads.filter((t) =>
    !searchQuery ||
    t.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.prospect_domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (t.to_email && t.to_email.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (t.campaign_name && t.campaign_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const selectedThread = threads.find(t => t.id === selectedThreadId) || filtered[0];

  const updateMutation = useMutation({
    mutationFn: ({ threadId, subject, body }: { threadId: string; subject?: string; body?: string }) =>
      fetchApi(`/campaigns/threads/${threadId}?tenant_id=${MOCK_TENANT_ID}`, {
        method: "PUT",
        body: JSON.stringify({ subject, body_html: body }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["all-threads"] });
      setEditing(false);
    },
  });

  const sendMutation = useMutation({
    mutationFn: (threadId: string) =>
      fetchApi(`/campaigns/threads/${threadId}/send?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["all-threads"] });
    },
  });

  const replyMutation = useMutation({
    mutationFn: (threadId: string) =>
      fetchApi(`/campaigns/threads/${threadId}/simulate-reply?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({ reply_body: "Thank you for reaching out. I'd be happy to discuss this further." }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["all-threads"] });
    },
  });

  const followUpMutation = useMutation({
    mutationFn: ({ threadId, body }: { threadId: string; body: string }) =>
      fetchApi(`/campaigns/threads/${threadId}/follow-up?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({ follow_up_body: body }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["all-threads"] });
      setShowFollowUp(false);
      setFollowUpBody("");
    },
  });

  const linkMutation = useMutation({
    mutationFn: ({ threadId, url, anchor }: { threadId: string; url: string; anchor: string }) =>
      fetchApi(`/campaigns/threads/${threadId}/mark-link-acquired?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({ acquired_url: url, anchor_text: anchor }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["all-threads"] });
      setShowLinkAcquired(false);
      setAcquiredUrl("");
      setAcquiredAnchor("");
    },
  });

  const handleEdit = () => {
    if (!selectedThread) return;
    setEditSubject(selectedThread.subject);
    setEditBody(selectedThread.body_html);
    setEditing(true);
  };

  const handleSave = () => {
    if (!selectedThread) return;
    updateMutation.mutate({
      threadId: selectedThread.id,
      subject: editSubject,
      body: editBody,
    });
  };

  const handleSend = () => {
    if (!selectedThread) return;
    sendMutation.mutate(selectedThread.id);
  };

  const handleReply = () => {
    if (!selectedThread) return;
    replyMutation.mutate(selectedThread.id);
  };

  const handleFollowUp = () => {
    if (!selectedThread || !followUpBody.trim()) return;
    followUpMutation.mutate({ threadId: selectedThread.id, body: followUpBody });
  };

  const handleLinkAcquired = () => {
    if (!selectedThread || !acquiredUrl.trim()) return;
    linkMutation.mutate({
      threadId: selectedThread.id,
      url: acquiredUrl,
      anchor: acquiredAnchor || selectedThread.subject,
    });
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight flex items-center gap-3">
            <Mail className="w-8 h-8 text-platform-500" />
            Outbox
          </h1>
          <p className="text-slate-400 mt-1">Global view of all generated and sent outreach emails.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowScheduleModal(true)}
            className="px-3 py-1.5 rounded-md border border-surface-border text-xs font-mono text-slate-400 hover:text-slate-200 flex items-center gap-2 hover:bg-surface-border/30 transition-colors"
          >
            <Bell className="w-4 h-4" /> Schedule
          </button>
          <button
            onClick={() => openCommand("send_email")}
            className="px-3 py-1.5 rounded-md bg-platform-600 hover:bg-platform-500 text-white text-xs font-mono flex items-center gap-2 transition-colors"
          >
            <Send className="w-4 h-4" /> Send Now
          </button>
        </div>
      </div>

      <div className="glass-panel border-surface-border overflow-hidden flex flex-1 h-full min-h-0">
        {/* Sidebar */}
        <div className="w-1/3 min-w-[300px] border-r border-surface-border flex flex-col bg-surface-darker/50 h-full">
          <div className="p-4 border-b border-surface-border shrink-0">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search emails..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-surface-darker border border-surface-border rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500 focus:ring-1 focus:ring-platform-500 transition-all text-xs"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : isError ? (
              <div className="p-4 text-center text-red-400 text-xs">
                Failed to load threads
              </div>
            ) : filtered.length === 0 ? (
              <div className="p-8 text-center">
                <Mail className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-xs font-mono text-slate-500">No emails found. Emails appear here when campaigns generate outreach.</p>
              </div>
            ) : (
              <div className="divide-y divide-surface-border">
                {filtered.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => { setSelectedThreadId(t.id); setEditing(false); setShowFollowUp(false); setShowLinkAcquired(false); }}
                    className={`w-full text-left p-4 transition-colors hover:bg-surface-border/50 ${
                      selectedThread?.id === t.id ? "bg-platform-500/5 border-l-2 border-platform-500" : "border-l-2 border-transparent"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-slate-200 truncate pr-2">{t.prospect_domain}</span>
                      <span className={`px-1.5 py-0.5 text-[9px] font-mono rounded border uppercase shrink-0 ${statusColor(t.status)}`}>
                        {t.status}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 truncate mb-2">{t.subject}</div>
                    <div className="text-[9px] font-mono text-slate-500 flex items-center justify-between">
                      <span>{t.to_email || "Pending resolution"}</span>
                      <span>{t.created_at ? new Date(t.created_at).toLocaleDateString() : "Draft"}</span>
                    </div>
                    {t.campaign_name && (
                      <div className="text-[8px] font-mono text-slate-600 mt-1 truncate">
                        Campaign: {t.campaign_name}
                      </div>
                    )}
                  </button>
                ))}
</div>
      )}

      {/* Schedule Email Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">Schedule Email Send</h2>
                <p className="text-sm text-slate-400">Schedule emails for later delivery</p>
              </div>
              <button
                onClick={() => setShowScheduleModal(false)}
                className="p-2 hover:bg-surface-border rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <div className="glass-panel p-4 bg-slate-900/50">
                <h4 className="text-xs font-mono text-slate-400 uppercase mb-2">Selected Emails</h4>
                <p className="text-sm text-slate-300">
                  {scheduleForm.threadIds.length > 0 
                    ? `${scheduleForm.threadIds.length} email(s) selected`
                    : "No emails selected - will use currently viewed email"}
                </p>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Send Date & Time</label>
                <input
                  type="datetime-local"
                  value={scheduleForm.scheduledAt}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, scheduledAt: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Timezone</label>
                <select
                  value={scheduleForm.timezone}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, timezone: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                >
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">Eastern Time</option>
                  <option value="America/Chicago">Central Time</option>
                  <option value="America/Denver">Mountain Time</option>
                  <option value="America/Los_Angeles">Pacific Time</option>
                  <option value="Europe/London">London</option>
                  <option value="Europe/Paris">Paris</option>
                  <option value="Asia/Tokyo">Tokyo</option>
                  <option value="Asia/Shanghai">Shanghai</option>
                </select>
              </div>

              <div className="glass-panel p-4 bg-amber-500/5 border-amber-500/20">
                <div className="flex items-start gap-2">
                  <Clock className="w-4 h-4 text-amber-500 mt-0.5" />
                  <div>
                    <p className="text-xs font-mono text-amber-500 uppercase mb-1">Scheduling Info</p>
                    <p className="text-xs text-slate-400">
                      Scheduled emails will be queued for delivery at the specified time. You can cancel scheduled emails before they are sent.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
              <button
                onClick={() => setShowScheduleModal(false)}
                className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  // Would call schedule mutation
                  setShowScheduleModal(false);
                  setScheduleForm({ threadIds: [], scheduledAt: "", timezone: "UTC" });
                }}
                className="flex-1 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center justify-center gap-2"
              >
                <Bell className="w-4 h-4" /> Schedule Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
