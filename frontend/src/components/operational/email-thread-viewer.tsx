"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail, ChevronDown, ChevronUp, ExternalLink,
  Clock, CheckCircle2, Reply, Send, Loader2,
  AlertCircle, User, Building2, Sparkles,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

export interface ThreadData {
  id: string;
  campaign_id: string;
  campaign_name: string | null;
  prospect_domain: string;
  prospect_name: string | null;
  to_email: string | null;
  subject: string;
  body_html: string;
  status: string;
  follow_up_count: number;
  sent_at: string | null;
  replied_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  confidence_score: number;
  ai_personalization: Record<string, unknown>;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    sent: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    delivered: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    opened: "bg-platform-500/10 text-platform-400 border-platform-500/20",
    replied: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    link_acquired: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    bounced: "bg-red-500/10 text-red-400 border-red-500/20",
    draft: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  };

  return (
    <span className={`px-2 py-0.5 text-[9px] font-mono rounded-full border uppercase ${styles[status] || "bg-slate-500/10 text-slate-400 border-slate-500/20"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function ThreadCard({ thread }: { thread: ThreadData }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-surface-border rounded-lg overflow-hidden bg-surface-darker/50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-3 hover:bg-surface-border/20 transition-colors text-left"
      >
        <div className="shrink-0 mt-0.5">
          <Mail className="w-4 h-4 text-platform-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-200 truncate">{thread.subject}</span>
            <StatusBadge status={thread.status} />
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
              <Building2 className="w-3 h-3" />
              {thread.prospect_domain}
            </span>
            {thread.prospect_name && (
              <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                <User className="w-3 h-3" />
                {thread.prospect_name}
              </span>
            )}
            {thread.sent_at && (
              <span className="text-[10px] font-mono text-slate-600 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(thread.sent_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <div className="shrink-0 text-slate-600">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-surface-border"
          >
            <div className="p-3 space-y-3">
              {thread.replied_at && (
                <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-500 bg-emerald-500/5 px-2 py-1 rounded">
                  <Reply className="w-3 h-3" />
                  Replied on {new Date(thread.replied_at).toLocaleString()}
                </div>
              )}
              <div className="bg-surface-darker rounded p-3 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap font-sans"
                dangerouslySetInnerHTML={{ __html: thread.body_html }}
              />
              {thread.ai_personalization && Object.keys(thread.ai_personalization).length > 0 && (
                <div className="border-t border-surface-border pt-2 mt-2">
                  <span className="text-[9px] font-mono text-slate-600 uppercase tracking-wider">AI Personalization</span>
                  <pre className="text-[10px] text-slate-500 mt-1 font-mono">
                    {JSON.stringify(thread.ai_personalization, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface EmailThreadViewerProps {
  campaignId: string;
}

export function EmailThreadViewer({ campaignId }: EmailThreadViewerProps) {
  const queryClient = useQueryClient();
  const [generating, setGenerating] = useState(false);

  const { data: threads = [], isLoading, isError, error } = useQuery<ThreadData[]>({
    queryKey: ["campaign-threads", campaignId],
    queryFn: () => fetchApi(`/campaigns/${campaignId}/threads`),
    enabled: !!campaignId,
    refetchInterval: 5000,
  });

  const generateEmails = useCallback(async () => {
    setGenerating(true);
    try {
      await fetchApi(`/campaigns/${campaignId}/generate-emails`, {
        method: "POST",
        body: JSON.stringify({ tenant_id: MOCK_TENANT_ID }),
      });
      queryClient.invalidateQueries({ queryKey: ["campaign-threads", campaignId] });
    } catch (err) {
      console.error("Failed to generate emails", err);
    } finally {
      setGenerating(false);
    }
  }, [campaignId, queryClient]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="w-5 h-5 text-platform-500 animate-spin" />
        <span className="ml-2 text-xs text-slate-500">Loading emails...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 py-3 text-red-400">
        <AlertCircle className="w-4 h-4" />
        <span className="text-xs">Failed to load: {(error as Error)?.message || "Unknown error"}</span>
      </div>
    );
  }

  if (threads.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-slate-600">
        <Mail className="w-8 h-8 mb-2" />
        <span className="text-xs mb-4">No emails generated yet</span>
        <button
          onClick={generateEmails}
          disabled={generating}
          className="px-4 py-2 bg-platform-600 hover:bg-platform-500 disabled:bg-slate-700 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-2"
        >
          {generating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4" />
          )}
          {generating ? "GENERATING..." : "GENERATE BESPOKE EMAILS"}
        </button>
      </div>
    );
  }

  const sentCount = threads.filter((t) => ["sent", "delivered", "opened", "replied", "link_acquired"].includes(t.status)).length;
  const replyCount = threads.filter((t) => ["replied", "link_acquired"].includes(t.status)).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-4">
          <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
            <Send className="w-3 h-3" />
            {sentCount} sent
          </span>
          <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
            <Reply className="w-3 h-3" />
            {replyCount} replies
          </span>
          <span className="text-[10px] font-mono text-slate-600 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            {threads.length} total threads
          </span>
        </div>
        <button
          onClick={generateEmails}
          disabled={generating}
          className="px-3 py-1.5 bg-platform-600 hover:bg-platform-500 disabled:bg-slate-700 text-white rounded text-[10px] font-mono font-bold transition-colors flex items-center gap-1.5"
        >
          {generating ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Sparkles className="w-3 h-3" />
          )}
          {generating ? "GENERATING..." : "GENERATE"}
        </button>
      </div>
      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
        {threads.map((thread) => (
          <ThreadCard key={thread.id} thread={thread} />
        ))}
      </div>
    </div>
  );
}
