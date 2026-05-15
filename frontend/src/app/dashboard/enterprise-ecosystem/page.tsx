"use client";

import { motion } from "framer-motion";
import {
  Building2, GitFork, Users, Link2, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface OrganizationIntelligence {
  org_health: number;
  efficiency: number;
  collaboration_score: number;
}

interface OrgGraphNode {
  department: string;
  teams: string[];
  relationships: string[];
}

interface OrganizationalGraph {
  nodes: OrgGraphNode[];
}

interface CrossTeamCoordination {
  coordination_success_rate: number;
  avg_handoff_time_minutes: number;
  teams: { team_a: string; team_b: string; success_rate: number }[];
}

interface OperationalDependency {
  department: string;
  depends_on: string[];
  dependency_type: string;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function EnterpriseEcosystemPage() {
  const { data: orgIntel, isLoading: loadingIntel } = useQuery<OrganizationIntelligence>({
    queryKey: ["ecosystem-org-intel"],
    queryFn: () => fetchApi("/enterprise-ecosystem/organization-intelligence"),
    refetchInterval: 15000,
  });

  const { data: orgGraph, isLoading: loadingGraph } = useQuery<OrganizationalGraph>({
    queryKey: ["ecosystem-org-graph"],
    queryFn: () => fetchApi("/enterprise-ecosystem/organizational-graph"),
    refetchInterval: 15000,
  });

  const { data: crossTeam, isLoading: loadingCross } = useQuery<CrossTeamCoordination>({
    queryKey: ["ecosystem-cross-team"],
    queryFn: () => fetchApi("/enterprise-ecosystem/cross-team-coordination"),
    refetchInterval: 15000,
  });

  const { data: dependencies, isLoading: loadingDeps } = useQuery<OperationalDependency[]>({
    queryKey: ["ecosystem-dependencies"],
    queryFn: () => fetchApi("/enterprise-ecosystem/operational-dependencies"),
    refetchInterval: 15000,
  });

  const depList = dependencies || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">ECOSYSTEM</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Enterprise Ecosystem Intelligence Dashboard</p>
        </div>
        {orgIntel && (
          <div className="px-3 py-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400 flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            HEALTH: {Math.round(orgIntel.org_health)}%
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Organization Intelligence */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">ORG_INTELLIGENCE</h3>
          </div>
          {loadingIntel ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !orgIntel ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No organization intelligence data</div>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                <span className={`text-3xl font-bold font-mono ${orgIntel.org_health >= 80 ? "text-emerald-400" : orgIntel.org_health >= 50 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(orgIntel.org_health)}%
                </span>
                <p className="text-[10px] font-mono text-slate-500 mt-1">Org Health</p>
              </div>
              <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                <span className={`text-3xl font-bold font-mono ${orgIntel.efficiency >= 80 ? "text-emerald-400" : orgIntel.efficiency >= 50 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(orgIntel.efficiency)}%
                </span>
                <p className="text-[10px] font-mono text-slate-500 mt-1">Efficiency</p>
              </div>
              <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                <span className={`text-3xl font-bold font-mono ${orgIntel.collaboration_score >= 80 ? "text-emerald-400" : orgIntel.collaboration_score >= 50 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(orgIntel.collaboration_score)}%
                </span>
                <p className="text-[10px] font-mono text-slate-500 mt-1">Collaboration</p>
              </div>
            </div>
          )}
        </motion.div>

        {/* Cross-Team Coordination */}
        <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">CROSS_TEAM_COORDINATION</h3>
          </div>
          {loadingCross ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !crossTeam ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No coordination data</div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <span className={`text-2xl font-bold font-mono ${crossTeam.coordination_success_rate >= 80 ? "text-emerald-400" : crossTeam.coordination_success_rate >= 50 ? "text-amber-400" : "text-red-400"}`}>
                    {Math.round(crossTeam.coordination_success_rate)}%
                  </span>
                  <p className="text-[10px] font-mono text-slate-500 mt-1">Success Rate</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <span className="text-2xl font-bold font-mono text-amber-400">{Math.round(crossTeam.avg_handoff_time_minutes)}m</span>
                  <p className="text-[10px] font-mono text-slate-500 mt-1">Avg Handoff Time</p>
                </div>
              </div>
              {crossTeam.teams.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Team Pairs</p>
                  <div className="space-y-2">
                    {crossTeam.teams.map((t, i) => (
                      <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/30 border border-surface-border/30">
                        <span className="text-xs font-mono text-slate-300">{t.team_a} ↔ {t.team_b}</span>
                        <span className={`text-[10px] font-mono font-bold ${t.success_rate >= 80 ? "text-emerald-400" : t.success_rate >= 50 ? "text-amber-400" : "text-red-400"}`}>
                          {Math.round(t.success_rate)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Organizational Graph */}
        <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <GitFork className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">ORGANIZATIONAL_GRAPH</h3>
          </div>
          {loadingGraph ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !orgGraph || orgGraph.nodes.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No organizational graph data</div>
          ) : (
            <div className="space-y-3">
              {orgGraph.nodes.map((node, i) => (
                <motion.div
                  key={node.department || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-mono text-slate-200">{node.department}</span>
                    <span className="text-[10px] font-mono text-slate-500">{node.teams.length} teams</span>
                  </div>
                  {node.teams.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {node.teams.map((team, j) => (
                        <span key={j} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-platform-500/10 text-platform-400 border border-platform-500/20">{team}</span>
                      ))}
                    </div>
                  )}
                  {node.relationships.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {node.relationships.map((rel, j) => (
                        <span key={j} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-500/10 text-slate-500">{rel}</span>
                      ))}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Operational Dependencies */}
        <motion.div {...slideUp} transition={{ delay: 0.15 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Link2 className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">OPERATIONAL_DEPENDENCIES</h3>
          </div>
          {loadingDeps ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : depList.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No dependency data</div>
          ) : (
            <div className="space-y-3">
              {depList.map((dep, i) => (
                <motion.div
                  key={dep.department || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-mono text-slate-200">{dep.department}</span>
                    <span className="text-[10px] font-mono text-slate-500">{dep.dependency_type}</span>
                  </div>
                  {dep.depends_on.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {dep.depends_on.map((d, j) => (
                        <span key={j} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">{d}</span>
                      ))}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
