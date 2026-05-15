"use client";

import { motion } from "framer-motion";
import {
  Shield, Gauge, ClipboardCheck, Activity, FileText, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface StewardshipAssessment {
  stewardship_score: number;
  dimension_scores: Record<string, number>;
  findings: { dimension: string; status: string; score: number }[];
  overall_verdict: string;
}

interface OperationalQualityScore {
  quality_score: number;
  reliability_score: number;
  maintainability_score: number;
  observability_score: number;
  security_score: number;
}

interface PlatformSustainabilityReport {
  sustainability_score: number;
  technical_debt_index: number;
  bus_factor: number;
  documentation_coverage: number;
  recommendations: string[];
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const VERDICT_BADGE: Record<string, string> = {
  excellent: "bg-green-500/10 text-green-400 border-green-500/20",
  good: "bg-platform-500/10 text-platform-400 border-platform-500/20",
  needs_improvement: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

export default function PlatformStewardshipPage() {
  const { data: stewardship, isLoading: loadingSteward } = useQuery<StewardshipAssessment>({
    queryKey: ["stewardship"],
    queryFn: () => fetchApi("/platform-stewardship/stewardship-assessment?scope=platform"),
  });

  const { data: quality, isLoading: loadingQuality } = useQuery<OperationalQualityScore>({
    queryKey: ["quality-score"],
    queryFn: () => fetchApi("/platform-stewardship/operational-quality-score?service_id=platform-core"),
  });

  const { data: sustainability, isLoading: loadingSustain } = useQuery<PlatformSustainabilityReport>({
    queryKey: ["platform-sustainability"],
    queryFn: () => fetchApi("/platform-stewardship/platform-sustainability?scope=platform"),
  });

  if (loadingSteward || loadingQuality || loadingSustain) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Platform Stewardship</h1>
        <p className="text-slate-400 mt-1">Operational stewardship, quality scoring, and platform sustainability</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Stewardship</h2>
          </div>
          {stewardship && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-4xl font-bold text-slate-100">{(stewardship.stewardship_score * 100).toFixed(0)}%</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${VERDICT_BADGE[stewardship.overall_verdict] || ""}`}>
                  {stewardship.overall_verdict}
                </span>
              </div>
              <div className="space-y-2">
                {stewardship.findings.map((f, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 capitalize">{f.dimension}</span>
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${f.status === "good" ? "bg-green-400" : "bg-amber-400"}`} />
                      <span className="text-slate-300">{(f.score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Gauge className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Operational Quality</h2>
          </div>
          {quality && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-amber-400">{(quality.quality_score * 100).toFixed(0)}%</span>
                <span className="text-sm text-slate-400">overall quality</span>
              </div>
              <div className="space-y-2">
                {[
                  { label: "Reliability", value: quality.reliability_score },
                  { label: "Maintainability", value: quality.maintainability_score },
                  { label: "Observability", value: quality.observability_score },
                  { label: "Security", value: quality.security_score },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center gap-2 text-xs">
                    <span className="w-24 text-slate-400">{label}</span>
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
            <FileText className="w-5 h-5 text-purple-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Sustainability</h2>
          </div>
          {sustainability && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-purple-400">{(sustainability.sustainability_score * 100).toFixed(0)}%</span>
                <span className="text-sm text-slate-400">sustainability</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-slate-400">Tech debt: <span className="text-slate-200">{(sustainability.technical_debt_index * 100).toFixed(0)}%</span></div>
                <div className="text-slate-400">Bus factor: <span className="text-slate-200">{sustainability.bus_factor}</span></div>
                <div className="text-slate-400">Docs: <span className="text-slate-200">{(sustainability.documentation_coverage * 100).toFixed(0)}%</span></div>
              </div>
              <div className="pt-2 border-t border-slate-700/40">
                <div className="text-xs text-slate-500 mb-1">Recommendations:</div>
                {sustainability.recommendations.map((r, i) => (
                  <div key={i} className="text-xs text-slate-400 flex items-start gap-1">
                    <span className="text-platform-400 mt-0.5">•</span> {r}
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
