"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Mail, Loader2, AlertCircle, Clock, User, Building2, CheckCircle2,
  Search, ArrowRight, Edit3, Send, Reply, Link2, Calendar, Save, X,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import type { ThreadData } from "@/components/operational/email-thread-viewer";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

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

  const { data: threads = [], isLoading, isError } = useQuery<ThreadData[]>({
    queryKey: ["all-threads"],
    queryFn: () => fetchApi(`/campaigns/threads/all?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 10000,
  });

  const filtered = threads.filter((t) =>
    !searchQuery ||
    safeLower(t.subject, "").includes(safeLower(searchQuery, "")) ||
    safeLower(t.prospect_domain, "").includes(safeLower(searchQuery, "")) ||
    safeLower(t.to_email, "").includes(safeLower(searchQuery, "")) ||
    safeLower(t.campaign_name, "").includes(safeLower(searchQuery, ""))
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
        <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400">
          {safeArr(threads).length} THREADS
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
            ) : safeArr(filtered).length === 0 ? (
              <div className="p-8 text-center">
                <Mail className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-xs font-mono text-slate-500">No emails found. Emails appear here when campaigns generate outreach.</p>
              </div>
            ) : (
              <div className="divide-y divide-surface-border">
                {safeArr<ThreadData>(filtered).map((t) => (
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
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 bg-surface-dark flex flex-col h-full overflow-hidden">
          {selectedThread ? (
            <div className="flex flex-col h-full">
              {/* Header */}
              <div className="p-6 border-b border-surface-border shrink-0 bg-surface-darker/30">
                <h2 className="text-xl font-medium text-slate-100 mb-4">{selectedThread.subject}</h2>

                <div className="flex flex-wrap gap-4 text-xs font-mono text-slate-400">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">To:</span>
                    <span className="text-slate-200">{selectedThread.to_email || "Pending resolution"}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">Domain:</span>
                    <span className="flex items-center gap-1 text-platform-400 bg-platform-500/10 px-2 py-0.5 rounded">
                      <Building2 className="w-3 h-3" />
                      {selectedThread.prospect_domain}
                    </span>
                  </div>
                  {selectedThread.prospect_name && (
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">Contact:</span>
                      <span className="flex items-center gap-1 text-slate-300">
                        <User className="w-3 h-3" />
                        {selectedThread.prospect_name}
                      </span>
                    </div>
                  )}
                  {selectedThread.campaign_name && (
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">Campaign:</span>
                      <span className="text-slate-300">{selectedThread.campaign_name}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 ml-auto">
                    <Clock className="w-3 h-3 text-slate-500" />
                    <span className="text-slate-400">
                      {selectedThread.sent_at
                        ? `Sent: ${new Date(selectedThread.sent_at).toLocaleString()}`
                        : `Created: ${selectedThread.created_at ? new Date(selectedThread.created_at).toLocaleString() : "N/A"}`}
                    </span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-surface-border/50">
                  {selectedThread.status === "draft" && (
                    <>
                      <button
                        onClick={handleEdit}
                        disabled={updateMutation.isPending}
                        className="px-3 py-1.5 text-xs font-mono rounded-md border border-surface-border text-slate-300 hover:text-slate-100 hover:border-platform-500/30 flex items-center gap-1.5"
                      >
                        <Edit3 className="w-3.5 h-3.5" /> Edit
                      </button>
                      <button
                        onClick={handleSend}
                        disabled={sendMutation.isPending}
                        className="px-3 py-1.5 text-xs font-mono rounded-md bg-platform-600 hover:bg-platform-500 text-white flex items-center gap-1.5"
                      >
                        {sendMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                        Send
                      </button>
                    </>
                  )}
                  {selectedThread.status === "sent" && (
                    <button
                      onClick={handleReply}
                      disabled={replyMutation.isPending}
                      className="px-3 py-1.5 text-xs font-mono rounded-md border border-surface-border text-slate-300 hover:text-slate-100 hover:border-blue-500/30 flex items-center gap-1.5"
                    >
                      {replyMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Reply className="w-3.5 h-3.5" />}
                      Simulate Reply
                    </button>
                  )}
                  {(selectedThread.status === "sent" || selectedThread.status === "replied") && (
                    <button
                      onClick={() => setShowFollowUp(!showFollowUp)}
                      className="px-3 py-1.5 text-xs font-mono rounded-md border border-surface-border text-slate-300 hover:text-slate-100 hover:border-amber-500/30 flex items-center gap-1.5"
                    >
                      <Calendar className="w-3.5 h-3.5" /> Follow-Up
                    </button>
                  )}
                  {(selectedThread.status === "replied" || selectedThread.status === "sent") && (
                    <button
                      onClick={() => setShowLinkAcquired(!showLinkAcquired)}
                      className="px-3 py-1.5 text-xs font-mono rounded-md border border-surface-border text-slate-300 hover:text-slate-100 hover:border-purple-500/30 flex items-center gap-1.5"
                    >
                      <Link2 className="w-3.5 h-3.5" /> Mark Link Acquired
                    </button>
                  )}
                  <span className={`px-2 py-0.5 text-[9px] font-mono rounded-full border uppercase ${statusColor(selectedThread.status)}`}>
                    {selectedThread.status.replace(/_/g, " ")}
                  </span>
                </div>
              </div>

              {/* Content Area */}
              <div className="flex-1 overflow-y-auto p-6">
                {editing ? (
                  <div className="space-y-4 max-w-3xl">
                    <div>
                      <label className="text-[10px] font-mono text-slate-500 uppercase">Subject</label>
                      <input
                        value={editSubject}
                        onChange={(e) => setEditSubject(e.target.value)}
                        className="w-full mt-1 bg-surface-darker border border-surface-border rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-mono text-slate-500 uppercase">Body (HTML)</label>
                      <textarea
                        value={editBody}
                        onChange={(e) => setEditBody(e.target.value)}
                        rows={12}
                        className="w-full mt-1 bg-surface-darker border border-surface-border rounded px-3 py-2 text-sm text-slate-200 font-mono focus:outline-none focus:border-platform-500"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleSave}
                        disabled={updateMutation.isPending}
                        className="px-4 py-2 text-xs font-mono rounded-md bg-platform-600 hover:bg-platform-500 text-white flex items-center gap-1.5"
                      >
                        {updateMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                        Save
                      </button>
                      <button
                        onClick={() => setEditing(false)}
                        className="px-4 py-2 text-xs font-mono rounded-md border border-surface-border text-slate-400 hover:text-slate-200 flex items-center gap-1.5"
                      >
                        <X className="w-3.5 h-3.5" /> Cancel
                      </button>
                    </div>
                  </div>
                ) : showFollowUp ? (
                  <div className="space-y-4 max-w-3xl">
                    <h3 className="text-sm font-mono text-slate-300 flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-amber-500" /> Schedule Follow-Up
                    </h3>
                    <div>
                      <label className="text-[10px] font-mono text-slate-500 uppercase">Follow-Up Body (HTML)</label>
                      <textarea
                        value={followUpBody}
                        onChange={(e) => setFollowUpBody(e.target.value)}
                        placeholder="<p>Hi [Name],</p><p>Just following up on my previous email...</p>"
                        rows={8}
                        className="w-full mt-1 bg-surface-darker border border-surface-border rounded px-3 py-2 text-sm text-slate-200 font-mono focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleFollowUp}
                        disabled={followUpMutation.isPending || !followUpBody.trim()}
                        className="px-4 py-2 text-xs font-mono rounded-md bg-amber-600 hover:bg-amber-500 text-white flex items-center gap-1.5"
                      >
                        {followUpMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                        Send Follow-Up
                      </button>
                      <button
                        onClick={() => { setShowFollowUp(false); setFollowUpBody(""); }}
                        className="px-4 py-2 text-xs font-mono rounded-md border border-surface-border text-slate-400 hover:text-slate-200 flex items-center gap-1.5"
                      >
                        <X className="w-3.5 h-3.5" /> Cancel
                      </button>
                    </div>
                  </div>
                ) : showLinkAcquired ? (
                  <div className="space-y-4 max-w-3xl">
                    <h3 className="text-sm font-mono text-slate-300 flex items-center gap-2">
                      <Link2 className="w-4 h-4 text-purple-500" /> Mark Link Acquired
                    </h3>
                    <div>
                      <label className="text-[10px] font-mono text-slate-500 uppercase">Acquired URL</label>
                      <input
                        value={acquiredUrl}
                        onChange={(e) => setAcquiredUrl(e.target.value)}
                        placeholder="https://example.com/blog/post-with-link"
                        className="w-full mt-1 bg-surface-darker border border-surface-border rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-purple-500"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-mono text-slate-500 uppercase">Anchor Text (optional)</label>
                      <input
                        value={acquiredAnchor}
                        onChange={(e) => setAcquiredAnchor(e.target.value)}
                        placeholder="Target keyword"
                        className="w-full mt-1 bg-surface-darker border border-surface-border rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-purple-500"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleLinkAcquired}
                        disabled={linkMutation.isPending || !acquiredUrl.trim()}
                        className="px-4 py-2 text-xs font-mono rounded-md bg-purple-600 hover:bg-purple-500 text-white flex items-center gap-1.5"
                      >
                        {linkMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                        Confirm Acquisition
                      </button>
                      <button
                        onClick={() => { setShowLinkAcquired(false); setAcquiredUrl(""); setAcquiredAnchor(""); }}
                        className="px-4 py-2 text-xs font-mono rounded-md border border-surface-border text-slate-400 hover:text-slate-200 flex items-center gap-1.5"
                      >
                        <X className="w-3.5 h-3.5" /> Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div
                      className="bg-white/5 border border-surface-border rounded-lg p-6 text-sm text-slate-300 leading-relaxed font-sans max-w-3xl"
                      dangerouslySetInnerHTML={{ __html: selectedThread.body_html }}
                    />

                    {selectedThread.ai_personalization && safeKeys(selectedThread.ai_personalization).length > 0 && (
                      <div className="mt-8 max-w-3xl">
                        <h3 className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                          <CheckCircle2 className="w-3 h-3 text-platform-500" />
                          AI Generation Metadata
                        </h3>
                        <pre className="p-4 rounded-lg bg-surface-darker border border-surface-border text-[10px] text-slate-400 font-mono overflow-x-auto">
                          {JSON.stringify(selectedThread.ai_personalization, null, 2)}
                        </pre>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 h-full">
              <Mail className="w-12 h-12 mb-4 opacity-20" />
              <p className="text-sm">Select an email to view</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
