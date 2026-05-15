"use client";

import { motion } from "framer-motion";
import {
  BrainCircuit, TrendingUp, History, Lightbulb, BarChart3, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface ImprovementRecommendation {
  title: string;
  description: string;
  expected_impact: string;
  effort: string;
  confidence: number;
  reasoning: string;
}

interface WorkflowOptimizationMemory {
  average_improvement_pct: number;
  optimizations_applied: { optimization: string; improvement_pct: number }[];
  memory_span_days: number;
}

interface HistoricalAnomalyLearning {
  anomaly_type: string;
  patterns_identified: { pattern: string; significance: string }[];
  recurrence_risk: number;
  preventive_measures: string[];
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const EFFORT_BADGE: Record<string, string> = {
  low: "bg-green-500/10 text-green-400 border-green-500/20",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  high: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function OperationalEvolutionPage() {
  const { data: recommendations, isLoading: loadingRecs } = useQuery<ImprovementRecommendation[]>({
    queryKey: ["improvement-recommendations"],
    queryFn: () => fetchApi("/operational-evolution/improvement-recommendations?scope=platform"),
  });

  const { data: optimization, isLoading: loadingOpt } = useQuery<WorkflowOptimizationMemory>({
    queryKey: ["optimization-memory"],
    queryFn: () => fetchApi("/operational-evolution/workflow-optimization-memory?workflow_type=data_processing"),
  });

  const { data: anomalyLearning, isLoading: loadingAnomaly } = useQuery<HistoricalAnomalyLearning>({
    queryKey: ["anomaly-learning"],
    queryFn: () => fetchApi("/operational-evolution/historical-anomaly-learning?anomaly_type=timeout"),
  });

  if (loadingRecs || loadingOpt || loadingAnomaly) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Operational Evolution</h1>
        <p className="text-slate-400 mt-1">Self-evolution, pattern learning, and recommendation intelligence</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Improvements</h2>
          </div>
          {recommendations && (
            <div className="space-y-3">
              {recommendations.map((r, i) => (
                <div key={i} className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/40">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-200">{r.title}</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium border ${EFFORT_BADGE[r.effort] || ""}`}>
                      {r.effort}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-2">{r.description}</p>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-slate-500">Impact: <span className="text-platform-400">{r.expected_impact}</span></span>
                    <span className="text-slate-500">Confidence: <span className="text-slate-300">{(r.confidence * 100).toFixed(0)}%</span></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-green-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Optimization Memory</h2>
          </div>
          {optimization && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-green-400">{optimization.average_improvement_pct}%</span>
                <span className="text-sm text-slate-400">avg improvement</span>
              </div>
              <div className="text-xs text-slate-500">Memory span: {optimization.memory_span_days} days</div>
              {optimization.optimizations_applied.map((o, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">{o.optimization}</span>
                  <span className="text-green-400">+{o.improvement_pct}%</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <History className="w-5 h-5 text-purple-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Anomaly Learning</h2>
          </div>
          {anomalyLearning && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-purple-400">{(anomalyLearning.recurrence_risk * 100).toFixed(0)}%</span>
                <span className="text-sm text-slate-400">recurrence risk</span>
              </div>
              {anomalyLearning.patterns_identified.map((p, i) => (
                <div key={i} className="p-2 rounded bg-slate-800/30 border border-slate-700/30">
                  <div className="text-xs font-medium text-slate-200">{p.pattern}</div>
                  <div className="text-xs text-slate-500">Significance: {p.significance}</div>
                </div>
              ))}
              <div>
                <div className="text-xs text-slate-500 mb-1">Prevention:</div>
                {anomalyLearning.preventive_measures.map((m, i) => (
                  <div key={i} className="text-xs text-slate-400 flex items-center gap-1">
                    <span className="text-green-400">•</span> {m}
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
