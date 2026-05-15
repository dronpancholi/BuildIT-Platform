"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle, Stethoscope, Gauge, ClipboardCheck, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface IncidentPrediction {
  type: string;
  probability: number;
  severity: string;
  component: string;
  prevention: string;
}

interface DiagnosticFinding {
  system: string;
  finding: string;
  action: string;
}

interface AutonomousDiagnostics {
  findings: DiagnosticFinding[];
}

interface ComponentPressure {
  component: string;
  pressure_score: number;
  breach_probability: number;
}

interface OperationalPressurePrediction {
  components: ComponentPressure[];
}

interface InfraSelfAnalysis {
  health_score: number;
  critical_issues: number;
  recommendations: string[];
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  low: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

export default function AdvancedSREPage() {
  const { data: predictions, isLoading: loadingPredictions } = useQuery<IncidentPrediction[]>({
    queryKey: ["sre-predictions"],
    queryFn: () => fetchApi("/advanced-sre/incident-predictions"),
    refetchInterval: 15000,
  });

  const { data: diagnostics, isLoading: loadingDiagnostics } = useQuery<AutonomousDiagnostics>({
    queryKey: ["sre-diagnostics"],
    queryFn: () => fetchApi("/advanced-sre/autonomous-diagnostics"),
    refetchInterval: 15000,
  });

  const { data: pressure, isLoading: loadingPressure } = useQuery<OperationalPressurePrediction>({
    queryKey: ["sre-pressure-prediction"],
    queryFn: () => fetchApi("/advanced-sre/operational-pressure-prediction"),
    refetchInterval: 15000,
  });

  const { data: selfAnalysis, isLoading: loadingSelf } = useQuery<InfraSelfAnalysis>({
    queryKey: ["sre-self-analysis"],
    queryFn: () => fetchApi("/advanced-sre/infra-self-analysis"),
    refetchInterval: 15000,
  });

  const predList = predictions || [];
  const findings = diagnostics?.findings || [];
  const components = pressure?.components || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">ADVANCED_SRE</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Advanced SRE Operations Dashboard</p>
        </div>
        {selfAnalysis && (
          <div className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 ${
            selfAnalysis.health_score >= 80 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : selfAnalysis.health_score >= 50 ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-red-500/10 text-red-400 border-red-500/20"
          }`}>
            <ClipboardCheck className="w-4 h-4" />
            {Math.round(selfAnalysis.health_score)}% HEALTH
          </div>
        )}
      </div>

      {loadingPredictions && predList.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Incident Predictions */}
            <motion.div {...slideUp} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">INCIDENT_PREDICTIONS</h3>
                {predList.length > 0 && (
                  <span className="ml-auto px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-400">
                    {predList.length} PREDICTED
                  </span>
                )}
              </div>
              {predList.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No incident predictions</div>
              ) : (
                <div className="space-y-3">
                  {predList.map((p, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-bold ${SEVERITY_BADGE[p.severity] || SEVERITY_BADGE.low}`}>
                          {p.severity.toUpperCase()}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500 uppercase">{p.component}</span>
                      </div>
                      <p className="text-xs font-mono text-slate-300 mb-1">{p.type.replace(/_/g, " ")}</p>
                      <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                        <span className="text-slate-500">Probability</span>
                        <span className={`font-bold ${p.probability >= 0.7 ? "text-emerald-400" : p.probability >= 0.4 ? "text-amber-400" : "text-red-400"}`}>
                          {Math.round(p.probability * 100)}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden mb-2">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${p.probability * 100}%` }}
                          className={`h-full rounded-full ${p.probability >= 0.7 ? "bg-emerald-500" : p.probability >= 0.4 ? "bg-amber-500" : "bg-red-500"}`}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                      <p className="text-[10px] font-mono text-emerald-400">&gt; Prevention: {p.prevention}</p>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Autonomous Diagnostics */}
            <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Stethoscope className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">AUTONOMOUS_DIAGNOSTICS</h3>
              </div>
              {loadingDiagnostics ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : findings.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No diagnostic findings</div>
              ) : (
                <div className="space-y-3">
                  {findings.map((f, i) => (
                    <motion.div
                      key={f.system || i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-slate-200 uppercase">{f.system}</span>
                      </div>
                      <p className="text-[10px] font-mono text-slate-400 mb-1">&gt; {f.finding}</p>
                      <p className="text-[10px] font-mono text-emerald-400">&gt; Action: {f.action}</p>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Operational Pressure Predictions */}
            <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Gauge className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">PRESSURE_PREDICTIONS</h3>
              </div>
              {loadingPressure ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : components.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No pressure data</div>
              ) : (
                <div className="space-y-3">
                  {components.map((c, i) => (
                    <motion.div
                      key={c.component || i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono text-slate-200 uppercase">{c.component.replace(/_/g, " ")}</span>
                        <span className={`text-[10px] font-mono font-bold ${c.pressure_score >= 70 ? "text-red-400" : c.pressure_score >= 40 ? "text-amber-400" : "text-emerald-400"}`}>
                          {Math.round(c.pressure_score)}%
                        </span>
                      </div>
                      <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden mb-2">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${c.pressure_score}%` }}
                          className={`h-full rounded-full ${c.pressure_score >= 70 ? "bg-red-500" : c.pressure_score >= 40 ? "bg-amber-500" : "bg-emerald-500"}`}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className="text-slate-500">Breach Probability</span>
                        <span className={`font-bold ${c.breach_probability >= 0.7 ? "text-red-400" : c.breach_probability >= 0.4 ? "text-amber-400" : "text-emerald-400"}`}>
                          {Math.round(c.breach_probability * 100)}%
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Infra Self-Analysis */}
            <motion.div {...slideUp} transition={{ delay: 0.15 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <ClipboardCheck className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">INFRA_SELF_ANALYSIS</h3>
              </div>
              {loadingSelf ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : !selfAnalysis ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No self-analysis data</div>
              ) : (
                <div className="space-y-4">
                  <div className="text-center">
                    <span className={`text-5xl font-bold font-mono ${selfAnalysis.health_score >= 80 ? "text-emerald-400" : selfAnalysis.health_score >= 50 ? "text-amber-400" : "text-red-400"}`}>
                      {Math.round(selfAnalysis.health_score)}%
                    </span>
                    <p className="text-xs font-mono text-slate-500 mt-1">Infra Health Score</p>
                  </div>
                  <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${selfAnalysis.health_score}%` }}
                      className={`h-full rounded-full ${selfAnalysis.health_score >= 80 ? "bg-emerald-500" : selfAnalysis.health_score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  {selfAnalysis.critical_issues > 0 && (
                    <div className="flex items-center gap-2 p-3 rounded-md bg-red-500/10 border border-red-500/20">
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      <span className="text-xs font-mono text-red-400">{selfAnalysis.critical_issues} critical issues detected</span>
                    </div>
                  )}
                  {selfAnalysis.recommendations.length > 0 && (
                    <div className="pt-3 border-t border-surface-border space-y-1">
                      <p className="text-[10px] font-mono text-emerald-400 uppercase mb-1">Recommendations</p>
                      {selfAnalysis.recommendations.map((r, i) => (
                        <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {r}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </div>
  );
}
