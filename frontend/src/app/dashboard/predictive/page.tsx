"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle, Loader2, TrendingUp, Activity, BarChart3,
  Search, Database,
} from "lucide-react";
import { useQuery, useQueries } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface WorkflowFailurePrediction {
  workflow_id: string;
  workflow_type: string;
  probability: number;
  risk_factors: string[];
  confidence_interval?: { lower: number; upper: number };
}

interface QueueSaturationForecast {
  queue_name: string;
  current_depth: number;
  predicted_depth: number;
  confidence: number;
  saturation_probability: number;
}

interface InfrastructureBottleneck {
  component: string;
  probability: number;
  impact: string;
  risk_factors?: string[];
}

interface WeeklyProjection {
  week: string;
  predicted_links: number;
  confidence_lower: number;
  confidence_upper: number;
}

interface CampaignForecast {
  campaign_id: string;
  weekly_projections: WeeklyProjection[];
}

interface BacklinkAcquisitionForecast {
  probability: number;
  confidence: number;
  estimated_links: number;
}

const WORKFLOW_IDS = [
  "OnboardingWorkflow",
  "KeywordResearchWorkflow",
  "BacklinkCampaignWorkflow",
  "CitationSubmissionWorkflow",
  "ReportGenerationWorkflow",
];

const QUEUE_NAMES = [
  "backlink-outreach",
  "keyword-research",
  "citation-submission",
  "report-generation",
];

const CAMPAIGN_IDS = ["campaign-001", "campaign-002", "campaign-003"];

const PROSPECT_DOMAINS = ["example.com", "competitor-site.com", "industry-blog.com"];

const PROB_BAR = (p: number) =>
  p >= 0.7 ? "bg-emerald-500" : p >= 0.4 ? "bg-amber-500" : "bg-red-500";

const PROB_TEXT = (p: number) =>
  p >= 0.7 ? "text-emerald-400" : p >= 0.4 ? "text-amber-400" : "text-red-400";

const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.4 },
};

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

function ProbabilityBar({ value, label }: { value: number; label?: string }) {
  return (
    <div>
      <div className="flex justify-between text-[10px] font-mono mb-1">
        <span className="text-slate-500">{label || "Probability"}</span>
        <span className={PROB_TEXT(value)}>{Math.round(value * 100)}%</span>
      </div>
      <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          className={`h-full rounded-full ${PROB_BAR(value)}`}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );
}

function DualBar({ current, predicted, labelCurrent, labelPredicted }: {
  current: number; predicted: number; labelCurrent?: string; labelPredicted?: string;
}) {
  const maxVal = Math.max(current, predicted, 1);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[10px] font-mono">
        <span className="text-slate-500">{labelCurrent || "Current"}: {current}</span>
        <span className="text-amber-400">{labelPredicted || "Predicted"}: {predicted}</span>
      </div>
      <div className="w-full h-4 bg-surface-darker rounded-full overflow-hidden flex">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(current / maxVal) * 100}%` }}
          className="h-full bg-slate-500 rounded-l-full"
          transition={{ duration: 0.5 }}
        />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(predicted / maxVal) * 100}%` }}
          className="h-full bg-amber-500 rounded-r-full"
          transition={{ duration: 0.5, delay: 0.2 }}
        />
      </div>
    </div>
  );
}

