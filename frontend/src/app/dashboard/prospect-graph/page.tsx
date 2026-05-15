"use client";

import { useState } from "react";
import { Network, Search, GitBranch, Target, Loader2, Activity, Users, Link2, ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface GraphNode {
  id: string;
  label: string;
  domain_authority: number;
  group?: string;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  relationship_type: string;
}

interface GraphStats {
  node_count: number;
  edge_count: number;
  density: number;
  central_domains: string[];
}

interface AuthorityBridge {
  source_domain: string;
  bridge_domain: string;
  target_domain: string;
  authority_gain: number;
}

export default function ProspectGraphPage() {
  const [searchDomain, setSearchDomain] = useState("");
  const [highlightBridges, setHighlightBridges] = useState(false);

  const { data: graphData, isLoading } = useQuery<{ nodes: GraphNode[]; edges: GraphEdge[] }>({
    queryKey: ["prospect-graph", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/prospect-graph?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: stats } = useQuery<GraphStats>({
    queryKey: ["prospect-graph", "stats", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/prospect-graph/stats?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: bridges } = useQuery<AuthorityBridge[]>({
    queryKey: ["prospect-graph", "bridges", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/prospect-graph/bridges?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const nodes = graphData?.nodes ?? [];
  const edges = graphData?.edges ?? [];
  const bridgeList = bridges ?? [];

  const searchedDomain = searchDomain.trim().toLowerCase();
  const connectedDomains = searchedDomain
    ? edges
        .filter((e) => e.source.toLowerCase().includes(searchedDomain) || e.target.toLowerCase().includes(searchedDomain))
        .slice(0, 20)
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">PROSPECT_GRAPH</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Domain relationship visualization</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setHighlightBridges(!highlightBridges)}
            className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 transition-colors ${
              highlightBridges
                ? "bg-purple-500/10 border-purple-500/30 text-purple-400"
                : "bg-surface-darker border-surface-border text-slate-400"
            }`}
          >
            <GitBranch className="w-4 h-4" />
            BRIDGES
          </button>
          <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
            <Network className="w-4 h-4" />
            {nodes.length} NODES
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Graph Statistics */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Activity className="w-5 h-5 text-platform-500" />
            GRAPH_STATS
          </h3>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : stats ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <StatBox label="NODES" value={String(stats.node_count)} />
                <StatBox label="EDGES" value={String(stats.edge_count)} />
              </div>
              <StatBox label="DENSITY" value={`${(stats.density * 100).toFixed(2)}%`} />
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase mb-2">Central Domains</p>
                <div className="space-y-1">
                  {stats.central_domains.slice(0, 5).map((d, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400 truncate">{d}</p>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500 font-mono">NO_GRAPH_DATA</div>
          )}
        </div>

        {/* Graph Visualization */}
        <div className="lg:col-span-2 glass-panel overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <Network className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">DOMAIN_GRAPH</h3>
            <span className="ml-auto text-[10px] font-mono text-slate-600">
              {nodes.length} NODES &middot; {edges.length} EDGES
            </span>
          </div>
          <div className="p-6 min-h-[400px]">
            {isLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
              </div>
            ) : nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <div className="w-16 h-16 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-4">
                  <Network className="text-slate-600" size={32} />
                </div>
                <h3 className="text-lg font-medium text-slate-300 font-mono">No Graph Data</h3>
                <p className="text-sm text-slate-500 mt-2 max-w-sm">
                  Domain relationship graph will populate as prospects are identified and scored.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {nodes.slice(0, 40).map((node) => (
                  <div
                    key={node.id}
                    className={`p-3 rounded-lg border text-center transition-all hover:scale-105 ${
                      highlightBridges && bridgeList.some(
                        (b) => b.bridge_domain === node.label || b.source_domain === node.label
                      )
                        ? "bg-purple-500/10 border-purple-500/30"
                        : "bg-surface-darker/50 border-surface-border/50"
                    }`}
                  >
                    <div className="w-8 h-8 rounded-full bg-platform-500/20 border border-platform-500/30 flex items-center justify-center mx-auto mb-2">
                      <span className="text-[10px] font-mono text-platform-400 font-bold">
                        {node.label.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <p className="text-[10px] font-mono text-slate-300 truncate">{node.label}</p>
                    <p className="text-[9px] font-mono text-slate-600">DA: {Math.round(node.domain_authority * 100)}</p>
                  </div>
                ))}
                {nodes.length > 40 && (
                  <div className="p-3 rounded-lg border border-surface-border/50 bg-surface-darker/30 flex items-center justify-center">
                    <span className="text-[10px] font-mono text-slate-500">+{nodes.length - 40} MORE</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Search & Bridges */}
        <div className="space-y-6">
          {/* Domain Search */}
          <div className="glass-panel p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
              <Search className="w-5 h-5 text-cyan-500" />
              SEARCH_DOMAIN
            </h3>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="domain.com"
                value={searchDomain}
                onChange={(e) => setSearchDomain(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500 transition-all font-mono"
              />
            </div>
            {connectedDomains.length > 0 && (
              <div className="space-y-1 max-h-[200px] overflow-auto">
                {connectedDomains.map((e, i) => (
                  <div key={i} className="flex items-center gap-1 text-[10px] font-mono text-slate-400 p-1 rounded hover:bg-surface-darker/50">
                    <span className="truncate max-w-[70px]">{e.source}</span>
                    <ArrowRight className="w-3 h-3 shrink-0" />
                    <span className="truncate max-w-[70px]">{e.target}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Authority Bridges */}
          <div className="glass-panel p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
              <Target className="w-5 h-5 text-purple-500" />
              AUTHORITY_BRIDGES
            </h3>
            {bridgeList.length === 0 ? (
              <div className="text-center py-6 text-slate-500 font-mono text-xs">NO_BRIDGES_FOUND</div>
            ) : (
              <div className="space-y-2 max-h-[250px] overflow-auto">
                {bridgeList.map((b, i) => (
                  <div key={i} className="p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                    <div className="flex items-center gap-1 text-[9px] font-mono">
                      <span className="text-slate-400 truncate max-w-[60px]">{b.source_domain}</span>
                      <span className="text-purple-400">&rarr;</span>
                      <span className="text-purple-300 truncate max-w-[60px] font-bold">{b.bridge_domain}</span>
                      <span className="text-purple-400">&rarr;</span>
                      <span className="text-slate-400 truncate max-w-[60px]">{b.target_domain}</span>
                    </div>
                    <div className="w-full h-1 bg-surface-darker rounded-full overflow-hidden mt-1">
                      <div className="h-full bg-purple-500 rounded-full" style={{ width: `${b.authority_gain * 100}%` }} />
                    </div>
                    <p className="text-[8px] font-mono text-slate-600 mt-0.5">GAIN: {Math.round(b.authority_gain * 100)}%</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border/50 text-center">
      <p className="text-lg font-bold font-mono text-slate-200">{value}</p>
      <p className="text-[9px] font-mono text-slate-500 uppercase mt-0.5">{label}</p>
    </div>
  );
}
