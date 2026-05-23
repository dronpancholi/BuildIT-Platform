"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Search, Sparkles, Loader2, Target,
  Globe, ArrowUpRight, Users, Check, X, Plus,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useCommandCenter } from "@/hooks/use-command-center";
import { KeywordIntelligencePanel } from "@/components/operational/keyword-intelligence-panel";
import { PageGuide } from "@/components/ui/page-guide";
import type { KeywordOpportunity } from "@/types/business-intelligence";

export default function KeywordsPage() {
  const { openCommand } = useCommandCenter();
  const router = useRouter();
  const [viewMode, setViewMode] = useState<"intelligence" | "history">("intelligence");
  const [showAssignmentModal, setShowAssignmentModal] = useState(false);
  const [selectedKeyword, setSelectedKeyword] = useState<KeywordOpportunity | null>(null);
  const [assignmentForm, setAssignmentForm] = useState({
    campaignId: "",
    cluster: "",
    priority: "medium",
  });

  const { data: opportunities = [], isLoading: loadingOpps } = useQuery<KeywordOpportunity[]>({
    queryKey: ["keyword-opportunities"],
    queryFn: () => fetchApi<any>("/business-intelligence/intelligence/keyword-opportunities")
      .then((d) => d?.opportunities ?? []),
    refetchInterval: 30000,
  });

  const { data: history = [], isLoading: loadingHistory } = useQuery<any[]>({
    queryKey: ["keywords", "research"],
    queryFn: () => fetchApi(`/keywords/research?tenant_id=${MOCK_TENANT_ID}`),
    enabled: viewMode === "history",
  });

  const topOpportunities = useMemo(() =>
    [...opportunities].sort((a, b) => b.opportunity_score - a.opportunity_score).slice(0, 20),
    [opportunities],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">INTELLIGENCE</h1>
          <p className="text-slate-400 mt-1 font-mono text-xs uppercase tracking-widest">
            Live keyword intelligence &amp; semantic clustering
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-surface-darker rounded-lg border border-surface-border p-0.5">
            <button
              onClick={() => setViewMode("intelligence")}
              className={`px-3 py-1.5 text-[10px] font-mono rounded-md transition-all ${
                viewMode === "intelligence"
                  ? "bg-platform-500/10 text-platform-400 border border-platform-500/20"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              INTELLIGENCE
            </button>
            <button
              onClick={() => setViewMode("history")}
              className={`px-3 py-1.5 text-[10px] font-mono rounded-md transition-all ${
                viewMode === "history"
                  ? "bg-platform-500/10 text-platform-400 border border-platform-500/20"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              HISTORY
            </button>
          </div>
          <button
            onClick={() => openCommand("keyword_discovery")}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-bold font-mono transition-colors shadow-lg shadow-emerald-900/20 flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            DISCOVERY
          </button>
        </div>
      </div>

      <PageGuide title="About Keywords">
        <p>The <strong>Intelligence</strong> view shows live keyword opportunities ranked by opportunity score, search volume, and difficulty. The <strong>History</strong> view shows past keyword research sessions.</p>
        <p>Use the <strong>Discovery</strong> button to run new keyword research from a seed term.</p>
      </PageGuide>

      {viewMode === "intelligence" ? (
        <>
          {loadingOpps ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
            </div>
          ) : (
            <>
              <KeywordIntelligencePanel />

              {/* Top Opportunities Table */}
              <div className="glass-panel overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-surface-border bg-surface-darker/50">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-platform-400" />
                    <h3 className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
                      Keyword Opportunity Leaderboard
                    </h3>
                    <span className="text-[9px] font-mono text-slate-600">
                      {topOpportunities.length} ranked by opportunity score
                    </span>
                  </div>
                </div>
                <div className="divide-y divide-surface-border">
                  {topOpportunities.length === 0 ? (
                    <div className="p-12 text-center">
                      <Search className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                      <p className="text-xs font-mono text-slate-500">No opportunity data yet. Run keyword discovery to find opportunities.</p>
                    </div>
                  ) : (
                    topOpportunities.map((opp, i) => {
                      const oppPct = Math.round(opp.opportunity_score * 100);
                      return (
                        <motion.div
                          key={opp.keyword}
                          initial={{ opacity: 0, x: -5 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.02 }}
                          className="px-5 py-3 hover:bg-surface-border/30 transition-colors flex items-center gap-4 cursor-pointer"
                          onClick={() => {
                            setSelectedKeyword(opp);
                            setShowAssignmentModal(true);
                          }}
                        >
                          <span className="text-[10px] font-mono text-slate-600 w-6 text-right font-bold">
                            {i + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-mono text-slate-200 truncate">{opp.keyword}</p>
                            <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500 mt-0.5">
                              <span className="flex items-center gap-1">
                                <Globe className="w-3 h-3" />
                                {opp.search_volume.toLocaleString()} vol
                              </span>
                              <span>difficulty {opp.difficulty}%</span>
                              {opp.cpc > 0 && <span>CPC ${opp.cpc.toFixed(2)}</span>}
                              <p className="text-[10px] font-mono text-slate-500">{opp.cluster && <span className="text-platform-500/70">{opp.cluster}</span>}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0">
                            <div className="w-20 h-2 bg-surface-darker rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${oppPct}%` }}
                                transition={{ duration: 0.5, delay: i * 0.03 }}
                                className={`h-full rounded-full ${
                                  oppPct > 70 ? "bg-emerald-500" :
                                  oppPct > 50 ? "bg-amber-500" :
                                  "bg-platform-500"
                                }`}
                              />
                            </div>
                            <span className={`text-xs font-mono font-bold w-10 text-right ${
                              oppPct > 70 ? "text-emerald-400" :
                              oppPct > 50 ? "text-amber-400" :
                              "text-platform-400"
                            }`}>
                              {oppPct}%
                            </span>
</div>
                      )}
                    ))}
                  </div>
                )}
              </div>
              {/* Keyword Assignment Modal */}
              {showAssignmentModal && selectedKeyword && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
                  <div className="glass-panel w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
                    <div className="p-6 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
                      <div>
                        <h2 className="text-xl font-bold text-slate-100">Assign Keyword</h2>
                        <p className="text-sm text-slate-400">{selectedKeyword.keyword}</p>
                      </div>
                      <button
                        onClick={() => {
                          setShowAssignmentModal(false);
                          setSelectedKeyword(null);
                        }}
                        className="p-2 hover:bg-surface-border rounded-lg transition-colors"
                      >
                        <X className="w-5 h-5 text-slate-400" />
                      </button>
                    </div>
                    <div className="p-6 overflow-y-auto space-y-4">
                      <div>
                        <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Target Campaign</label>
                        <select
                          value={assignmentForm.campaignId}
                          onChange={(e) => setAssignmentForm({ ...assignmentForm, campaignId: e.target.value })}
                          className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                        >
                          <option value="">Select a campaign...</option>
                          <option value="new">+ Create New Campaign</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Content Cluster</label>
                        <input
                          type="text"
                          placeholder="e.g., SEO Best Practices"
                          value={assignmentForm.cluster}
                          onChange={(e) => setAssignmentForm({ ...assignmentForm, cluster: e.target.value })}
                          className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Priority</label>
                        <div className="flex gap-2">
                          {["low", "medium", "high"].map((p) => (
                            <button
                              key={p}
                              onClick={() => setAssignmentForm({ ...assignmentForm, priority: p })}
                              className={`flex-1 px-3 py-2 rounded-lg text-xs font-mono uppercase transition-all ${
                                assignmentForm.priority === p
                                  ? p === "high"
                                    ? "bg-red-500/20 text-red-400 border border-red-500/30"
                                    : p === "medium"
                                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                    : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                  : "bg-slate-900 text-slate-500 border border-surface-border hover:border-slate-600"
                              }`}
                            >
                              {p}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="glass-panel p-4 bg-slate-900/50">
                        <h4 className="text-xs font-mono text-slate-400 uppercase mb-2">Keyword Details</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div>
                            <span className="text-slate-500">Search Volume:</span>
                            <span className="ml-2 text-slate-300">{selectedKeyword.search_volume.toLocaleString()}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Difficulty:</span>
                            <span className="ml-2 text-slate-300">{selectedKeyword.difficulty}%</span>
                          </div>
                          <div>
                            <span className="text-slate-500">CPC:</span>
                            <span className="ml-2 text-slate-300">${selectedKeyword.cpc?.toFixed(2) || "0.00"}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Opportunity:</span>
                            <span className="ml-2 text-emerald-400">{Math.round(selectedKeyword.opportunity_score * 100)}%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
                      <button
                        onClick={() => {
                          setShowAssignmentModal(false);
                          setSelectedKeyword(null);
                        }}
                        className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => {
                          // Would call assignment mutation
                          setShowAssignmentModal(false);
                          setSelectedKeyword(null);
                          setAssignmentForm({ campaignId: "", cluster: "", priority: "medium" });
                        }}
                        className="flex-1 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center justify-center gap-2"
                      >
                        <Check className="w-4 h-4" /> Assign Keyword
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      ) : (
        <div className="space-y-4">
          <div className="glass-panel overflow-hidden">
            <div className="p-4 border-b border-surface-border bg-surface-darker/50 flex items-center gap-2">
              <Search className="w-4 h-4 text-slate-500" />
              <span className="text-xs font-bold font-mono text-slate-400 uppercase tracking-widest">Research History</span>
            </div>
            {loadingHistory ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : history.length === 0 ? (
              <div className="p-12 flex flex-col items-center justify-center text-center">
                <div className="w-14 h-14 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-3">
                  <Search className="text-slate-600" size={28} />
                </div>
                <h3 className="text-base font-medium text-slate-300">Start Your Research</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  Enter a seed keyword to begin AI-powered topical mapping.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-surface-border">
                {history.map((h) => (
                  <div key={h.id} className="p-4 hover:bg-surface-border/30 transition-colors flex items-center justify-between group">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded bg-surface-darker border border-surface-border flex items-center justify-center text-emerald-500">
                        <Sparkles size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-slate-200">{h.seed_keyword}</div>
                        <div className="text-[10px] text-slate-500 flex items-center gap-3 mt-0.5 font-mono">
                          <span>{new Date(h.created_at).toLocaleDateString()}</span>
                          <span className="uppercase px-1.5 py-0.5 rounded border border-surface-border bg-surface-darker text-[9px]">
                            {h.status}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setViewMode("intelligence");
                      }}
                      className="px-3 py-1.5 bg-surface-darker border border-surface-border text-slate-400 group-hover:text-emerald-400 group-hover:border-emerald-500/30 rounded text-[10px] font-bold font-mono transition-all flex items-center gap-1"
                    >
                      VIEW <ArrowUpRight className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
