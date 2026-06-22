"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Server, Shield, Activity, Clock, Loader2,
  Cpu, Radio, ArrowRight, AlertTriangle, CheckCircle2,
  Key, Save, Trash2, X, Check,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

interface ProviderEntry {
  provider: string;
  uptime_pct: number;
  avg_latency_ms: number;
  total_calls_24h: number;
  success_count_24h: number;
  circuit_breaker_state: string;
  healthy: boolean;
  not_configured?: boolean;
}

interface ProviderHealthData {
  providers: Record<string, ProviderEntry>;
  overall_uptime_pct: number;
  healthy_providers: number;
  total_providers: number;
  not_configured_providers?: number;
  configured_providers?: number;
  fallback_chain: Record<string, string[]>;
}

interface KeyCatalogEntry {
  provider: string;
  label: string;
  category: string;
  fields: string[];
  configured: boolean;
  is_active: boolean;
  updated_at?: string;
  updated_by?: string | null;
}

interface KeyCatalogData {
  catalog: KeyCatalogEntry[];
  configured_count: number;
  total_in_catalog: number;
}

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  DataForSEO: <Server className="w-5 h-5 text-platform-400" />,
  Ahrefs: <Server className="w-5 h-5 text-amber-400" />,
  Scrapling: <Activity className="w-5 h-5 text-emerald-400" />,
  SearXNG: <Radio className="w-5 h-5 text-cyan-400" />,
  OpenPageRank: <Cpu className="w-5 h-5 text-purple-400" />,
  Hunter: <Activity className="w-5 h-5 text-rose-400" />,
  Trafilatura: <Activity className="w-5 h-5 text-indigo-400" />,
};

function getProviderIcon(name: string): React.ReactNode {
  return PROVIDER_ICONS[name] || <Server className="w-5 h-5 text-slate-400" />;
}

