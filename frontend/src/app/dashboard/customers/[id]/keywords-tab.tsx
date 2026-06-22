"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Search, TrendingUp, DollarSign, BarChart3, Filter, Shield } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface Keyword {
  id: string;
  keyword: string;
  search_volume: number;
  difficulty: number;
  cpc: number;
  competition: number;
  intent: string;
  opportunity_score?: number;
}

function IntentBadge({ intent }: { intent: string }) {
  const config: Record<string, string> = {
    transactional: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    commercial: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    navigational: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    informational: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  };
  const cls = config[intent] || config.informational;
  return <span className={`px-2 py-0.5 text-[10px] font-mono rounded border ${cls}`}>{safeUpper(intent)}</span>;
}

export function KeywordsTab({ customerId }: { customerId: string }) {
  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data: keywords = [], isLoading, error } = useQuery<Keyword[]>({
    queryKey: ["customer", customerId, "keywords"],
    queryFn: async () => {
      const res = await fetchApi<any>(`/seo-intelligence/opportunities?tenant_id=${tid}&limit=100`);
      const items = res?.data || [];
      return items;
    },
    refetchInterval: 60000,
  });

  const total = safeArr<Keyword>(keywords).length;
  const avgVol = total > 0 ? safeArr<Keyword>(keywords).reduce((s, k) => s + safeNum(k.search_volume), 0) / total : 0;
  const avgDiff = total > 0 ? safeArr<Keyword>(keywords).reduce((s, k) => s + safeNum(k.difficulty), 0) / total : 0;
  const byIntent = safeArr<Keyword>(keywords).reduce<Record<string, number>>((acc, k) => {
    acc[k.intent] = (acc[k.intent] || 0) + 1;
    return acc;
  }, {});

  if (isLoading) return <div className="p-6 text-center text-xs font-mono text-slate-500">Loading keywords...</div>;
  if (error) return <div className="p-6 text-center text-xs font-mono text-red-400">Failed to load keywords</div>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Search className="w-3.5 h-3.5" /> Total Keywords
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{total}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <TrendingUp className="w-3.5 h-3.5" /> Avg Volume
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{safeFixed(avgVol, 0)}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Shield className="w-3.5 h-3.5" /> Avg Difficulty
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{safeFixed(avgDiff, 1)}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <BarChart3 className="w-3.5 h-3.5" /> Intents
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{Object.keys(byIntent).length}</p>
        </div>
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-platform-400" />
            <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">Keywords</h3>
          </div>
          <div className="flex items-center gap-1 text-[10px] font-mono text-slate-500 px-2 py-1 rounded border border-surface-border">
            <Filter className="w-3 h-3" /> {total} results
          </div>
        </div>
        <div className="divide-y divide-surface-border max-h-[600px] overflow-y-auto">
          {safeArr<Keyword>(keywords).map((kw) => (
            <div key={kw.id || kw.keyword} className="p-3 hover:bg-surface-border/20 transition-colors">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono text-slate-200">{kw.keyword}</span>
                  <IntentBadge intent={kw.intent} />
                </div>
                <span className="text-[10px] font-mono text-platform-400">
                  Score: {safeFixed(kw.opportunity_score, 2)}
                </span>
              </div>
              <div className="flex items-center gap-4 text-[10px] font-mono text-slate-600">
                <span className="flex items-center gap-1">
                  <TrendingUp className="w-3 h-3 text-emerald-500" /> Vol: {safeLocale(kw.search_volume)}
                </span>
                <span className="flex items-center gap-1">
                  <Shield className="w-3 h-3 text-amber-500" /> KD: {safeNum(kw.difficulty)}
                </span>
                <span className="flex items-center gap-1">
                  <DollarSign className="w-3 h-3 text-blue-500" /> CPC: ${safeFixed(kw.cpc, 2, "0.00")}
                </span>
                <span>Comp: {safeFixed(kw.competition, 2)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
