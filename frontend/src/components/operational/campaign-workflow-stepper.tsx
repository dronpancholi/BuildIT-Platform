"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2, Loader2, AlertCircle, Radio, ArrowRight,
} from "lucide-react";

export interface WorkflowMilestone {
  phase: string;
  label: string;
  status: "pending" | "processing" | "completed" | "failed";
  timestamp?: string;
}

const WORKFLOW_STEPS: WorkflowMilestone[] = [
  { phase: "discovery", label: "Discovery", status: "pending" },
  { phase: "scoring", label: "Filtering & Scoring", status: "pending" },
  { phase: "profiling", label: "CMS Profiling", status: "pending" },
  { phase: "authority", label: "Authority Vetting", status: "pending" },
  { phase: "enrichment", label: "Contact Enrichment", status: "pending" },
  { phase: "outreach_generation", label: "Email Generation", status: "pending" },
  { phase: "compliance", label: "Compliance Scan", status: "pending" },
  { phase: "complete", label: "Complete", status: "pending" },
];

export function CampaignWorkflowStepper({ activePhase }: { activePhase?: string }) {
  const currentPhase = activePhase || "discovery";
  const currentIdx = WORKFLOW_STEPS.findIndex((s) => s.phase === currentPhase);

  const steps: WorkflowMilestone[] = WORKFLOW_STEPS.map((step, i) => ({
    ...step,
    status: i < currentIdx ? "completed" : i === currentIdx ? "processing" : "pending",
  }));

  return (
    <div className="glass-panel p-5">
      <h3 className="text-sm font-mono text-slate-400 mb-4 uppercase tracking-wider flex items-center gap-2">
        <Radio className="w-4 h-4 text-platform-500" />
        WORKFLOW_PROGRESS
      </h3>
      <div className="space-y-0">
        {steps.map((step, i) => (
          <div key={step.phase} className="flex items-start gap-3">
            <div className="flex flex-col items-center">
              <motion.div
                initial={false}
                animate={step.status === "processing" ? { scale: [1, 1.2, 1] } : {}}
                transition={{ duration: 1.5, repeat: Infinity }}
                className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                  step.status === "completed"
                    ? "bg-emerald-500/20 border-emerald-500"
                    : step.status === "processing"
                      ? "bg-platform-500/20 border-platform-500"
                      : step.status === "failed"
                        ? "bg-red-500/20 border-red-500"
                        : "bg-surface-darker border-slate-600"
                }`}
              >
                {step.status === "completed" ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : step.status === "processing" ? (
                  <Loader2 className="w-3.5 h-3.5 text-platform-400 animate-spin" />
                ) : step.status === "failed" ? (
                  <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                ) : (
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                )}
              </motion.div>
              {i < steps.length - 1 && (
                <div className={`w-0.5 h-8 ${
                  step.status === "completed" ? "bg-emerald-500/50" : "bg-surface-border"
                }`} />
              )}
            </div>
            <div className={`pb-6 ${i === steps.length - 1 ? "pb-0" : ""}`}>
              <p className={`text-xs font-mono font-medium ${
                step.status === "completed" ? "text-emerald-400" :
                step.status === "processing" ? "text-platform-400" :
                step.status === "failed" ? "text-red-400" :
                "text-slate-500"
              }`}>
                {step.label}
              </p>
              {step.status === "processing" && (
                <p className="text-[9px] font-mono text-slate-600 mt-0.5">In progress...</p>
              )}
              {step.status === "completed" && (
                <p className="text-[9px] font-mono text-slate-600 mt-0.5">Complete</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
