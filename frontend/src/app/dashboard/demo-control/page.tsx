"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, RefreshCw, Loader2, CheckCircle2, AlertTriangle,
  Server, Database, Radio, Bot,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface Scenario {
  name: string;
  niche: string;
  keyword_count: number;
}

interface ReadinessCheck {
  healthy: boolean;
  message: string;
}

interface ReadinessData {
  overall_healthy: boolean;
  readiness: string;
  checks: Record<string, ReadinessCheck>;
}

interface ScenarioLoadResult {
  scenario: string;
  niche: string;
  keyword_count: number;
  status: string;
}

export default function DemoControlPage() {
  const [loadingScenario, setLoadingScenario] = useState<string | null>(null);
  const [loadingReset, setLoadingReset] = useState(false);
  const [resultMessage, setResultMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const queryClient = useQueryClient();

  const { data: readiness, isLoading: loadingReadiness, refetch: refetchReadiness } = useQuery<ReadinessData>({
    queryKey: ["demo-readiness"],
    queryFn: () => fetchApi("/demo/readiness"),
    refetchInterval: 30000,
  });

  const { data: scenariosData, isLoading: loadingScenarios } = useQuery<{ scenarios: Scenario[] }>({
    queryKey: ["demo-scenarios"],
    queryFn: () => fetchApi("/demo/scenarios"),
    staleTime: 60000,
  });

  const scenarios = scenariosData?.scenarios ?? [];

  const loadScenario = async (name: string) => {
    setLoadingScenario(name);
    setResultMessage(null);
    try {
      const result = await fetchApi<ScenarioLoadResult>(
        `/demo/scenarios/load?name=${name}&tenant_id=${MOCK_TENANT_ID}`,
        { method: "POST" },
      );
      setResultMessage({ type: "success", text: `Scenario "${result.scenario}" loaded — ${result.keyword_count} keywords seeded` });
      queryClient.invalidateQueries({ queryKey: ["demo-readiness"] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["keywords"] });
    } catch (err) {
      setResultMessage({ type: "error", text: err instanceof Error ? err.message : "Failed to load scenario" });
    } finally {
      setLoadingScenario(null);
    }
  };

  const resetWorkspace = async () => {
    setLoadingReset(true);
    setResultMessage(null);
    try {
      await fetchApi(`/demo/reset?tenant_id=${MOCK_TENANT_ID}`, { method: "POST" });
      setResultMessage({ type: "success", text: "Workspace reset — all demo data cleared, Redis flushed" });
      queryClient.invalidateQueries();
      refetchReadiness();
    } catch (err) {
      setResultMessage({ type: "error", text: err instanceof Error ? err.message : "Failed to reset workspace" });
    } finally {
      setLoadingReset(false);
    }
  };

  const checkEntries = readiness ? Object.entries(readiness.checks) : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">DEMO_CONTROL</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Scenario injection & workspace management</p>
        </div>
        <div className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 ${
          readiness?.overall_healthy
            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
            : "bg-red-500/10 border-red-500/20 text-red-400"
        }`}>
          <span className={`w-2 h-2 rounded-full ${readiness?.overall_healthy ? "bg-emerald-500" : "bg-red-500"} ${!readiness?.overall_healthy ? "animate-pulse" : ""}`} />
          {readiness?.readiness.toUpperCase() ?? "CHECKING"}
        </div>
      </div>

      {/* Readiness Overview */}
      <motion.div
        initial={{ opacity: 0, y: -5 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-5"
      >
        <h3 className="text-sm font-mono text-slate-400 mb-4 uppercase tracking-wider">System Readiness</h3>
        {loadingReadiness ? (
          <div className="flex justify-center py-4">
            <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {checkEntries.map(([name, check]) => (
              <div key={name} className={`p-3 rounded-lg border ${
                check.healthy
                  ? "bg-emerald-500/5 border-emerald-500/20"
                  : "bg-red-500/5 border-red-500/20"
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  {name === "postgresql" ? <Database className="w-4 h-4 text-blue-400" /> :
                   name === "redis" ? <Database className="w-4 h-4 text-red-400" /> :
                   name === "temporal" ? <Server className="w-4 h-4 text-indigo-400" /> :
                   <Bot className="w-4 h-4 text-purple-400" />}
                  <span className={`text-[10px] font-mono font-bold uppercase ${
                    check.healthy ? "text-emerald-400" : "text-red-400"
                  }`}>{check.healthy ? "OK" : "FAIL"}</span>
                </div>
                <p className="text-[10px] font-mono text-slate-400 capitalize">{name}</p>
                <p className="text-[9px] font-mono text-slate-500 mt-0.5 truncate">{check.message}</p>
              </div>
            ))}
          </div>
        )}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scenario Loaders */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Sparkles className="w-5 h-5 text-platform-500" />
            LOAD_SCENARIO
          </h3>
          <p className="text-xs font-mono text-slate-500 mb-4">
            Instantly populate the workspace with realistic demo data for investor presentations.
          </p>
          {loadingScenarios ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : scenarios.length === 0 ? (
            <div className="text-center py-8 text-slate-500 font-mono text-sm">NO_SCENARIOS_AVAILABLE</div>
          ) : (
            <div className="space-y-3">
              {scenarios.map((scenario) => (
                <motion.div
                  key={scenario.name}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 rounded-lg bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-200">{scenario.name}</h4>
                      <p className="text-[10px] font-mono text-slate-500">{scenario.niche} · {scenario.keyword_count} keywords</p>
                    </div>
                  </div>
                  <button
                    onClick={() => loadScenario(scenario.name)}
                    disabled={loadingScenario === scenario.name}
                    className="w-full py-2 rounded-md bg-platform-600 hover:bg-platform-500 disabled:bg-slate-700 text-white text-xs font-mono font-bold transition-colors flex items-center justify-center gap-2"
                  >
                    {loadingScenario === scenario.name ? (
                      <><Loader2 className="w-3.5 h-3.5 animate-spin" /> LOADING...</>
                    ) : (
                      <><Sparkles className="w-3.5 h-3.5" /> LOAD {scenario.name.toUpperCase()}</>
                    )}
                  </button>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Reset & Actions */}
        <div className="space-y-6">
          <div className="glass-panel p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
              <RefreshCw className="w-5 h-5 text-red-400" />
              RESET_WORKSPACE
            </h3>
            <p className="text-xs font-mono text-slate-500 mb-4">
              Wipes campaign databases, clears Redis caches, resets circuit breakers, and restores clean tenant state.
            </p>
            <button
              onClick={resetWorkspace}
              disabled={loadingReset}
              className="w-full py-2.5 rounded-md bg-red-600 hover:bg-red-500 disabled:bg-slate-700 text-white text-xs font-mono font-bold transition-colors flex items-center justify-center gap-2"
            >
              {loadingReset ? (
                <><RefreshCw className="w-4 h-4 animate-spin" /> RESETTING...</>
              ) : (
                <><RefreshCw className="w-4 h-4" /> RESET WORKSPACE</>
              )}
            </button>
          </div>

          {/* Quick Actions */}
          <div className="glass-panel p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
              <Radio className="w-5 h-5 text-emerald-500" />
              QUICK_ACTIONS
            </h3>
            <div className="space-y-2">
              <button
                onClick={() => refetchReadiness()}
                className="w-full py-2 rounded-md bg-surface-darker border border-surface-border hover:border-platform-500/30 text-slate-300 text-xs font-mono transition-colors flex items-center justify-center gap-2"
              >
                <Database className="w-3.5 h-3.5" /> RE-CHECK SYSTEM READINESS
              </button>
            </div>
          </div>

          {/* Result Toast */}
          <AnimatePresence>
            {resultMessage && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={`p-4 rounded-lg border ${
                  resultMessage.type === "success"
                    ? "bg-emerald-500/10 border-emerald-500/20"
                    : "bg-red-500/10 border-red-500/20"
                }`}
              >
                <div className="flex items-start gap-2">
                  {resultMessage.type === "success" ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5" />
                  )}
                  <p className={`text-xs font-mono ${
                    resultMessage.type === "success" ? "text-emerald-300" : "text-red-300"
                  }`}>
                    {resultMessage.text}
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
