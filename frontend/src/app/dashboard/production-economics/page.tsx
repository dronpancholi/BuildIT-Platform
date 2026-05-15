"use client";

import { motion } from "framer-motion";
import {
  DollarSign, TrendingUp, BarChart3, Cpu, Gauge, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface EfficiencyScore {
  overall_efficiency: number;
  cost_efficiency: number;
  resource_efficiency: number;
  operational_efficiency: number;
}

interface DynamicInfraRecommendation {
  recommendation_type: string;
  description: string;
  estimated_savings: number;
  implementation_cost: number;
  net_benefit: number;
  priority: string;
}

interface OperationalROI {
  roi_percentage: number;
  payback_period_months: number;
  risk_adjusted_roi: number;
  confidence: number;
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

export default function ProductionEconomicsPage() {
  const { data: efficiency, isLoading: loadingEfficiency } = useQuery<EfficiencyScore>({
    queryKey: ["efficiency-score"],
    queryFn: () => fetchApi("/production-economics/efficiency-score?service_id=platform-core"),
  });

  const { data: recommendations, isLoading: loadingRecs } = useQuery<DynamicInfraRecommendation[]>({
    queryKey: ["dynamic-recs"],
    queryFn: () => fetchApi("/production-economics/dynamic-infra-recommendations?scope=platform"),
  });

  const { data: roi, isLoading: loadingRoi } = useQuery<OperationalROI>({
    queryKey: ["operational-roi"],
    queryFn: () => fetchApi("/production-economics/operational-roi?initiative_id=phase6-optimization"),
  });

  if (loadingEfficiency || loadingRecs || loadingRoi) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Production Economics</h1>
        <p className="text-slate-400 mt-1">Cost optimization, efficiency scoring, and operational ROI intelligence</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Gauge className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Efficiency Score</h2>
          </div>
          {efficiency && (
            <div className="space-y-3">
              <span className="text-4xl font-bold text-slate-100">{(efficiency.overall_efficiency * 100).toFixed(0)}%</span>
              <div className="space-y-2 mt-4">
                {[
                  { label: "Cost", value: efficiency.cost_efficiency },
                  { label: "Resource", value: efficiency.resource_efficiency },
                  { label: "Operational", value: efficiency.operational_efficiency },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center gap-2 text-xs">
                    <span className="w-20 text-slate-400">{label}</span>
                    <div className="flex-1 bg-surface-border rounded-full h-1.5">
                      <div className="bg-platform-500 rounded-full h-1.5" style={{ width: `${value * 100}%` }} />
                    </div>
                    <span className="w-8 text-right text-slate-400">{(value * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-green-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">ROI Analysis</h2>
          </div>
          {roi && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-green-400">{roi.roi_percentage}%</span>
                <span className="text-sm text-slate-400">projected ROI</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-slate-400">Payback: <span className="text-slate-200">{roi.payback_period_months} mo</span></div>
                <div className="text-slate-400">Risk-adj: <span className="text-slate-200">{roi.risk_adjusted_roi}%</span></div>
              </div>
              <div className="text-xs text-slate-500">Confidence: {(roi.confidence * 100).toFixed(0)}%</div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Infra Recommendations</h2>
          </div>
          {recommendations && (
            <div className="space-y-2">
              {recommendations.map((r, i) => (
                <div key={i} className="p-2 rounded bg-slate-800/40 border border-slate-700/40">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-slate-200 capitalize">{r.recommendation_type.replace(/_/g, " ")}</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium border ${PRIORITY_BADGE[r.priority] || ""}`}>
                      {r.priority}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-1">{r.description}</p>
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span className="text-green-400">+${r.estimated_savings.toFixed(0)}</span>
                    <span>cost: ${r.implementation_cost.toFixed(0)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
