"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot, ChevronDown, ChevronRight, Loader2, BrainCircuit, Server,
  Activity, Search, GitBranch,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface WorkflowRecommendation {
  category: string;
  explanation: string;
  confidence: number;
  expected_impact: string;
}

interface WorkflowAssistance {
  recommendations: WorkflowRecommendation[];
}

interface CampaignAssistanceItem {
  category: string;
  action: string;
  confidence: number;
}

interface QueueAssistanceItem {
  queue_name: string;
  category: string;
  action: string;
  confidence: number;
}

interface ScrapingAssistanceItem {
  category: string;
  explanation: string;
  confidence: number;
}

interface InfrastructureAssistanceItem {
  component: string;
  category: string;
  action: string;
}

const SECTIONS = [
  { id: "workflow", label: "WORKFLOW_ASSISTANCE", icon: <GitBranch className="w-5 h-5 text-blue-500" /> },
  { id: "campaign", label: "CAMPAIGN_ASSISTANCE", icon: <Search className="w-5 h-5 text-emerald-500" /> },
  { id: "queue", label: "QUEUE_ASSISTANCE", icon: <Activity className="w-5 h-5 text-amber-500" /> },
  { id: "scraping", label: "SCRAPING_ASSISTANCE", icon: <Bot className="w-5 h-5 text-purple-500" /> },
  { id: "infrastructure", label: "INFRA_ASSISTANCE", icon: <Server className="w-5 h-5 text-cyan-500" /> },
];

const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.4 },
};

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 0.7 ? "bg-emerald-500" : value >= 0.5 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="mt-2">
      <div className="flex justify-between text-[10px] font-mono mb-1">
        <span className="text-slate-500">Confidence</span>
        <span className={value >= 0.7 ? "text-emerald-400" : value >= 0.5 ? "text-amber-400" : "text-red-400"}>
          {Math.round(value * 100)}%
        </span>
      </div>
      <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          className={`h-full rounded-full ${color}`}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );
}

