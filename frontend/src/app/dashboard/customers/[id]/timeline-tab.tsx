"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { TrendingUp, GitBranch, Mail, AlertTriangle, CheckCircle2, FileText, Zap, Calendar, Filter } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface TimelineEvent {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  status?: string;
  metadata?: Record<string, any>;
}

const TYPE_ICONS: Record<string, any> = {
  campaign: GitBranch,
  approval: CheckCircle2,
  automation: Zap,
  alert: AlertTriangle,
  report: FileText,
  communication: Mail,
};
const TYPE_COLORS: Record<string, string> = {
  campaign: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  approval: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  automation: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  alert: "text-red-400 bg-red-500/10 border-red-500/20",
  report: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  communication: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
};

export function TimelineTab({ customerId }: { customerId: string }) {
  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";
  const [filter, setFilter] = useState<string>("all");
  const [limit, setLimit] = useState(50);

  const { data: events = [], isLoading, error } = useQuery<TimelineEvent[]>({
    queryKey: ["customer", customerId, "timeline", filter, limit],
    queryFn: async () => {
      const res = await fetchApi<any>(`/customers/${customerId}/timeline?tenant_id=${tid}&limit=${limit}${filter !== "all" ? `&type=${filter}` : ""}`);
      return res || [];
    },
    refetchInterval: 30000,
  });

  const typeCounts = safeArr<TimelineEvent>(events).reduce<Record<string, number>>((acc, e) => {
    acc[e.type] = (acc[e.type] || 0) + 1;
    return acc;
  }, {});

  if (isLoading) return <div className="p-6 text-center text-xs font-mono text-slate-500">Loading timeline...</div>;
  if (error) return <div className="p-6 text-center text-xs font-mono text-red-400">Failed to load timeline</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <div className="flex items-center gap-1">
            {["all", ...safeKeys(typeCounts)].map((t) => (
              <button
                key={t}
                onClick={() => setFilter(t)}
                className={`px-2.5 py-1 text-[10px] font-mono rounded-md transition-all ${
                  filter === t
                    ? "bg-platform-600 text-white"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-border"
                }`}
              >
                {safeStr(t, "").charAt(0).toUpperCase() + safeStr(t, "").slice(1)} ({t === "all" ? safeArr<TimelineEvent>(events).length : safeNum(typeCounts[t])})
              </button>
            ))}
          </div>
        </div>
        <span className="text-[10px] font-mono text-slate-500">{safeArr<TimelineEvent>(events).length} events</span>
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-platform-400" />
            <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">
              {filter === "all" ? "Unified Timeline" : `${filter.charAt(0).toUpperCase() + filter.slice(1)} Events`}
            </h3>
          </div>
        </div>
        <div className="divide-y divide-surface-border max-h-[600px] overflow-y-auto">
          {safeArr<TimelineEvent>(events).length === 0 ? (
            <div className="p-8 text-center">
              <TrendingUp className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Events</h3>
              <p className="text-xs text-slate-500">Activity will appear here as campaigns run and automations trigger</p>
            </div>
          ) : (
            safeArr<TimelineEvent>(events).map((event, i) => {
              const Icon = TYPE_ICONS[event.type] || TrendingUp;
              const colorCls = TYPE_COLORS[event.type] || "text-slate-400 bg-slate-500/10 border-slate-500/20";
              return (
                <div key={event.id || i} className="p-4 hover:bg-surface-border/20 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={`p-1.5 rounded-lg border ${colorCls} mt-0.5`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-mono text-slate-200">{event.title}</span>
                        {event.status && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400">
                            {event.status}
                          </span>
                        )}
                      </div>
                      {event.description && (
                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{event.description}</p>
                      )}
                      <div className="flex items-center gap-3 mt-1.5 text-[10px] font-mono text-slate-600">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" /> {new Date(event.timestamp).toLocaleString()}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] ${
                          colorCls.split(" ")[0] + " " + colorCls.split(" ")[1]
                        } border`}>
                          {event.type}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {safeArr<TimelineEvent>(events).length >= limit && (
        <div className="text-center">
          <button
            onClick={() => setLimit((l) => l + 50)}
            className="px-4 py-2 text-xs font-mono text-platform-400 hover:text-platform-300 transition-colors"
          >
            Load more
          </button>
        </div>
      )}
    </div>
  );
}