export default function ProvidersPage() {
  const { data, isLoading, refetch } = useQuery<ProviderHealthData>({
    queryKey: ["provider-health"],
    queryFn: () => fetchApi("/provider-health"),
    refetchInterval: 5000,
  });

  const providers = data?.providers ?? {};
  const entries = Object.entries(providers);
  const fallbackChains = data?.fallback_chain ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Providers</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Real-time provider status & fallback paths</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {data?.healthy_providers ?? 0}/{data?.total_providers ?? 0} HEALTHY
          </div>
          {(data?.not_configured_providers ?? 0) > 0 && (
            <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-amber-500/30 text-xs font-mono text-amber-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {data?.not_configured_providers} NOT CONFIGURED
            </div>
          )}
          <button onClick={() => refetch()} className="px-3 py-1.5 rounded-md bg-platform-600 hover:bg-platform-500 text-white text-xs font-mono font-bold transition-colors flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5" /> REFRESH
          </button>
        </div>
      </div>

      {/* Overview Bar */}
      <motion.div
        initial={{ opacity: 0, y: -5 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-4 flex items-center gap-6 overflow-x-auto"
      >
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-sm font-mono font-bold text-emerald-400">{data?.overall_uptime_pct ?? 100}%</span>
          <span className="text-[10px] font-mono text-slate-500">OVERALL UPTIME</span>
        </div>
        <div className="w-px h-6 bg-surface-border" />
        <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500">
          <Shield className="w-3.5 h-3.5" />
          Providers: <span className="text-slate-300 font-bold">{data?.total_providers ?? 0}</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          Healthy: <span className="text-emerald-400 font-bold">{data?.healthy_providers ?? 0}</span>
        </div>
      </motion.div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Provider Cards */}
          <div className="space-y-4">
            <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wider">Provider Status Cards</h3>
            {entries.map(([name, prov], i) => (
              <motion.div
                key={name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`glass-panel p-5 border-l-2 ${
                  prov.not_configured ? "border-l-slate-500 opacity-60" :
                  prov.circuit_breaker_state === "OPEN" ? "border-l-red-500" :
                  prov.circuit_breaker_state === "HALF_OPEN" ? "border-l-amber-500" :
                  prov.healthy ? "border-l-emerald-500" : "border-l-amber-500"
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    {getProviderIcon(name)}
                    <div>
                      <h4 className="text-sm font-semibold text-slate-200">{name}</h4>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          prov.circuit_breaker_state === "OPEN" ? "bg-red-500" :
                          prov.circuit_breaker_state === "HALF_OPEN" ? "bg-amber-500" :
                          prov.healthy ? "bg-emerald-500" : "bg-amber-500"
                        } ${prov.circuit_breaker_state !== "CLOSED" ? "animate-pulse" : ""}`} />
                        <span className="text-[10px] font-mono text-slate-500 uppercase">
                          CB: {prov.circuit_breaker_state}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded text-[10px] font-mono font-bold border ${
                    prov.not_configured
                      ? "bg-slate-500/10 text-slate-400 border-slate-500/20"
                      : prov.healthy
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}>
                    {prov.not_configured ? "NOT CONFIGURED" : prov.healthy ? "HEALTHY" : "DEGRADED"}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50 text-center">
                    <p className="text-lg font-bold font-mono text-slate-200">{prov.not_configured ? "—" : `${prov.uptime_pct}%`}</p>
                    <p className="text-[8px] font-mono text-slate-600 uppercase">Uptime</p>
                  </div>
                  <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50 text-center">
                    <p className="text-lg font-bold font-mono text-slate-200">{prov.not_configured ? "—" : `${prov.avg_latency_ms.toFixed(0)}ms`}</p>
                    <p className="text-[8px] font-mono text-slate-600 uppercase">Latency</p>
                  </div>
                  <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50 text-center">
                    <p className="text-lg font-bold font-mono text-slate-200">{prov.total_calls_24h}</p>
                    <p className="text-[8px] font-mono text-slate-600 uppercase">Calls/24h</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-surface-darker rounded-full overflow-hidden">
                    {prov.not_configured ? (
                      <div className="h-full w-full bg-slate-700/50" />
                    ) : (
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${prov.uptime_pct}%` }}
                        className={`h-full rounded-full ${
                          prov.uptime_pct >= 95 ? "bg-emerald-500" :
                          prov.uptime_pct >= 80 ? "bg-amber-500" : "bg-red-500"
                        }`}
                        transition={{ duration: 0.5 }}
                      />
                    )}
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 w-10 text-right">{prov.not_configured ? "0/0" : `${prov.success_count_24h}/${prov.total_calls_24h}`}</span>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="space-y-6">
            {/* Fallback Chains */}
            <div className="glass-panel p-6">
              <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
                <ArrowRight className="w-5 h-5 text-platform-500" />
                FALLBACK_CHAINS
              </h3>
              <div className="space-y-4">
                {Object.entries(fallbackChains).map(([category, chain]) => (
                  <div key={category}>
                    <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">{category}</p>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {chain.map((provider, idx) => {
                        const prov = providers[provider];
                        const isHealthy = prov?.healthy ?? false;
                        const isOpen = prov?.circuit_breaker_state === "OPEN";
                        return (
                          <div key={provider} className="flex items-center gap-1.5">
                            <div className={`px-2 py-1 rounded text-[10px] font-mono font-bold border flex items-center gap-1 ${
                              isOpen ? "bg-red-500/10 text-red-400 border-red-500/20" :
                              isHealthy ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                              "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            }`}>
                              <span className={`w-1 h-1 rounded-full ${
                                isOpen ? "bg-red-500" : isHealthy ? "bg-emerald-500" : "bg-amber-500"
                              }`} />
                              {provider}
                            </div>
                            {idx < chain.length - 1 && (
                              <ArrowRight className="w-3 h-3 text-slate-600" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Circuit Breaker Summary */}
            <div className="glass-panel p-6">
              <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
                <Shield className="w-5 h-5 text-amber-500" />
                CIRCUIT_BREAKERS
              </h3>
              <div className="space-y-2">
                {entries.map(([name, prov]) => {
                  const state = prov.circuit_breaker_state;
                  return (
                    <div key={name} className="flex items-center justify-between p-2.5 rounded-md bg-surface-darker/50 border border-surface-border/50">
                      <div className="flex items-center gap-2">
                        {getProviderIcon(name)}
                        <span className="text-xs font-mono text-slate-300">{name}</span>
                      </div>
                      <div className={`flex items-center gap-2 text-xs font-mono ${
                        state === "OPEN" ? "text-red-400" :
                        state === "HALF_OPEN" ? "text-amber-400" :
                        "text-emerald-400"
                      }`}>
                        <span className={`w-2 h-2 rounded-full ${
                          state === "OPEN" ? "bg-red-500" :
                          state === "HALF_OPEN" ? "bg-amber-500" :
                          "bg-emerald-500"
                        } ${state !== "CLOSED" ? "animate-pulse" : ""}`} />
                        {state}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Provider Latency Radar */}
            <div className="glass-panel p-6">
              <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
                <Clock className="w-5 h-5 text-indigo-500" />
                LATENCY_OVERVIEW
              </h3>
              <div className="space-y-3">
                {entries
                  .sort(([, a], [, b]) => b.avg_latency_ms - a.avg_latency_ms)
                  .map(([name, prov]) => (
                    <div key={name}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-mono text-slate-400">{name}</span>
                        <span className={`text-[10px] font-mono ${
                          prov.avg_latency_ms < 100 ? "text-emerald-400" :
                          prov.avg_latency_ms < 500 ? "text-amber-400" : "text-red-400"
                        }`}>{prov.avg_latency_ms.toFixed(0)}ms</span>
                      </div>
                      <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.min(prov.avg_latency_ms / 10, 100)}%` }}
                          className={`h-full rounded-full ${
                            prov.avg_latency_ms < 100 ? "bg-emerald-500" :
                            prov.avg_latency_ms < 500 ? "bg-amber-500" : "bg-red-500"
                          }`}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Provider Key Management Section */}
      <ProviderKeyManager />
    </div>
  );
}


function ProviderKeyManager() {
  const queryClient = useQueryClient();
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});

  const { data, isLoading, isError, refetch } = useQuery<KeyCatalogData>({
    queryKey: ["provider-keys-catalog"],
    queryFn: () => fetchApi<KeyCatalogData>("/provider-keys"),
  });

  const saveMutation = useMutation({
    mutationFn: async ({ provider, values }: { provider: string; values: Record<string, string> }) => {
      return fetchApi(`/provider-keys/${provider}`, {
        method: "PUT",
        body: JSON.stringify(values),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["provider-keys-catalog"] });
      queryClient.invalidateQueries({ queryKey: ["provider-health"] });
      setEditingProvider(null);
      setFormValues({});
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (provider: string) => {
      return fetchApi(`/provider-keys/${provider}`, { method: "DELETE" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["provider-keys-catalog"] });
      queryClient.invalidateQueries({ queryKey: ["provider-health"] });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ provider, enable }: { provider: string; enable: boolean }) => {
      const action = enable ? "enable" : "disable";
      return fetchApi(`/providers/keys/${provider}/${action}`, { method: "POST" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["provider-keys-catalog"] });
      queryClient.invalidateQueries({ queryKey: ["provider-health"] });
    },
  });

  const testMutation = useMutation({
    mutationFn: async (provider: string) => {
      return fetchApi<{ healthy: boolean; status_code?: number; error?: string }>(`/providers/keys/${provider}/test`, { method: "POST" });
    },
    onSuccess: (data: any) => {
      if (data.healthy) {
        toast.success(`${data.provider || "Provider"} is healthy`, {
          description: data.status_code ? `HTTP ${data.status_code}` : "Connection successful",
        });
      } else {
        toast.error(`${data.provider || "Provider"} is unhealthy`, {
          description: data.error || `HTTP ${data.status_code}`,
        });
      }
    },
    onError: (error: any) => {
      toast.error("Test failed", { description: error?.detail || error?.message || "Unknown error" });
    },
  });

  const handleStartEdit = (entry: KeyCatalogEntry) => {
    setEditingProvider(entry.provider);
    const initial: Record<string, string> = {};
    for (const f of entry.fields) initial[f] = "";
    setFormValues(initial);
  };

  const handleCancelEdit = () => {
    setEditingProvider(null);
    setFormValues({});
  };

  const handleSave = (provider: string) => {
    saveMutation.mutate({ provider, values: formValues });
  };

  const fieldLabel = (f: string) => f.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const fieldType = (f: string) => (f.includes("password") || f.includes("api_key")) ? "password" : "text";

  return (
    <div className="glass-panel p-6 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-medium text-slate-200 flex items-center gap-2 font-mono">
            <Key className="w-5 h-5 text-platform-500" />
            API_KEYS
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Configure provider credentials at runtime. Keys are encrypted at rest (AES-256-GCM). {data?.configured_count ?? 0}/{data?.total_in_catalog ?? 0} configured.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
        >
          REFRESH
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
        </div>
      ) : isError ? (
        <div className="text-sm text-red-400 font-mono">Failed to load key catalog. Check console for details.</div>
      ) : (
        <div className="space-y-3">
          {data?.catalog.map((entry) => {
            const isEditing = editingProvider === entry.provider;
            return (
              <div
                key={entry.provider}
                className={`p-4 rounded-md border ${
                  entry.configured
                    ? "bg-emerald-500/5 border-emerald-500/20"
                    : "bg-surface-darker/30 border-surface-border/50"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-mono font-semibold text-slate-200">{entry.label}</h3>
                      <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.5 rounded bg-surface-darker border border-surface-border uppercase">
                        {entry.category}
                      </span>
                      {entry.configured ? (
                        <span className={`text-[10px] font-mono flex items-center gap-1 ${entry.is_active ? "text-emerald-400" : "text-slate-500"}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${entry.is_active ? "bg-emerald-500" : "bg-slate-500"}`} />
                          {entry.is_active ? "ENABLED" : "DISABLED"}
                        </span>
                      ) : (
                        <span className="text-[10px] font-mono text-amber-400 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> NOT CONFIGURED
                        </span>
                      )}
                    </div>
                    {entry.configured && entry.updated_at && (
                      <p className="text-[10px] font-mono text-slate-500 mt-1">
                        Last updated: {new Date(entry.updated_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {entry.configured && !isEditing && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => toggleMutation.mutate({ provider: entry.provider, enable: !entry.is_active })}
                        disabled={toggleMutation.isPending}
                        className={entry.is_active ? "text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10" : "text-slate-400 border-slate-500/30 hover:bg-slate-500/10"}
                      >
                        {entry.is_active ? "ENABLED" : "DISABLED"}
                      </Button>
                    )}
                    {entry.configured && !isEditing && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => testMutation.mutate(entry.provider)}
                        disabled={testMutation.isPending}
                      >
                        TEST
                      </Button>
                    )}
                    {!isEditing && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleStartEdit(entry)}
                        disabled={deleteMutation.isPending}
                      >
                        {entry.configured ? "ROTATE" : "ADD"}
                      </Button>
                    )}
                    {entry.configured && !isEditing && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          if (confirm(`Remove the configured key for ${entry.label}?`)) {
                            deleteMutation.mutate(entry.provider);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="text-red-400 border-red-500/30 hover:bg-red-500/10"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </div>
                </div>

                {isEditing && (
                  <div className="mt-4 pt-4 border-t border-surface-border/50 space-y-3">
                    {entry.fields.map((field) => (
                      <div key={field}>
                        <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                          {fieldLabel(field)}
                        </label>
                        <Input
                          type={fieldType(field)}
                          value={formValues[field] || ""}
                          onChange={(e) => setFormValues({ ...formValues, [field]: e.target.value })}
                          placeholder={`Enter ${fieldLabel(field).toLowerCase()}`}
                          className="mt-1 font-mono"
                          autoComplete="off"
                        />
                      </div>
                    ))}
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleCancelEdit}
                        disabled={saveMutation.isPending}
                      >
                        <X className="w-3.5 h-3.5" /> CANCEL
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleSave(entry.provider)}
                        disabled={saveMutation.isPending || entry.fields.some((f) => !formValues[f])}
                      >
                        {saveMutation.isPending ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Save className="w-3.5 h-3.5" />
                        )}
                        SAVE
                      </Button>
                    </div>
                    {saveMutation.isError && (
                      <p className="text-xs text-red-400 font-mono">
                        Failed: {(saveMutation.error as Error)?.message || "unknown"}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
