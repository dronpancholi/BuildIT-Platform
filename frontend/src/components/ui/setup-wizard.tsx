"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Check, ArrowRight, ArrowLeft, Building2, GitBranch, Target, Sparkles, Globe } from "lucide-react";
import { useCommandCenter } from "@/hooks/use-command-center";

interface StepProps {
  step: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  fields: { label: string; name: string; placeholder: string; required?: boolean; type?: string; options?: { value: string; label: string }[] }[];
}

const STEPS: StepProps[] = [
  {
    step: 1,
    title: "Add Your Client",
    description: "Create a client profile to start building their SEO presence. This is the foundation for all campaigns and intelligence.",
    icon: <Building2 className="w-6 h-6" />,
    fields: [
      { label: "Client Name", name: "client_name", placeholder: "e.g. Acme Corp", required: true },
      { label: "Website Domain", name: "domain", placeholder: "e.g. acme.com", required: true },
      { label: "Industry", name: "niche", placeholder: "e.g. B2B SaaS", required: true, type: "select",
        options: [
          { value: "B2B SaaS", label: "B2B SaaS" },
          { value: "E-commerce", label: "E-commerce" },
          { value: "Healthcare", label: "Healthcare" },
          { value: "Legal", label: "Legal" },
          { value: "Local Services", label: "Local Services" },
          { value: "Technology", label: "Technology" },
          { value: "Finance", label: "Finance" },
        ]
      },
    ],
  },
  {
    step: 2,
    title: "Set Your Goal",
    description: "What do you want to achieve? Choose the primary objective for this client.",
    icon: <Target className="w-6 h-6" />,
    fields: [
      {
        label: "Primary Goal", name: "goal", required: true, placeholder: "", type: "select",
        options: [
          { value: "seo_growth", label: "SEO Growth — Improve organic rankings" },
          { value: "backlinks", label: "Backlinks — Build high-quality links" },
          { value: "local_seo", label: "Local SEO — Dominate local search" },
          { value: "outreach", label: "Outreach — Scale email campaigns" },
        ],
      },
    ],
  },
  {
    step: 3,
    title: "Create Campaign",
    description: "Launch your first campaign. BuildIT will discover opportunities and track progress automatically.",
    icon: <GitBranch className="w-6 h-6" />,
    fields: [
      { label: "Campaign Name", name: "campaign_name", placeholder: "e.g. Q3 Backlink Growth", required: true },
      {
        label: "Campaign Type", name: "campaign_type", required: true, placeholder: "", type: "select",
        options: [
          { value: "guest_post", label: "Guest Posting" },
          { value: "broken_link", label: "Broken Link Building" },
          { value: "resource_page", label: "Resource Page Outreach" },
        ],
      },
    ],
  },
  {
    step: 4,
    title: "Discover Keywords",
    description: "Start with a seed keyword. BuildIT will research related terms, analyze competition, and find opportunities.",
    icon: <Sparkles className="w-6 h-6" />,
    fields: [
      { label: "Seed Keyword", name: "seed_keyword", placeholder: "e.g. enterprise seo", required: true },
      { label: "Target Location", name: "geo", placeholder: "", required: true, type: "select",
        options: [
          { value: "US", label: "United States" },
          { value: "UK", label: "United Kingdom" },
          { value: "Global", label: "Global" },
        ],
      },
    ],
  },
  {
    step: 5,
    title: "Launch Analysis",
    description: "BuildIT will now analyze your client's website, discover keyword opportunities, find backlink prospects, and prepare your outreach campaigns.",
    icon: <Globe className="w-6 h-6" />,
    fields: [],
  },
];

export function SetupWizard({ onClose }: { onClose: () => void }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isLaunching, setIsLaunching] = useState(false);
  const [launched, setLaunched] = useState(false);
  const { openCommand } = useCommandCenter();

  const step = STEPS[currentStep];
  const isLast = currentStep === STEPS.length - 1;
  const isFirst = currentStep === 0;

  const updateField = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const canProceed = () => {
    if (isLast) return true;
    return step.fields.every((f) => !f.required || formData[f.name]);
  };

  const handleNext = () => {
    if (isLast) {
      setIsLaunching(true);
      setTimeout(() => {
        setLaunched(true);
        setIsLaunching(false);
      }, 1500);
    } else {
      setCurrentStep((s) => s + 1);
    }
  };

  const handleFinish = () => {
    openCommand("add_client");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <AnimatePresence mode="wait">
        {launched ? (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="relative bg-surface-card border border-surface-border rounded-2xl shadow-2xl p-12 max-w-md w-full mx-4 text-center"
          >
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-emerald-400" />
            </div>
            <h2 className="text-xl font-bold text-slate-100 mb-2">Ready to Begin</h2>
            <p className="text-sm text-slate-400 mb-6">You now know what&apos;s needed. Let&apos;s add your first client and put the plan into action.</p>
            <button
              onClick={handleFinish}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-bold font-mono transition-all"
            >
              ADD YOUR FIRST CLIENT
            </button>
          </motion.div>
        ) : isLaunching ? (
          <motion.div
            key="launching"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="relative bg-surface-card border border-surface-border rounded-2xl shadow-2xl p-12 max-w-md w-full mx-4 text-center"
          >
            <div className="w-16 h-16 rounded-full bg-platform-500/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-4">
              <div className="w-8 h-8 border-2 border-platform-400 border-t-transparent rounded-full animate-spin" />
            </div>
            <h2 className="text-xl font-bold text-slate-100 mb-2">Launching Analysis</h2>
            <p className="text-sm text-slate-400">Setting up your workspace and starting initial scans...</p>
          </motion.div>
        ) : (
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            className="relative bg-surface-card border border-surface-border rounded-2xl shadow-2xl max-w-lg w-full mx-4"
          >
            <div className="flex items-center justify-between p-6 border-b border-surface-border">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400">
                  {step.icon}
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-100">{step.title}</h2>
                  <p className="text-xs text-slate-500 font-mono">Step {step.step} of {STEPS.length}</p>
                </div>
              </div>
              <button onClick={onClose} className="p-2 hover:bg-surface-border rounded-lg text-slate-400 transition-colors">
                <X size={18} />
              </button>
            </div>

            <div className="p-6">
              <div className="flex gap-1 mb-6">
                {STEPS.map((_, i) => (
                  <div
                    key={i}
                    className={`flex-1 h-1 rounded-full transition-colors ${
                      i <= currentStep ? "bg-platform-500" : "bg-surface-border"
                    }`}
                  />
                ))}
              </div>

              <p className="text-sm text-slate-400 mb-6">{step.description}</p>

              <div className="space-y-4">
                {step.fields.map((field) => (
                  <div key={field.name} className="space-y-1.5">
                    <label className="text-xs font-mono text-slate-500 uppercase">{field.label}</label>
                    {field.type === "select" && field.options ? (
                      <select
                        name={field.name}
                        value={formData[field.name] || ""}
                        onChange={(e) => updateField(field.name, e.target.value)}
                        className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                      >
                        <option value="">Select...</option>
                        {field.options.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        name={field.name}
                        value={formData[field.name] || ""}
                        onChange={(e) => updateField(field.name, e.target.value)}
                        placeholder={field.placeholder}
                        className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between p-6 border-t border-surface-border">
              <button
                onClick={() => setCurrentStep((s) => s - 1)}
                disabled={isFirst}
                className="flex items-center gap-1.5 px-4 py-2 text-sm text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ArrowLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleNext}
                disabled={!canProceed()}
                className="flex items-center gap-1.5 px-6 py-2.5 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-sm font-bold font-mono disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {isLast ? "LAUNCH" : "Continue"} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
