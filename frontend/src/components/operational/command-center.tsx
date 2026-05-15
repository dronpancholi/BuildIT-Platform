"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  X, Loader2, CheckCircle2, AlertCircle, RotateCcw, Clock,
  Terminal, History,
} from "lucide-react";
import { useCommandCenter, type CommandType } from "@/hooks/use-command-center";
import { useState, useEffect, useCallback } from "react";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useQuery, useQueryClient } from "@tanstack/react-query";

interface CommandHistoryEntry {
  id: string;
  command: CommandType;
  status: "success" | "error";
  timestamp: number;
  message: string;
  workflowRunId?: string;
}

const COMMAND_DESCRIPTIONS: Record<string, string> = {
  add_client: "Register a new client with primary domain and contact details",
  create_campaign: "Launch a new backlink acquisition campaign for a client",
  keyword_discovery: "Research seed keywords with AI-powered cluster analysis",
  generate_report: "Generate executive performance or technical SEO report",
  citation_submission: "Submit business NAP data to local citation platforms",
};

export function CommandCenter() {
  const { activeCommand, isOpen, closeCommand, context } = useCommandCenter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [workflowRunId, setWorkflowRunId] = useState<string | null>(null);
  const [commandHistory, setCommandHistory] = useState<CommandHistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const queryClient = useQueryClient();

  const commandDescription = activeCommand ? COMMAND_DESCRIPTIONS[activeCommand] || "" : "";

  const executeCommand = useCallback(async (formData: FormData) => {
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);
    setWorkflowRunId(null);

    const data = Object.fromEntries(formData.entries());

    try {
      let endpoint = "";
      let payload: Record<string, unknown> = Object.fromEntries(formData.entries());
      let expectedWorkflowId = "";

      switch (activeCommand) {
        case "add_client":
          endpoint = "/clients";
          payload = { ...data, tenant_id: MOCK_TENANT_ID };
          break;
        case "create_campaign":
          endpoint = "/campaigns";
          payload = {
            ...data,
            tenant_id: MOCK_TENANT_ID,
            target_link_count: parseInt(data.target_link_count as string) || 10,
          };
          break;
        case "generate_report":
          endpoint = "/reports";
          break;
        case "citation_submission":
          endpoint = "/citations";
          break;
        case "keyword_discovery":
          endpoint = "/keywords/research";
          const rawKeywords = data.seed_keywords as string || "";
          payload = {
            ...data,
            tenant_id: MOCK_TENANT_ID,
            seed_keywords: rawKeywords ? rawKeywords.split(",").map((s: string) => s.trim()) : [],
          };
          break;
      }

      const response = await fetchApi<any>(endpoint, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const wfRunId = response?.workflow_run_id || response?.id || null;
      setWorkflowRunId(wfRunId);
      setSuccess("Operation executed successfully. Workflow initialized.");

      const entry: CommandHistoryEntry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        command: activeCommand!,
        status: "success",
        timestamp: Date.now(),
        message: `Executed ${activeCommand!.replace(/_/g, " ")}`,
        workflowRunId: wfRunId || undefined,
      };
      setCommandHistory((prev) => [entry, ...prev].slice(0, 50));

      queryClient.invalidateQueries();

      setTimeout(() => {
        closeCommand();
        setSuccess(null);
        setWorkflowRunId(null);
      }, 2500);
    } catch (err: any) {
      setError(err.message || "Failed to execute operation.");

      const entry: CommandHistoryEntry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        command: activeCommand!,
        status: "error",
        timestamp: Date.now(),
        message: err.message || "Failed to execute operation",
      };
      setCommandHistory((prev) => [entry, ...prev].slice(0, 50));
    } finally {
      setIsSubmitting(false);
    }
  }, [activeCommand, closeCommand, queryClient]);

  const handleRetry = () => {
    setError(null);
    setSuccess(null);
    setWorkflowRunId(null);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    await executeCommand(formData);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end overflow-hidden">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={closeCommand}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
      />

      <motion.div
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 200 }}
        className="relative w-full max-w-lg h-full bg-surface-card border-l border-surface-border shadow-2xl flex flex-col"
      >
        <div className="p-6 border-b border-surface-border flex items-center justify-between bg-surface-darker/50">
          <div>
            <h2 className="text-xl font-bold text-slate-100 font-mono uppercase tracking-tight">
              {activeCommand?.replace("_", " ")}
            </h2>
            <p className="text-xs text-slate-500 font-mono mt-1">OPERATIONAL_COMMAND_GATEWAY</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className={`p-2 rounded-lg transition-colors ${showHistory ? "bg-platform-500/10 text-platform-400" : "text-slate-500 hover:text-slate-300 hover:bg-surface-border"}`}
              title="Command History"
            >
              <History size={18} />
            </button>
            <button onClick={closeCommand} className="p-2 hover:bg-surface-border rounded-lg text-slate-400 transition-colors">
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {showHistory ? (
            <div className="space-y-2">
              <h3 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">Command History</h3>
              {commandHistory.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-8">No commands executed yet</p>
              ) : (
                commandHistory.map((entry) => (
                  <div
                    key={entry.id}
                    className={`p-3 rounded-md border text-sm ${
                      entry.status === "success"
                        ? "bg-emerald-500/5 border-emerald-500/20"
                        : "bg-red-500/5 border-red-500/20"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {entry.status === "success" ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-400" />
                      )}
                      <span className="text-xs font-mono text-slate-300 capitalize">
                        {entry.command?.replace(/_/g, " ")}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 ml-auto">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 ml-6">{entry.message}</p>
                    {entry.workflowRunId && (
                      <p className="text-[10px] font-mono text-platform-400 ml-6 mt-1">
                        WORKFLOW: {entry.workflowRunId.slice(0, 12)}...
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          ) : success ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <CheckCircle2 size={48} className="text-emerald-500 mb-4" />
              <h3 className="text-lg font-medium text-slate-200">Execution Confirmed</h3>
              <p className="text-sm text-slate-400 mt-2">{success}</p>
              {workflowRunId && (
                <div className="mt-4 p-3 rounded-md bg-platform-500/10 border border-platform-500/20">
                  <p className="text-xs font-mono text-platform-400 uppercase tracking-wider mb-1">Workflow Run ID</p>
                  <code className="text-sm font-mono text-slate-200">{workflowRunId}</code>
                </div>
              )}
            </div>
          ) : (
            <>
              {commandDescription && (
                <div className="mb-6 p-3 rounded-md bg-surface-darker border border-surface-border flex items-start gap-3">
                  <Terminal className="w-4 h-4 text-platform-400 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-slate-400 leading-relaxed">{commandDescription}</p>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                {error && (
                  <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3">
                    <AlertCircle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-red-400">{error}</p>
                      <button
                        type="button"
                        onClick={handleRetry}
                        className="mt-2 text-xs text-red-400/70 hover:text-red-300 flex items-center gap-1 transition-colors"
                      >
                        <RotateCcw className="w-3 h-3" /> Retry
                      </button>
                    </div>
                  </div>
                )}

                {activeCommand === "add_client" && <AddClientForm />}
                {activeCommand === "create_campaign" && <CreateCampaignForm />}
                {activeCommand === "keyword_discovery" && <KeywordResearchForm />}
                {activeCommand === "generate_report" && <GenerateReportForm />}
                {activeCommand === "citation_submission" && <CitationSubmissionForm />}

                {isSubmitting && (
                  <div className="p-4 bg-platform-500/10 border border-platform-500/20 rounded-lg flex items-center gap-3">
                    <Loader2 size={18} className="animate-spin text-platform-400" />
                    <div className="flex-1">
                      <p className="text-xs font-mono text-platform-400">Executing command...</p>
                      <div className="mt-2 w-full h-1 bg-surface-darker rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-platform-500 rounded-full"
                          initial={{ width: "0%" }}
                          animate={{ width: "100%" }}
                          transition={{ duration: 2, repeat: Infinity }}
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div className="pt-6 border-t border-surface-border flex gap-3">
                  <button
                    type="button"
                    onClick={closeCommand}
                    className="flex-1 px-4 py-2 bg-surface-darker border border-surface-border text-slate-300 rounded-lg text-sm font-medium hover:bg-surface-border transition-colors"
                  >
                    CANCEL
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex-1 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-sm font-bold font-mono transition-all shadow-lg shadow-platform-600/20 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? <Loader2 size={18} className="animate-spin" /> : "EXECUTE_COMMAND"}
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}

function AddClientForm() {
  return (
    <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
      <div className="text-[10px] font-mono text-platform-400 uppercase tracking-wider mb-3">Business Identity</div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-[10px] font-mono text-slate-500 uppercase">Client Name</label>
          <input name="name" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500" placeholder="Acme Corp" />
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] font-mono text-slate-500 uppercase">Website</label>
          <input name="domain" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500" placeholder="acme.com" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-[10px] font-mono text-slate-500 uppercase">Industry / Niche</label>
          <select name="niche" className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500">
            <option value="">Select niche...</option>
            <option value="B2B SaaS">B2B SaaS</option>
            <option value="E-commerce">E-commerce</option>
            <option value="Healthcare">Healthcare</option>
            <option value="Legal">Legal</option>
            <option value="Real Estate">Real Estate</option>
            <option value="Local Services">Local Services</option>
            <option value="Content Publishing">Content Publishing</option>
            <option value="Agency">Agency</option>
            <option value="Education">Education</option>
            <option value="Finance">Finance</option>
            <option value="Technology">Technology</option>
            <option value="Hospitality">Hospitality</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] font-mono text-slate-500 uppercase">Business Type</label>
          <select name="business_type" className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500">
            <option value="">Select type...</option>
            <option value="B2B">B2B</option>
            <option value="B2C">B2C</option>
            <option value="B2B + B2C">B2B + B2C</option>
            <option value="Marketplace">Marketplace</option>
            <option value="Agency">Agency</option>
          </select>
        </div>
      </div>

      <div className="text-[10px] font-mono text-platform-400 uppercase tracking-wider mt-4 mb-3">Geography & Local SEO</div>
      <div className="space-y-1.5">
        <label className="text-[10px] font-mono text-slate-500 uppercase">Target Cities / Regions</label>
        <input name="geo_focus" className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500" placeholder="e.g. San Francisco, California (comma-separated)" />
      </div>

      <div className="text-[10px] font-mono text-platform-400 uppercase tracking-wider mt-4 mb-3">Business Goals</div>
      <div className="grid grid-cols-2 gap-2">
        {["backlinks", "rankings", "local SEO", "traffic", "brand visibility", "maps ranking", "authority growth", "lead generation"].map((g) => (
          <label key={g} className="flex items-center gap-2 p-2 rounded bg-surface-darker/50 border border-surface-border/50 text-xs text-slate-300 cursor-pointer hover:border-platform-500/30">
            <input type="checkbox" name="goals" value={g} className="accent-platform-500" />
            {g}
          </label>
        ))}
      </div>

      <div className="text-[10px] font-mono text-platform-400 uppercase tracking-wider mt-4 mb-3">Competitors</div>
      <div className="space-y-1.5">
        <label className="text-[10px] font-mono text-slate-500 uppercase">Competitor Domains (comma-separated)</label>
        <input name="competitors" className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500" placeholder="competitor1.com, competitor2.com" />
      </div>
    </div>
  );
}

function CreateCampaignForm() {
  const { data: clients = [] } = useQuery<any[]>({
    queryKey: ["clients"],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
  });

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Target Client</label>
        <select name="client_id" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500 text-sm">
          <option value="">Select a client...</option>
          {clients.map((c: any) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Campaign Name</label>
        <input name="name" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500" placeholder="Q3 Backlink Expansion" />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Campaign Type</label>
        <select name="campaign_type" className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500">
          <option value="guest_post">Guest Posting</option>
          <option value="broken_link">Broken Link Building</option>
          <option value="resource_page">Resource Page Outreach</option>
        </select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Target Link Count</label>
        <input name="target_link_count" type="number" defaultValue="10" className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500" />
      </div>
    </div>
  );
}

function KeywordResearchForm() {
  const { data: clients = [] } = useQuery<any[]>({
    queryKey: ["clients"],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
  });

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Target Client</label>
        <select name="client_id" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500 text-sm">
          <option value="">Select a client...</option>
          {clients.map((c: any) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Seed Keyword</label>
        <input name="seed_keywords" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500" placeholder="e.g. enterprise seo platform" />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Target Domain (Context)</label>
        <input name="domain" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500" placeholder="acme.com" />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Geo Target</label>
        <select name="geo_target" className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500">
          <option value="US">United States</option>
          <option value="UK">United Kingdom</option>
          <option value="Global">Global</option>
        </select>
      </div>
    </div>
  );
}

function GenerateReportForm() {
  const { data: clients = [] } = useQuery<any[]>({
    queryKey: ["clients"],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
  });

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Target Client</label>
        <select name="client_id" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500 text-sm">
          <option value="">Select a client...</option>
          {clients.map((c: any) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Report Type</label>
        <select name="report_type" className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500">
          <option value="performance">Executive Performance</option>
          <option value="technical">Technical SEO Audit</option>
          <option value="backlink">Link Acquisition Report</option>
        </select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Date Range</label>
        <select name="date_range" className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500">
          <option value="last_7_days">Last 7 Days</option>
          <option value="last_30_days">Last 30 Days</option>
          <option value="last_90_days">Last 90 Days</option>
        </select>
      </div>
    </div>
  );
}

function CitationSubmissionForm() {
  const { data: clients = [] } = useQuery<any[]>({
    queryKey: ["clients"],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
  });

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Target Client</label>
        <select name="client_id" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500 text-sm">
          <option value="">Select a client...</option>
          {clients.map((c: any) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Target Platform</label>
        <select name="platform" className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-platform-500">
          <option value="yelp">Yelp</option>
          <option value="yellowpages">YellowPages</option>
          <option value="foursquare">Foursquare</option>
        </select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-mono text-slate-500 uppercase">Business NAP</label>
        <div className="space-y-2">
          <input name="business_name" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 text-xs" placeholder="Business Name" />
          <input name="address" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 text-xs" placeholder="Full Address" />
          <input name="phone" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 text-xs" placeholder="Phone Number" />
          <input name="website" required className="w-full bg-surface-darker border border-surface-border rounded-lg px-4 py-2 text-slate-200 text-xs" placeholder="Website" />
        </div>
      </div>
    </div>
  );
}