export default function PredictivePage() {
  const wfFailureResults = useQueries({
    queries: WORKFLOW_IDS.map(wfId => ({
      queryKey: ["wf-failure", wfId],
      queryFn: () => fetchApi<WorkflowFailurePrediction>("/predictive/workflow-failure", {
        method: "POST",
        body: JSON.stringify({ workflow_id: wfId }),
      }),
      refetchInterval: 15000,
    })),
  });

  const queueResults = useQueries({
    queries: QUEUE_NAMES.map(qn => ({
      queryKey: ["queue-saturation", qn],
      queryFn: () => fetchApi<QueueSaturationForecast>(`/predictive/queue-saturation?queue_name=${qn}&lookahead_minutes=30`),
      refetchInterval: 15000,
    })),
  });

  const { data: bottlenecks = [], isLoading: loadingBottlenecks } = useQuery<InfrastructureBottleneck[]>({
    queryKey: ["infra-bottlenecks"],
    queryFn: () => fetchApi("/predictive/infrastructure-bottlenecks?lookahead_hours=2"),
    refetchInterval: 15000,
  });

  const campaignResults = useQueries({
    queries: CAMPAIGN_IDS.map(cid => ({
      queryKey: ["campaign-forecast", cid],
      queryFn: () => fetchApi<CampaignForecast>("/predictive/campaign-forecast", {
        method: "POST",
        body: JSON.stringify({ campaign_id: cid }),
      }),
      refetchInterval: 15000,
    })),
  });

  const backlinkResults = useQueries({
    queries: PROSPECT_DOMAINS.map(domain => ({
      queryKey: ["backlink-acquisition", domain],
      queryFn: () => fetchApi<BacklinkAcquisitionForecast>("/predictive/backlink-acquisition", {
        method: "POST",
        body: JSON.stringify({ tenant_id: MOCK_TENANT_ID, prospect_domain: domain }),
      }),
      refetchInterval: 15000,
    })),
  });

  return (
    <div className="space-y-6">
      <motion.div className="flex items-center justify-between" {...fadeIn}>
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">PREDICTIVE</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Predictive Intelligence Dashboard</p>
        </div>
        <div className="px-3 py-1.5 rounded-md bg-platform-500/10 border border-platform-500/30 text-xs font-mono text-platform-400 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          FORECAST ACTIVE
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div className="glass-panel p-6" {...slideUp}>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">WORKFLOW_FAILURE</h3>
          </div>
          <div className="space-y-3 max-h-[400px] overflow-auto custom-scrollbar">
            {wfFailureResults.every(r => r.isLoading) ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : (
              wfFailureResults.map((result, i) => {
                const pred = result.data;
                if (!pred) return null;
                return (
                  <motion.div
                    key={pred.workflow_id || i}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono text-slate-300">{pred.workflow_type || pred.workflow_id}</span>
                      <span className={PROB_TEXT(pred.probability)}>{Math.round(pred.probability * 100)}%</span>
                    </div>
                    <ProbabilityBar value={pred.probability} />
                    {pred.risk_factors && pred.risk_factors.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {pred.risk_factors.map((rf, j) => (
                          <span key={j} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-red-500/10 text-red-400/80 border border-red-500/10">
                            {rf}
                          </span>
                        ))}
                      </div>
                    )}
                    {pred.confidence_interval && (
                      <div className="mt-1 text-[9px] font-mono text-slate-600">
                        CI: {Math.round(pred.confidence_interval.lower * 100)}%–{Math.round(pred.confidence_interval.upper * 100)}%
                      </div>
                    )}
                  </motion.div>
                );
              })
            )}
          </div>
        </motion.div>

        <motion.div className="glass-panel p-6" {...slideUp} transition={{ delay: 0.1 }}>
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">QUEUE_SATURATION</h3>
          </div>
          <div className="space-y-4 max-h-[400px] overflow-auto custom-scrollbar">
            {queueResults.every(r => r.isLoading) ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : (
              queueResults.map((result, i) => {
                const q = result.data;
                if (!q) return null;
                return (
                  <motion.div
                    key={q.queue_name || i}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <p className="text-xs font-mono text-slate-300 uppercase mb-2">{q.queue_name?.replace(/_/g, " ") || QUEUE_NAMES[i]}</p>
                    <DualBar
                      current={q.current_depth}
                      predicted={q.predicted_depth}
                      labelCurrent="Current"
                      labelPredicted="Predicted"
                    />
                    <div className="mt-2 flex items-center gap-3 text-[10px] font-mono text-slate-600">
                      <span>Saturation: {Math.round(q.saturation_probability * 100)}%</span>
                      <span>Confidence: {Math.round(q.confidence * 100)}%</span>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div className="glass-panel p-6" {...slideUp} transition={{ delay: 0.2 }}>
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-5 h-5 text-orange-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">INFRA_BOTTLENECKS</h3>
          </div>
          {loadingBottlenecks ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : bottlenecks.length === 0 ? (
            <div className="text-xs font-mono text-slate-500 py-10 text-center">No bottlenecks predicted</div>
          ) : (
            <div className="space-y-3 max-h-[350px] overflow-auto custom-scrollbar">
              {bottlenecks.map((b, i) => (
                <motion.div
                  key={b.component || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-300 uppercase">{b.component}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${b.probability >= 0.7 ? "bg-red-500/10 text-red-400 border-red-500/20" : b.probability >= 0.4 ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"}`}>
                      {b.impact || "—"}
                    </span>
                  </div>
                  <ProbabilityBar value={b.probability} />
                  {b.risk_factors && b.risk_factors.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {b.risk_factors.map((rf, j) => (
                        <span key={j} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-500/10 text-amber-400/80 border border-amber-500/10">
                          {rf}
                        </span>
                      ))}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        <motion.div className="glass-panel p-6" {...slideUp} transition={{ delay: 0.3 }}>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-indigo-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">CAMPAIGN_FORECAST</h3>
          </div>
          <div className="space-y-4 max-h-[400px] overflow-auto custom-scrollbar">
            {campaignResults.every(r => r.isLoading) ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : (
              campaignResults.map((result, i) => {
                const fc = result.data;
                if (!fc) return null;
                return (
                  <motion.div
                    key={fc.campaign_id || i}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                  >
                    <p className="text-xs font-mono text-slate-300 mb-2">{fc.campaign_id || CAMPAIGN_IDS[i]}</p>
                    {fc.weekly_projections && fc.weekly_projections.length > 0 ? (
                      <div className="space-y-2">
                        <div className="flex text-[9px] font-mono text-slate-600 px-1">
                          <span className="w-20">Week</span>
                          <span className="w-16 text-right">Predicted</span>
                          <span className="w-20 text-right">CI Range</span>
                        </div>
                        {fc.weekly_projections.map((wp, j) => (
                          <div key={j} className="flex items-center text-[10px] font-mono text-slate-300 px-1">
                            <span className="w-20">{wp.week}</span>
                            <span className="w-16 text-right text-platform-400">{wp.predicted_links}</span>
                            <span className="w-20 text-right text-slate-600">
                              [{wp.confidence_lower}–{wp.confidence_upper}]
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[10px] font-mono text-slate-500">No weekly projections</p>
                    )}
                  </motion.div>
                );
              })
            )}
          </div>
        </motion.div>
      </div>

      <motion.div className="glass-panel p-6" {...slideUp} transition={{ delay: 0.4 }}>
        <div className="flex items-center gap-2 mb-4">
          <Search className="w-5 h-5 text-platform-500" />
          <h3 className="text-lg font-medium text-slate-200 font-mono">BACKLINK_FORECAST</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {backlinkResults.every(r => r.isLoading) ? (
            <div className="col-span-full flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : (
            backlinkResults.map((result, i) => {
              const bf = result.data;
              if (!bf) return null;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <p className="text-xs font-mono text-slate-300 mb-3">{PROSPECT_DOMAINS[i]}</p>
                  <ProbabilityBar value={bf.probability} label="Acquisition Probability" />
                  <div className="mt-3 grid grid-cols-2 gap-2 text-center">
                    <div className="p-2 rounded bg-surface-darker border border-surface-border">
                      <p className="text-[9px] font-mono text-slate-500">Confidence</p>
                      <p className="text-sm font-mono text-slate-200">{Math.round(bf.confidence * 100)}%</p>
                    </div>
                    <div className="p-2 rounded bg-surface-darker border border-surface-border">
                      <p className="text-[9px] font-mono text-slate-500">Est. Links</p>
                      <p className="text-sm font-mono text-slate-200">{bf.estimated_links}</p>
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>
      </motion.div>
    </div>
  );
}
