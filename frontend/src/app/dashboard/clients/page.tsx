"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Users, Plus, Search, Loader2, Globe, MapPin, Target, TrendingUp, CheckCircle2, AlertTriangle, ArrowRight, Sparkles, Building2, Briefcase, Bot } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useCommandCenter } from "@/hooks/use-command-center";
import { useRouter } from "next/navigation";
import { useClientStore } from "@/hooks/use-client";

interface ClientProfile {
  id: string;
  name: string;
  domain: string;
  niche: string;
  business_type: string;
  geo_focus: string[];
  profile_data: Record<string, any>;
  competitors: string[];
  created_at: string;
  keyword_count?: number;
  campaign_count?: number;
}

const NICHE_OPTIONS = [
  "B2B SaaS", "E-commerce", "Healthcare", "Legal", "Real Estate",
  "Local Services", "Content Publishing", "Agency", "Education",
  "Finance", "Technology", "Hospitality", "Manufacturing", "Non-profit",
];

export default function ClientsPage() {
  const { openCommand } = useCommandCenter();
  const router = useRouter();
  const setClient = useClientStore((s) => s.setClient);
  const [search, setSearch] = useState("");

  const { data: clients = [], isLoading } = useQuery<ClientProfile[]>({
    queryKey: ["clients"],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 30000,
  });

  const filtered = clients.filter((c) =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.domain.includes(search)
  );

  const switchToClient = (client: ClientProfile) => {
    setClient({ id: client.id, name: client.name, domain: client.domain, niche: client.niche || "General" });
    router.push("/dashboard");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Clients</h1>
          <p className="text-slate-500 text-sm mt-0.5">{clients.length} client{clients.length !== 1 ? "s" : ""}</p>
        </div>
        <button onClick={() => openCommand("add_client")} className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-sm font-bold font-mono transition-colors shadow-lg shadow-platform-900/30 flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Client
        </button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          placeholder="Search clients..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-surface-darker border border-surface-border rounded-lg py-2 pl-10 pr-4 text-sm text-slate-200 focus:outline-none focus:border-platform-500/50 transition-colors"
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 text-platform-500 animate-spin" /></div>
      ) : filtered.length === 0 ? (
        <div className="glass-panel p-12 flex flex-col items-center justify-center text-center">
          <div className="w-14 h-14 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-3">
            <Users className="text-slate-600" size={28} />
          </div>
          <h3 className="text-base font-medium text-slate-300">No clients found</h3>
          <p className="text-sm text-slate-500 mt-1">Add a client to start building their SEO intelligence.</p>
          <button onClick={() => openCommand("add_client")} className="mt-4 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono">
            + ADD CLIENT
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((client, i) => {
            const pd = client.profile_data || {};
            const derivedNiche = client.niche || pd?.derived_industry || "General";
            const goals = pd?.goals || [];
            const hasEnrichment = pd?.last_analyzed;
            return (
              <motion.div
                key={client.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="glass-panel p-5 hover:border-platform-500/30 transition-all cursor-pointer group"
                onClick={() => switchToClient(client)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-sm">
                      {client.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-200">{client.name}</h3>
                      <p className="text-[10px] font-mono text-slate-500">{client.domain}</p>
                    </div>
                  </div>
                  <div className={`px-2 py-0.5 rounded text-[9px] font-mono border ${
                    hasEnrichment ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  }`}>
                    {hasEnrichment ? "ENRICHED" : "PENDING"}
                  </div>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center gap-2 text-slate-500">
                    <Briefcase className="w-3 h-3" />
                    <span>{derivedNiche}</span>
                    {client.business_type && <span className="text-platform-400">· {client.business_type}</span>}
                  </div>
                  {client.geo_focus && client.geo_focus.length > 0 && (
                    <div className="flex items-center gap-2 text-slate-500">
                      <MapPin className="w-3 h-3" />
                      <span>{client.geo_focus.join(", ")}</span>
                    </div>
                  )}
                  {goals.length > 0 && (
                    <div className="flex items-center gap-2 text-slate-500">
                      <Target className="w-3 h-3" />
                      <span>{goals.slice(0, 3).join(", ")}{goals.length > 3 ? ` +${goals.length - 3}` : ""}</span>
                    </div>
                  )}
                  {client.competitors && client.competitors.length > 0 && (
                    <div className="flex items-center gap-2 text-slate-500">
                      <TrendingUp className="w-3 h-3" />
                      <span>{client.competitors.length} competitors</span>
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-surface-border/50 flex items-center justify-between text-[10px] font-mono text-slate-600">
                  <span>{client.keyword_count ?? 0} kw · {client.campaign_count ?? 0} campaigns</span>
                  <span className="text-platform-400 group-hover:underline flex items-center gap-1">
                    Open <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
