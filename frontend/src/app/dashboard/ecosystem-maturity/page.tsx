"use client";

import { motion } from "framer-motion";
import {
  Building2, Share2, Shield, GitBranch, TrendingUp, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface EcosystemIntelligenceReport {
  active_integrations: number;
  ecosystem_health_score: number;
  integration_breakdown: { name: string; type: string; status: string; health: number }[];
  optimization_opportunities: string[];
}

interface CrossSystemTrace {
  total_systems_traversed: number;
  trace_completeness: number;
  system_boundaries: { from_system: string; to_system: string; latency_ms: number; complete: boolean }[];
  gap_analysis: string[];
}

interface ComplianceEvolutionReport {
  current_compliance_score: number;
  compliance_evolution: { quarter: string; compliance_score: number; frameworks_applied: string[] }[];
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const STATUS_BADGE: Record<string, string> = {
  active: "bg-green-500/10 text-green-400 border-green-500/20",
  degraded: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  inactive: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function EcosystemMaturityPage() {
  const { data: ecosystem, isLoading: loadingEcosystem } = useQuery<EcosystemIntelligenceReport>({
    queryKey: ["ecosystem-intelligence"],
    queryFn: () => fetchApi("/ecosystem-maturity/ecosystem-intelligence?scope=platform"),
  });

  const { data: trace, isLoading: loadingTrace } = useQuery<CrossSystemTrace>({
    queryKey: ["cross-system-trace"],
    queryFn: () => fetchApi("/ecosystem-maturity/cross-system-trace?workflow_id=wf-eco-001"),
  });

  const { data: compliance, isLoading: loadingCompliance } = useQuery<ComplianceEvolutionReport>({
    queryKey: ["compliance-evolution"],
    queryFn: () => fetchApi("/ecosystem-maturity/compliance-evolution?org_id=org-main"),
  });

  if (loadingEcosystem || loadingTrace || loadingCompliance) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Ecosystem Maturity</h1>
        <p className="text-slate-400 mt-1">Integration lifecycle, ecosystem intelligence, and compliance evolution</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Share2 className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Ecosystem Health</h2>
          </div>
          {ecosystem && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-slate-100">{ecosystem.active_integrations}</span>
                <span className="text-sm text-slate-400">active of {ecosystem.integration_breakdown.length}</span>
              </div>
              <div className="text-sm text-slate-500">
                Health: <span className="text-slate-200">{(ecosystem.ecosystem_health_score * 100).toFixed(0)}%</span>
              </div>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {ecosystem.integration_breakdown.slice(0, 6).map((int, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-300">{int.name}</span>
                      <span className="text-slate-500 text-[10px]">{int.type}</span>
                    </div>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${STATUS_BADGE[int.status] || ""}`}>
                      {int.status}
                    </span>
                  </div>
                ))}
              </div>
              {ecosystem.optimization_opportunities.length > 0 && (
                <div className="pt-2 border-t border-slate-700/40">
                  <div className="text-xs text-slate-500 mb-1">Opportunities:</div>
                  {ecosystem.optimization_opportunities.map((o, i) => (
                    <div key={i} className="text-xs text-slate-400 flex items-center gap-1">
                      <span className="text-platform-400">•</span> {o}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Cross-System Tracing</h2>
          </div>
          {trace && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-amber-400">{trace.total_systems_traversed}</span>
                <span className="text-sm text-slate-400">systems traversed</span>
              </div>
              <div className="text-sm text-slate-500">
                Completeness: <span className="text-slate-200">{(trace.trace_completeness * 100).toFixed(0)}%</span>
              </div>
              {trace.system_boundaries.map((b, i) => (
                <div key={i} className="flex items-center justify-between text-xs p-1.5 rounded bg-slate-800/30">
                  <span className="text-slate-300">{b.from_system} → {b.to_system}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">{b.latency_ms}ms</span>
                    {b.complete ? (
                      <span className="text-green-400">✓</span>
                    ) : (
                      <span className="text-red-400">✗</span>
                    )}
                  </div>
                </div>
              ))}
              {trace.gap_analysis.length > 0 && (
                <div className="text-xs text-red-400">{trace.gap_analysis[0]}</div>
              )}
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-green-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Compliance Evolution</h2>
          </div>
          {compliance && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-green-400">{(compliance.current_compliance_score * 100).toFixed(0)}%</span>
                <span className="text-sm text-slate-400">current</span>
              </div>
              {compliance.compliance_evolution.map((q, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className="w-8 text-slate-400">{q.quarter}</span>
                  <div className="flex-1 bg-surface-border rounded-full h-1.5">
                    <div className="bg-green-500 rounded-full h-1.5" style={{ width: `${q.compliance_score * 100}%` }} />
                  </div>
                  <span className="w-8 text-right text-slate-400">{(q.compliance_score * 100).toFixed(0)}%</span>
                </div>
              ))}
              <div className="text-xs text-slate-500">
                Frameworks: {compliance.compliance_evolution[compliance.compliance_evolution.length - 1]?.frameworks_applied.join(", ") || "N/A"}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
