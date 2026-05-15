"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lightbulb, TrendingUp, AlertTriangle, Target,
  ArrowUpRight, Sparkles, Activity,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import type { Recommendation } from "@/types/business-intelligence";

const PRIORITY_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  P0: { color: "text-red-400 border-red-500/20 bg-red-500/5", icon: <AlertTriangle className="w-3 h-3" />, label: "CRITICAL" },
  P1: { color: "text-amber-400 border-amber-500/20 bg-amber-500/5", icon: <TrendingUp className="w-3 h-3" />, label: "IMPORTANT" },
  P2: { color: "text-platform-400 border-platform-500/20 bg-platform-500/5", icon: <Lightbulb className="w-3 h-3" />, label: "SUGGESTION" },
};

export function RecommendationTicker() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await fetchApi<any>("/business-intelligence/intelligence/recommendations");
        if (data?.recommendations) setRecommendations(data.recommendations);
      } catch {}
    };
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (recommendations.length <= 1) return;
    const interval = setInterval(() => {
      setCurrentIdx((prev) => (prev + 1) % recommendations.length);
    }, 8000);
    return () => clearInterval(interval);
  }, [recommendations.length]);

  if (recommendations.length === 0) return null;

  const current = recommendations[currentIdx];
  const config = PRIORITY_CONFIG[current.priority] || PRIORITY_CONFIG.P2;

  return (
    <div className="glass-panel overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-surface-border bg-surface-darker/50">
        <Sparkles className="w-3.5 h-3.5 text-platform-400" />
        <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider font-bold">Live Intelligence</span>
        <span className="text-[9px] font-mono text-slate-600">{recommendations.length} active recommendations</span>
        <div className="ml-auto flex gap-1">
          {recommendations.slice(0, 5).map((_, i) => (
            <span key={i} className={`w-1.5 h-1.5 rounded-full transition-colors ${
              i === currentIdx ? "bg-platform-500" : "bg-surface-border"
            }`} />
          ))}
        </div>
      </div>
      <div className="p-3 min-h-[60px] flex items-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={current.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="flex items-start gap-3 w-full"
          >
            <div className={`p-1.5 rounded-md border ${config.color} flex-shrink-0`}>
              {config.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className={`text-[10px] font-mono font-bold ${config.color.split(" ")[0]}`}>
                  {config.label}
                </span>
                <span className="text-[9px] font-mono text-slate-600">
                  confidence {(current.confidence * 100).toFixed(0)}% · impact {current.impact_score.toFixed(1)}
                </span>
              </div>
              <p className="text-xs font-mono text-slate-300 truncate">{current.title}</p>
              <p className="text-[10px] font-mono text-slate-500 mt-0.5 line-clamp-1">{current.description}</p>
            </div>
            <ArrowUpRight className="w-3.5 h-3.5 text-slate-600 flex-shrink-0 mt-1" />
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
