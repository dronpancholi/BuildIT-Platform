"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { 
  TrendingUp, TrendingDown, Activity, AlertTriangle,
  Users, GitBranch, Mail, CheckCircle2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useRouter } from "next/navigation";
import type { ClientInfo } from "@/hooks/use-client";

interface CustomerHealthData {
  id: string;
  name: string;
  domain: string;
  niche: string;
  health_score: number;
  active_campaigns: number;
  total_keywords: number;
  links_acquired: number;
  reply_rate: number;
  status: "healthy" | "at_risk" | "critical";
  recent_activity: any[];
}

function getHealthStatus(score: number): "healthy" | "at_risk" | "critical" {
  if (score >= 0.7) return "healthy";
  if (score >= 0.4) return "at_risk";
  return "critical";
}

function getHealthColor(score: number): string {
  if (score >= 0.7) return "text-emerald-400";
  if (score >= 0.4) return "text-amber-400";
  return "text-red-400";
}

function getHealthBg(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

function getStatusBadge(status: "healthy" | "at_risk" | "critical") {
  switch (status) {
    case "healthy":
      return <span className="px-1.5 py-0.5 text-[8px] font-mono rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">HEALTHY</span>;
    case "at_risk":
      return <span className="px-1.5 py-0.5 text-[8px] font-mono rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">AT RISK</span>;
    case "critical":
      return <span className="px-1.5 py-0.5 text-[8px] font-mono rounded-full bg-red-500/10 text-red-400 border border-red-500/20">CRITICAL</span>;
  }
}

export function CustomerHealthOverview() {
  const router = useRouter();
  
  const { data: customers = [], isLoading } = useQuery<CustomerHealthData[]>({
    queryKey: ["customers", "health"],
    queryFn: async () => {
      // Fetch clients
      const clientsResponse = await fetchApi<any>(`/clients?tenant_id=${MOCK_TENANT_ID}`);
      const clients = clientsResponse?.data || [];
      
      // Fetch campaign data for each client
      const campaignsResponse = await fetchApi<any>(`/business-intelligence/intelligence/campaigns?tenant_id=${MOCK_TENANT_ID}`);
      const campaigns = campaignsResponse?.data?.campaigns || [];
      
      // Merge data
      return clients.map((client: any) => {
        const clientCampaigns = campaigns.filter((c: any) => c.client_id === client.id);
        const activeCampaigns = clientCampaigns.filter((c: any) => c.status === "active" || c.status === "monitoring");
        const avgHealth = clientCampaigns.length > 0 
          ? clientCampaigns.reduce((sum: number, c: any) => sum + c.health_score, 0) / clientCampaigns.length
          : 0;
        
        return {
          id: client.id,
          name: client.name,
          domain: client.domain,
          niche: client.niche,
          health_score: avgHealth,
          active_campaigns: activeCampaigns.length,
          total_keywords: client.keyword_count || 0,
          links_acquired: clientCampaigns.reduce((sum: number, c: any) => sum + c.acquired_link_count, 0),
          reply_rate: 0.18, // Placeholder - would come from threads data
          status: getHealthStatus(avgHealth),
          recent_activity: [],
        };
      });
    },
    refetchInterval: 60000,
  });

  const stats = useMemo(() => {
    const total = customers.length;
    const healthy = customers.filter(c => c.status === "healthy").length;
    const atRisk = customers.filter(c => c.status === "at_risk").length;
    const critical = customers.filter(c => c.status === "critical").length;
    const avgHealth = total > 0 
      ? customers.reduce((sum, c) => sum + c.health_score, 0) / total 
      : 0;
    
    return { total, healthy, atRisk, critical, avgHealth };
  }, [customers]);

  if (isLoading) {
    return (
      <div className="glass-panel p-4 flex items-center justify-center min-h-[200px]">
        <Activity className="w-6 h-6 text-platform-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Stats Strip */}
      <div className="grid grid-cols-4 gap-2">
        <div className="glass-panel p-3">
          <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-500 uppercase mb-1">
            <Users className="w-3 h-3" /> Total
          </div>
          <p className="text-lg font-bold font-mono text-slate-100">{stats.total}</p>
        </div>
        <div className="glass-panel p-3 border-emerald-500/20">
          <div className="flex items-center gap-1.5 text-[9px] font-mono text-emerald-500 uppercase mb-1">
            <CheckCircle2 className="w-3 h-3" /> Healthy
          </div>
          <p className="text-lg font-bold font-mono text-emerald-400">{stats.healthy}</p>
        </div>
        <div className="glass-panel p-3 border-amber-500/20">
          <div className="flex items-center gap-1.5 text-[9px] font-mono text-amber-500 uppercase mb-1">
            <AlertTriangle className="w-3 h-3" /> At Risk
          </div>
          <p className="text-lg font-bold font-mono text-amber-400">{stats.atRisk}</p>
        </div>
        <div className="glass-panel p-3 border-red-500/20">
          <div className="flex items-center gap-1.5 text-[9px] font-mono text-red-500 uppercase mb-1">
            <AlertTriangle className="w-3 h-3" /> Critical
          </div>
          <p className="text-lg font-bold font-mono text-red-400">{stats.critical}</p>
        </div>
      </div>

      {/* Customer List */}
      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
          <span className="text-[9px] font-mono text-slate-500 uppercase">Portfolio Health</span>
          <span className="text-[9px] font-mono text-slate-600">
            Avg Health: <span className={getHealthColor(stats.avgHealth)}>{(stats.avgHealth * 100).toFixed(0)}%</span>
          </span>
        </div>

        {customers.length === 0 ? (
          <div className="p-8 text-center">
            <Users className="w-8 h-8 text-slate-700 mx-auto mb-2" />
            <p className="text-[10px] font-mono text-slate-600">No customers yet</p>
          </div>
        ) : (
          <div className="divide-y divide-surface-border">
            {customers.map((customer, i) => (
              <motion.div
                key={customer.id}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.02 }}
                onClick={() => router.push(`/dashboard/customers/${customer.id}`)}
                className="px-4 py-3 hover:bg-surface-border/20 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-xs flex-shrink-0">
                    {customer.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-slate-200 font-medium truncate">{customer.name}</span>
                      {getStatusBadge(customer.status)}
                    </div>
                    <div className="flex items-center gap-3 text-[9px] font-mono text-slate-600">
                      <span>{customer.domain}</span>
                      <span className="text-platform-500">{customer.niche}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${customer.health_score * 100}%` }}
                            className={`h-full rounded-full ${getHealthBg(customer.health_score)}`}
                          />
                        </div>
                        <span className={`text-[10px] font-mono font-bold ${getHealthColor(customer.health_score)}`}>
                          {(customer.health_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <div className="text-right min-w-[60px]">
                      <div className="text-[9px] font-mono text-slate-600">Campaigns</div>
                      <div className="text-xs font-mono text-slate-300">{customer.active_campaigns}</div>
                    </div>
                  </div>
                </div>

                {/* Mini metrics */}
                <div className="mt-2 ml-11 grid grid-cols-3 gap-4">
                  <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-600">
                    <GitBranch className="w-3 h-3 text-platform-500" />
                    <span>{customer.total_keywords} keywords</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-600">
                    <Users className="w-3 h-3 text-amber-500" />
                    <span>{customer.links_acquired} links</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[9px] font-mono text-slate-600">
                    <Mail className="w-3 h-3 text-blue-500" />
                    <span>{(customer.reply_rate * 100).toFixed(1)}% reply</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}