function CollapsibleSection({
  id,
  label,
  icon,
  expanded,
  onToggle,
  loading,
  children,
}: {
  id: string;
  label: string;
  icon: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  loading: boolean;
  children: React.ReactNode;
}) {
  return (
    <motion.div className="glass-panel overflow-hidden" {...fadeIn}>
      <div
        className="px-6 py-4 border-b border-surface-border flex items-center gap-2 cursor-pointer hover:bg-surface-darker/30 transition-colors"
        onClick={onToggle}
      >
        {icon}
        <h3 className="text-lg font-medium text-slate-200 font-mono">{label}</h3>
        <div className="ml-auto text-slate-500">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-6 py-4">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
                </div>
              ) : (
                children
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function AssistantPage() {
  const [expandedSection, setExpandedSection] = useState<string>("workflow");

  const { data: workflowAssistance, isLoading: loadingWorkflow } = useQuery<WorkflowRecommendation[]>({
    queryKey: ["assistant-workflow"],
    queryFn: () => fetchApi(`/operational-assistant/workflow?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: campaignAssistance = [], isLoading: loadingCampaign } = useQuery<CampaignAssistanceItem[]>({
    queryKey: ["assistant-campaign"],
    queryFn: () => fetchApi(`/operational-assistant/campaign?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: queueAssistance = [], isLoading: loadingQueue } = useQuery<QueueAssistanceItem[]>({
    queryKey: ["assistant-queue"],
    queryFn: () => fetchApi("/operational-assistant/queue"),
    refetchInterval: 15000,
  });

  const { data: scrapingAssistance = [], isLoading: loadingScraping } = useQuery<ScrapingAssistanceItem[]>({
    queryKey: ["assistant-scraping"],
    queryFn: () => fetchApi("/operational-assistant/scraping"),
    refetchInterval: 15000,
  });

  const { data: infraAssistance = [], isLoading: loadingInfra } = useQuery<InfrastructureAssistanceItem[]>({
    queryKey: ["assistant-infrastructure"],
    queryFn: () => fetchApi("/operational-assistant/infrastructure"),
    refetchInterval: 15000,
  });

  const workflowRecs = workflowAssistance || [];

  return (
    <div className="space-y-6">
      <motion.div className="flex items-center justify-between" {...fadeIn}>
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">AI_ASSISTANT</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">AI Operational Assistant</p>
        </div>
        <div className="px-3 py-1.5 rounded-md bg-platform-500/10 border border-platform-500/30 text-xs font-mono text-platform-400 flex items-center gap-2">
          <BrainCircuit className="w-4 h-4" />
          AI-POWERED
        </div>
      </motion.div>

      <CollapsibleSection
        id="workflow"
        label="WORKFLOW_ASSISTANCE"
        icon={<GitBranch className="w-5 h-5 text-blue-500" />}
        expanded={expandedSection === "workflow"}
        onToggle={() => setExpandedSection(expandedSection === "workflow" ? "" : "workflow")}
        loading={loadingWorkflow}
      >
        {workflowRecs.length === 0 ? (
          <p className="text-sm font-mono text-slate-500 py-4 text-center">No workflow recommendations</p>
        ) : (
          <div className="space-y-3">
            {workflowRecs.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase">
                    {r.category}
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-300">{r.explanation}</p>
                <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-slate-600">
                  <span>Impact: {r.expected_impact}</span>
                </div>
                <ConfidenceBar value={r.confidence} />
              </motion.div>
            ))}
          </div>
        )}
      </CollapsibleSection>

      <CollapsibleSection
        id="campaign"
        label="CAMPAIGN_ASSISTANCE"
        icon={<Search className="w-5 h-5 text-emerald-500" />}
        expanded={expandedSection === "campaign"}
        onToggle={() => setExpandedSection(expandedSection === "campaign" ? "" : "campaign")}
        loading={loadingCampaign}
      >
        {campaignAssistance.length === 0 ? (
          <p className="text-sm font-mono text-slate-500 py-4 text-center">No campaign recommendations</p>
        ) : (
          <div className="space-y-2">
            {campaignAssistance.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center justify-between p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase">
                    {r.category}
                  </span>
                  <span className="text-xs font-mono text-slate-300">{r.action}</span>
                </div>
                <span className={`text-[10px] font-mono ${r.confidence >= 0.7 ? "text-emerald-400" : r.confidence >= 0.5 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(r.confidence * 100)}%
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </CollapsibleSection>

      <CollapsibleSection
        id="queue"
        label="QUEUE_ASSISTANCE"
        icon={<Activity className="w-5 h-5 text-amber-500" />}
        expanded={expandedSection === "queue"}
        onToggle={() => setExpandedSection(expandedSection === "queue" ? "" : "queue")}
        loading={loadingQueue}
      >
        {queueAssistance.length === 0 ? (
          <p className="text-sm font-mono text-slate-500 py-4 text-center">No queue recommendations</p>
        ) : (
          <div className="space-y-3">
            {queueAssistance.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono text-slate-300 uppercase">{r.queue_name?.replace(/_/g, " ")}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase">
                    {r.category}
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-400">{r.action}</p>
                <ConfidenceBar value={r.confidence} />
              </motion.div>
            ))}
          </div>
        )}
      </CollapsibleSection>

      <CollapsibleSection
        id="scraping"
        label="SCRAPING_ASSISTANCE"
        icon={<Bot className="w-5 h-5 text-purple-500" />}
        expanded={expandedSection === "scraping"}
        onToggle={() => setExpandedSection(expandedSection === "scraping" ? "" : "scraping")}
        loading={loadingScraping}
      >
        {scrapingAssistance.length === 0 ? (
          <p className="text-sm font-mono text-slate-500 py-4 text-center">No scraping recommendations</p>
        ) : (
          <div className="space-y-3">
            {scrapingAssistance.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 uppercase">
                    {r.category}
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-300">{r.explanation}</p>
                <ConfidenceBar value={r.confidence} />
              </motion.div>
            ))}
          </div>
        )}
      </CollapsibleSection>

      <CollapsibleSection
        id="infrastructure"
        label="INFRA_ASSISTANCE"
        icon={<Server className="w-5 h-5 text-cyan-500" />}
        expanded={expandedSection === "infrastructure"}
        onToggle={() => setExpandedSection(expandedSection === "infrastructure" ? "" : "infrastructure")}
        loading={loadingInfra}
      >
        {infraAssistance.length === 0 ? (
          <p className="text-sm font-mono text-slate-500 py-4 text-center">No infrastructure recommendations</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {infraAssistance.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 uppercase">
                    {r.category}
                  </span>
                  <span className="text-xs font-mono text-slate-300 uppercase">{r.component}</span>
                </div>
                <p className="text-xs font-mono text-slate-400">{r.action}</p>
              </motion.div>
            ))}
          </div>
        )}
      </CollapsibleSection>
    </div>
  );
}
