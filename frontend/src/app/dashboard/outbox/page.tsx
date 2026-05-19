"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Mail, Loader2, AlertCircle, Clock, User, Building2, CheckCircle2, Search, ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import type { ThreadData } from "@/components/operational/email-thread-viewer";

export default function OutboxPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);

  const { data: threads = [], isLoading, isError, error } = useQuery<ThreadData[]>({
    queryKey: ["all-threads"],
    queryFn: () => fetchApi("/campaigns/threads/all"),
    refetchInterval: 10000,
  });

  const filtered = threads.filter((t) =>
    !searchQuery ||
    t.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.prospect_domain.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (t.to_email && t.to_email.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const selectedThread = threads.find(t => t.id === selectedThreadId) || filtered[0];

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
              <div className="p-8 text-center text-slate-500 text-xs">
                No emails found.
              </div>
            ) : (
              <div className="divide-y divide-surface-border">
                {filtered.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedThreadId(t.id)}
                    className={`w-full text-left p-4 transition-colors hover:bg-surface-border/50 ${
                      selectedThread?.id === t.id ? "bg-platform-500/5 border-l-2 border-platform-500" : "border-l-2 border-transparent"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-slate-200 truncate pr-2">{t.prospect_domain}</span>
                      <span className={`px-1.5 py-0.5 text-[9px] font-mono rounded border uppercase shrink-0 ${
                        t.status === "sent" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                        "bg-slate-500/10 text-slate-400 border-slate-500/20"
                      }`}>
                        {t.status}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 truncate mb-2">{t.subject}</div>
                    <div className="text-[9px] font-mono text-slate-500 flex items-center justify-between">
                      <span>{t.to_email || "Pending resolution"}</span>
                      {t.sent_at ? (
                        <span>{new Date(t.sent_at).toLocaleDateString()}</span>
                      ) : (
                        <span>Draft</span>
                      )}
                    </div>
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
                  {selectedThread.sent_at && (
                    <div className="flex items-center gap-2 ml-auto">
                      <Clock className="w-3 h-3 text-emerald-500" />
                      <span className="text-emerald-400">{new Date(selectedThread.sent_at).toLocaleString()}</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6">
                <div 
                  className="bg-white/5 border border-surface-border rounded-lg p-6 text-sm text-slate-300 leading-relaxed font-sans max-w-3xl"
                  dangerouslySetInnerHTML={{ __html: selectedThread.body_html }}
                />
                
                {selectedThread.ai_personalization && Object.keys(selectedThread.ai_personalization).length > 0 && (
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
