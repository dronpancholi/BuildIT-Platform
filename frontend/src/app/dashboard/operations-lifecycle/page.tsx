"use client";

import { motion } from "framer-motion";
import {
  Activity, Clock, AlertTriangle, TrendingDown, RefreshCcw, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface LifecycleScore {
  overall_score: number;
  age_days: number;
  dependency_health: number;
  entropy_level: number;
  rot_risk: string;
  recommendations: string[];
}

interface DegradationForecast {
  current_health: number;
  predicted_health_trajectory: { day: number; predicted_health: number }[];
  breach_probability: number;
}

interface SustainabilityAnalytics {
  sustainability_score: number;
  dimension_scores: Record<string, number>;
  long_term_viability: string;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const RISK_BADGE: Record<string, string> = {
  low: "bg-green-500/10 text-green-400 border-green-500/20",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  high: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function OperationsLifecyclePage() {
  const { data: score, isLoading: loadingScore } = useQuery<LifecycleScore>({
    queryKey: ["lifecycle-score"],
    queryFn: () => fetchApi("/operational-lifecycle/lifecycle-score?service_id=platform-core"),
  });

  const { data: degradation, isLoading: loadingDegradation } = useQuery<DegradationForecast>({
    queryKey: ["degradation-forecast"],
    queryFn: () => fetchApi("/operational-lifecycle/degradation-forecast?service_id=platform-core&horizon_days=90"),
  });

  const { data: sustainability, isLoading: loadingSustainability } = useQuery<SustainabilityAnalytics>({
    queryKey: ["sustainability"],
    queryFn: () => fetchApi("/operational-lifecycle/sustainability-analytics?scope=platform"),
  });

  if (loadingScore || loadingDegradation || loadingSustainability) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Operations Lifecycle</h1>
        <p className="text-slate-400 mt-1">Long-term operational survivability and infrastructure aging analysis</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Lifecycle Score</h2>
          </div>
          {score && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-4xl font-bold text-slate-100">{(score.overall_score * 100).toFixed(0)}%</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${RISK_BADGE[score.rot_risk]}`}>
                  {score.rot_risk} rot risk
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-slate-400">Age: <span className="text-slate-200">{score.age_days} days</span></div>
                <div className="text-slate-400">Dep health: <span className="text-slate-200">{(score.dependency_health * 100).toFixed(0)}%</span></div>
                <div className="text-slate-400">Entropy: <span className="text-slate-200">{(score.entropy_level * 100).toFixed(0)}%</span></div>
              </div>
              <ul className="space-y-1 text-xs">
                {score.recommendations.map((r, i) => (
                  <li key={i} className="text-slate-400 flex items-start gap-1">
                    <span className="text-platform-400 mt-0.5">•</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Degradation Forecast</h2>
          </div>
          {degradation && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-amber-400">{(degradation.current_health * 100).toFixed(0)}%</span>
                <span className="text-sm text-slate-400">current health</span>
              </div>
              <div className="flex gap-2">
                {degradation.predicted_health_trajectory.filter((_, i) => i % 3 === 0).map((p) => (
                  <div key={p.day} className="flex flex-col items-center flex-1">
                    <div className="w-full bg-surface-border rounded-full h-2">
                      <div className="bg-platform-500 rounded-full h-2 transition-all" style={{ width: `${p.predicted_health * 100}%` }} />
                    </div>
                    <span className="text-xs text-slate-500 mt-1">d{p.day}</span>
                  </div>
                ))}
              </div>
              <div className="text-sm text-slate-400">
                Breach probability: <span className="text-slate-200">{(degradation.breach_probability * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <RefreshCcw className="w-5 h-5 text-green-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Sustainability</h2>
          </div>
          {sustainability && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-green-400">{(sustainability.sustainability_score * 100).toFixed(0)}%</span>
                <span className={`text-xs font-medium ${sustainability.long_term_viability === "healthy" ? "text-green-400" : "text-amber-400"}`}>
                  {sustainability.long_term_viability}
                </span>
              </div>
              <div className="space-y-2">
                {Object.entries(sustainability.dimension_scores).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-2 text-sm">
                    <span className="w-28 text-slate-400 capitalize">{key}</span>
                    <div className="flex-1 bg-surface-border rounded-full h-1.5">
                      <div className="bg-platform-500 rounded-full h-1.5" style={{ width: `${val * 100}%` }} />
                    </div>
                    <span className="text-slate-300 w-8 text-right">{(val * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
