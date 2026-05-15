"use client";

import { motion } from "framer-motion";
import { Link2, Sparkles, Activity, Users, ArrowUpRight, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden flex flex-col items-center justify-center">
      {/* Background Gradients */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute -top-1/4 -left-1/4 w-1/2 h-1/2 bg-platform-900/40 blur-[120px] rounded-full" />
        <div className="absolute top-3/4 -right-1/4 w-1/2 h-1/2 bg-indigo-900/20 blur-[120px] rounded-full" />
      </div>

      <div className="relative z-10 w-full max-w-6xl mx-auto px-6 pt-20 pb-32">
        {/* Hero Section */}
        <div className="text-center space-y-8 max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-platform-900/50 border border-platform-500/20 text-platform-300 text-sm font-medium mb-4"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Enterprise SEO AI Platform v2.0</span>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-5xl md:text-7xl font-bold tracking-tight text-white leading-[1.1]"
          >
            AI proposes. <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-platform-300 to-emerald-300">
              Deterministic systems execute.
            </span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg md:text-xl text-slate-400 font-light"
          >
            A high-reliability orchestration platform for multi-tenant SEO operations, 
            backlink campaigns, and workflow automation.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-8"
          >
            <Link 
              href="/dashboard"
              className="flex items-center gap-2 px-8 py-4 rounded-lg bg-platform-600 hover:bg-platform-500 text-white font-medium transition-all shadow-lg shadow-platform-900/50 glow-effect w-full sm:w-auto"
            >
              Enter Operations Console
              <ArrowUpRight className="w-4 h-4" />
            </Link>
            <Link 
              href="/dashboard/approvals"
              className="flex items-center gap-2 px-8 py-4 rounded-lg bg-surface-border hover:bg-surface-border/80 text-white font-medium transition-all w-full sm:w-auto"
            >
              View Approval Queue
            </Link>
          </motion.div>
        </div>

        {/* Feature Grid */}
        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.5 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-32"
        >
          <FeatureCard 
            icon={<Sparkles className="w-6 h-6 text-platform-400" />}
            title="AI Governance Pipeline"
            description="PII masking, prompt injection defense, and output schema validation for every single LLM inference."
          />
          <FeatureCard 
            icon={<Activity className="w-6 h-6 text-platform-400" />}
            title="Temporal Orchestration"
            description="Idempotent, retryable workflow executions with multi-signal prospect scoring and automated outreach."
          />
          <FeatureCard 
            icon={<Users className="w-6 h-6 text-platform-400" />}
            title="Human-in-the-Loop"
            description="Strict approval gates with SLA escalations for campaign launches and outreach templates."
          />
        </motion.div>
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="glass-panel p-6 flex flex-col gap-4 glow-effect group cursor-default">
      <div className="w-12 h-12 rounded-lg bg-platform-900/30 flex items-center justify-center border border-platform-500/20 group-hover:bg-platform-900/50 transition-colors">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-slate-200">{title}</h3>
      <p className="text-slate-400 leading-relaxed text-sm">
        {description}
      </p>
    </div>
  );
}
