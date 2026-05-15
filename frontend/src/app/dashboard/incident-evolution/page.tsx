"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle, History, GitBranch, Lightbulb, ClipboardList, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface HistoricalIncidentAnalysis {
  total_incidents: number;
  incidents_by_type: Record<string, number>;
  mean_time_to_resolve_minutes: number;
  trend: string;
}

interface PostmortemReport {
  title: string;
  root_cause: string;
  timeline: { time: string; event: string }[];
  action_items: string[];
  lessons_learned: string[];
}

interface IncidentRecommendation {
  recommendation_type: string;
  description: string;
  priority: string;
  estimated_impact: string;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const PRIORITY_BADGE: Record<string, string> = {
  high: "bg-red-500/10 text-red-400 border-red-500/20",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  low: "bg-green-500/10 text-green-400 border-green-500/20",
};

export default function IncidentEvolutionPage() {
  const { data: historyData, isLoading: loadingHistory } = useQuery<HistoricalIncidentAnalysis>({
    queryKey: ["incident-history"],
    queryFn: () => fetchApi("/incident-evolution/historical-analysis?service_id=platform-core"),
  });

  const { data: postmortem, isLoading: loadingPostmortem } = useQuery<PostmortemReport>({
    queryKey: ["postmortem"],
    queryFn: () => fetchApi("/incident-evolution/postmortem?incident_id=inc-2026-001"),
  });

  const { data: recommendations, isLoading: loadingRecs } = useQuery<IncidentRecommendation[]>({
    queryKey: ["incident-recs"],
    queryFn: () => fetchApi("/incident-evolution/incident-recommendations?service_id=platform-core"),
  });

  if (loadingHistory || loadingPostmortem || loadingRecs) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Incident Evolution</h1>
        <p className="text-slate-400 mt-1">Historical incident intelligence, postmortem analysis, and learning memory</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <History className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Historical Analysis</h2>
          </div>
          {historyData && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-4xl font-bold text-slate-100">{historyData.total_incidents}</span>
                <span className="text-sm text-slate-400">total</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-slate-400">MTTR: <span className="text-slate-200">{historyData.mean_time_to_resolve_minutes.toFixed(0)}m</span></div>
                <div className="text-slate-400">Trend: <span className={`${historyData.trend === "improving" ? "text-green-400" : historyData.trend === "degrading" ? "text-red-400" : "text-amber-400"}`}>
                  {historyData.trend}
                </span></div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">By type:</div>
                {Object.entries(historyData.incidents_by_type).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 capitalize">{key.replace(/_/g, " ")}</span>
                    <span className="text-slate-300">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <ClipboardList className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Postmortem</h2>
          </div>
          {postmortem && (
            <div className="space-y-3">
              <div className="text-sm font-medium text-slate-200">{postmortem.title}</div>
              <div className="text-xs text-slate-400">
                <span className="text-slate-500">Root cause:</span> {postmortem.root_cause}
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">Timeline:</div>
                {postmortem.timeline.map((t, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="text-platform-400 w-12 shrink-0">{t.time}</span>
                    <span className="text-slate-400">{t.event}</span>
                  </div>
                ))}
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">Action items:</div>
                {postmortem.action_items.map((a, i) => (
                  <div key={i} className="text-xs text-slate-400 flex items-start gap-1">
                    <span className="text-platform-400 mt-0.5">•</span> {a}
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="w-5 h-5 text-purple-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Recommendations</h2>
          </div>
          {recommendations && (
            <div className="space-y-2">
              {recommendations.map((r, i) => (
                <div key={i} className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-slate-200 capitalize">{r.recommendation_type.replace(/_/g, " ")}</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium border ${PRIORITY_BADGE[r.priority] || ""}`}>
                      {r.priority}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-1">{r.description}</p>
                  <p className="text-xs text-slate-500">{r.estimated_impact}</p>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
