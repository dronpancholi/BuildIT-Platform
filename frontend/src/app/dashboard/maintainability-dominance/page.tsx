"use client";

import { motion } from "framer-motion";
import {
  Wrench, GitBranch, Shield, ArrowUpDown, CheckSquare, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface MaintainabilityScore {
  overall_score: number;
  dimension_scores: Record<string, number>;
  trend: string;
  critical_issues: number;
  recommendations: string[];
}

interface UpgradeSafety {
  safety_score: number;
  safety_checks: { check: string; passed: boolean; detail: string }[];
  recommended_readiness: string;
}

interface SchemaEvolution {
  impact_score: number;
  breaking_changes: string[];
  migration_complexity: string;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const READINESS_BADGE: Record<string, string> = {
  ready: "bg-green-500/10 text-green-400 border-green-500/20",
  needs_work: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  blocked: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function MaintainabilityDominancePage() {
  const { data: score, isLoading: loadingScore } = useQuery<MaintainabilityScore>({
    queryKey: ["maintainability-score"],
    queryFn: () => fetchApi("/maintainability-dominance/maintainability-score?component=platform-core"),
  });

  const { data: upgrade, isLoading: loadingUpgrade } = useQuery<UpgradeSafety>({
    queryKey: ["upgrade-safety"],
    queryFn: () => fetchApi("/maintainability-dominance/upgrade-safety?component=platform-core&target_version=v3.0"),
  });

  const { data: schema, isLoading: loadingSchema } = useQuery<SchemaEvolution>({
    queryKey: ["schema-evolution"],
    queryFn: () => fetchApi("/maintainability-dominance/schema-evolution?entity=WorkflowExecution"),
  });

  if (loadingScore || loadingUpgrade || loadingSchema) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Maintainability Dominance</h1>
        <p className="text-slate-400 mt-1">Enterprise maintainability, schema evolution, and upgrade safety</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Wrench className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Maintainability Score</h2>
          </div>
          {score && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-4xl font-bold text-slate-100">{(score.overall_score * 100).toFixed(0)}%</span>
                <span className={`text-xs font-medium ${score.trend === "improving" ? "text-green-400" : score.trend === "declining" ? "text-red-400" : "text-amber-400"}`}>
                  {score.trend}
                </span>
              </div>
              <div className="text-sm text-slate-500">Critical issues: {score.critical_issues}</div>
              <div className="space-y-1">
                {Object.entries(score.dimension_scores).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-2 text-xs">
                    <span className="w-24 text-slate-400 capitalize">{key}</span>
                    <div className="flex-1 bg-surface-border rounded-full h-1.5">
                      <div className="bg-platform-500 rounded-full h-1.5" style={{ width: `${val * 100}%` }} />
                    </div>
                    <span className="w-8 text-right text-slate-400">{(val * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Upgrade Safety</h2>
          </div>
          {upgrade && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-amber-400">{(upgrade.safety_score * 100).toFixed(0)}%</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${READINESS_BADGE[upgrade.recommended_readiness] || "bg-slate-500/10 text-slate-400"}`}>
                  {upgrade.recommended_readiness}
                </span>
              </div>
              <div className="space-y-2">
                {upgrade.safety_checks.map((check, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    {check.passed ? (
                      <CheckSquare className="w-4 h-4 text-green-400 shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded border-2 border-red-400 shrink-0" />
                    )}
                    <span className="text-slate-400">{check.check}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-5 h-5 text-purple-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Schema Evolution</h2>
          </div>
          {schema && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-purple-400">{(schema.impact_score * 100).toFixed(0)}%</span>
                <span className="text-sm text-slate-400 capitalize">{schema.migration_complexity}</span>
              </div>
              {schema.breaking_changes.length > 0 && (
                <div>
                  <div className="text-xs text-slate-500 mb-1">Breaking changes:</div>
                  {schema.breaking_changes.map((c, i) => (
                    <div key={i} className="text-xs text-red-400 flex items-center gap-1">
                      <span>•</span> {c}
                    </div>
                  ))}
                </div>
              )}
              {schema.breaking_changes.length === 0 && (
                <div className="text-sm text-green-400">No breaking changes detected</div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
