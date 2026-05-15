"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Link2, Search, Lightbulb, Activity,
  GitBranch, Radio, Settings, ChevronDown, ChevronRight,
  Bot, Users, Globe, Check,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useClientStore, type ClientInfo } from "@/hooks/use-client";

const CLIENTS: ClientInfo[] = [
  { id: "00000000-0000-0000-0000-000000000001", name: "TechStart Inc.", domain: "techstart.io", niche: "B2B SaaS" },
  { id: "11111111-1111-1111-1111-111111111111", name: "GrowthMedia Co.", domain: "growthmedia.io", niche: "Content Marketing" },
];

const BUSINESS_NAV = [
  { href: "/dashboard", icon: <LayoutDashboard size={17} />, label: "Command Center" },
  { href: "/dashboard/campaigns", icon: <GitBranch size={17} />, label: "Campaigns" },
  { href: "/dashboard/keywords", icon: <Search size={17} />, label: "Keywords" },
  { href: "/dashboard/seo-intelligence", icon: <Globe size={17} />, label: "SEO Intelligence" },
  { href: "/dashboard/backlink-intelligence", icon: <Link2 size={17} />, label: "Backlinks" },
  { href: "/dashboard/recommendations", icon: <Lightbulb size={17} />, label: "Recommendations" },
  { href: "/dashboard/local-seo", icon: <Users size={17} />, label: "Local SEO" },
  { href: "/dashboard/prospect-graph", icon: <Radio size={17} />, label: "Prospect Graph" },
  { href: "/dashboard/assistant", icon: <Bot size={17} />, label: "Assistant" },
];

const SYSTEM_NAV = [
  { href: "/dashboard/system", icon: <Activity size={17} />, label: "Platform Health" },
  { href: "/dashboard/approvals", icon: <Link2 size={17} />, label: "Approvals" },
  { href: "/dashboard/events", icon: <Radio size={17} />, label: "Event Stream" },
  { href: "/dashboard/topology", icon: <GitBranch size={17} />, label: "Workflows" },
  { href: "/dashboard/war-room", icon: <Activity size={17} />, label: "War Room" },
  { href: "/dashboard/settings", icon: <Settings size={17} />, label: "Settings" },
];

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();
  const currentClient = useClientStore((s) => s.currentClient);
  const setClient = useClientStore((s) => s.setClient);
  const [showClients, setShowClients] = useState(false);
  const [showSystem, setShowSystem] = useState(false);

  return (
    <div className={cn("w-56 border-r border-surface-border bg-surface-card flex flex-col h-screen sticky top-0", className)}>
      <div className="p-5 pb-3">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-platform-600 flex items-center justify-center shadow-lg shadow-platform-500/20">
            <span className="font-bold text-white text-sm">B</span>
          </div>
          <span className="font-semibold text-base tracking-wide text-slate-200">
            Build<span className="text-platform-400">IT</span>
          </span>
        </Link>
      </div>

      {/* Client Switcher */}
      <div className="px-3 mb-3">
        <button
          onClick={() => setShowClients(!showClients)}
          className="flex items-center justify-between w-full px-3 py-2 rounded-lg bg-surface-darker/50 border border-surface-border/50 hover:border-platform-500/30 transition-all"
        >
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-6 h-6 rounded bg-platform-600/20 flex items-center justify-center text-[10px] font-bold text-platform-400 flex-shrink-0">
              {currentClient.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
            </div>
            <div className="text-left min-w-0">
              <div className="text-xs font-medium text-slate-200 truncate">{currentClient.name}</div>
              <div className="text-[9px] font-mono text-slate-500 truncate">{currentClient.niche}</div>
            </div>
          </div>
          {showClients ? <ChevronDown className="w-3 h-3 text-slate-500 flex-shrink-0" /> : <ChevronRight className="w-3 h-3 text-slate-500 flex-shrink-0" />}
        </button>
        {showClients && (
          <div className="mt-1 space-y-0.5">
            {CLIENTS.map((cl) => (
              <button
                key={cl.id}
                onClick={() => { setClient(cl); setShowClients(false); }}
                className={`flex items-center gap-2 w-full px-3 py-1.5 rounded-md text-xs transition-colors text-left ${
                  cl.id === currentClient.id
                    ? "bg-platform-900/30 text-platform-300"
                    : "text-slate-400 hover:bg-surface-border hover:text-slate-200"
                }`}
              >
                <div className="w-5 h-5 rounded bg-surface-darker flex items-center justify-center text-[8px] font-bold text-slate-400 flex-shrink-0">
                  {cl.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate">{cl.name}</div>
                  <div className="text-[9px] text-slate-600 truncate">{cl.niche}</div>
                </div>
                {cl.id === currentClient.id && <Check className="w-3 h-3 text-platform-400 flex-shrink-0" />}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 px-3 py-1 space-y-0.5 overflow-y-auto">
        {BUSINESS_NAV.map((item) => (
          <NavItem key={item.href} {...item} active={pathname === item.href} />
        ))}

        <div className="pt-4 mt-4 border-t border-surface-border/50">
          <button
            onClick={() => setShowSystem(!showSystem)}
            className="flex items-center justify-between w-full px-3 py-1.5 text-[10px] font-mono text-slate-600 uppercase tracking-wider hover:text-slate-400 transition-colors"
          >
            <span>System</span>
            {showSystem ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </button>
          {showSystem && (
            <div className="mt-1 space-y-0.5">
              {SYSTEM_NAV.map((item) => (
                <NavItem key={item.href} {...item} active={pathname === item.href} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="p-4 border-t border-surface-border">
        <div className="flex items-center gap-2.5 px-2">
          <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-medium text-slate-300">
            OP
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-slate-300">Operator</span>
            <span className="text-[10px] text-slate-600">Local Dev</span>
          </div>
        </div>
        <div className="mt-2 px-2 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
          <span className="text-[8px] font-mono text-amber-500 uppercase tracking-wider">Demo Mode — Some data simulated</span>
        </div>
      </div>
    </div>
  );
}

function NavItem({ href, icon, label, active }: { href: string; icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 px-3 py-1.5 rounded-md transition-colors text-sm",
        active
          ? "bg-platform-900/30 text-platform-300 border border-platform-500/10"
          : "text-slate-400 hover:bg-surface-border hover:text-slate-200",
      )}
    >
      <span className={cn("flex-shrink-0", active ? "text-platform-400" : "text-slate-500")}>{icon}</span>
      <span>{label}</span>
    </Link>
  );
}
