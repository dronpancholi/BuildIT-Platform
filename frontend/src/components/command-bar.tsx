"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api";
import {
  Search, Command, Users, GitBranch, FileText, Mail, CheckCircle2,
  Zap, TrendingUp, AlertTriangle, FolderOpen, Plus, X,
  Layers, UserPlus, BarChart3, MessageSquare
} from "lucide-react";

interface SearchResult {
  id: string;
  label: string;
  subtitle: string;
  type: string;
  path: string;
}

interface CommandAction {
  id: string;
  label: string;
  icon: any;
  path: string;
  group: string;
}

const TYPE_ICONS: Record<string, any> = {
  customer: Users, campaign: GitBranch, keyword: Search, prospect: Users,
  email: Mail, draft: FileText, template: FileText, approval: CheckCircle2,
  report: FileText, automation: Zap, execution: TrendingUp, alert: AlertTriangle,
};

const TYPE_LABELS: Record<string, string> = {
  customer: "Customers", campaign: "Campaigns", keyword: "Keywords",
  email: "Emails", draft: "Drafts", template: "Templates",
  approval: "Approvals", report: "Reports", automation: "Rules",
  execution: "Runs", alert: "Alerts", prospect: "Prospects",
};

const COMMANDS: CommandAction[] = [
  { id: "create_campaign", label: "Create Campaign", icon: Plus, path: "/dashboard/campaigns", group: "Actions" },
  { id: "add_client", label: "Add Customer", icon: UserPlus, path: "/dashboard/clients", group: "Actions" },
  { id: "compose_email", label: "Compose Email", icon: MessageSquare, path: "/dashboard/communications", group: "Actions" },
  { id: "create_report", label: "Create Report", icon: BarChart3, path: "/dashboard/reports", group: "Actions" },
  { id: "executive", label: "Open Executive Center", icon: BarChart3, path: "/dashboard/executive", group: "Navigate" },
  { id: "automation", label: "Open Automation Dashboard", icon: Zap, path: "/dashboard/automation", group: "Navigate" },
  { id: "communications", label: "Open Communication Hub", icon: Mail, path: "/dashboard/communications", group: "Navigate" },
  { id: "portfolio", label: "Open Campaign Portfolio", icon: GitBranch, path: "/dashboard/portfolio", group: "Navigate" },
];

export function CommandBar() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  useEffect(() => {
    const stored = localStorage.getItem("commandBar:recent");
    if (stored) {
      try { setRecentSearches(JSON.parse(stored)); } catch {}
    }
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((p) => !p);
        setQuery("");
        setSelectedIndex(0);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
        setQuery("");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    if (query && !recentSearches.includes(query)) {
      const updated = [query, ...recentSearches.filter((s) => s !== query)].slice(0, 10);
      setRecentSearches(updated);
      localStorage.setItem("commandBar:recent", JSON.stringify(updated));
    }
  }, [query]);

  const { data, isLoading } = useQuery<any>({
    queryKey: ["global-search", query],
    queryFn: () => fetchApi(`/search/global?q=${encodeURIComponent(query)}&tenant_id=${tid}&limit=10`),
    enabled: query.length >= 2,
    staleTime: 15000,
  });

  const searchResults: SearchResult[] = data?.data?.results || [];
  const showCommands = query.length < 2;

  const groupedResults = searchResults.reduce<Record<string, SearchResult[]>>((acc, r) => {
    const group = TYPE_LABELS[r.type] || r.type;
    if (!acc[group]) acc[group] = [];
    if (acc[group].length < 5) acc[group].push(r);
    return acc;
  }, {});

  const allItems = showCommands
    ? COMMANDS
    : Object.entries(groupedResults).flatMap(([group, items]) =>
        [{ _type: "_group", group } as any, ...items]
      );

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, allItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = allItems[selectedIndex];
      if (!item?._type) {
        if (item.path) {
          router.push(item.path);
          setOpen(false);
        }
      }
    }
  }, [allItems, selectedIndex, router]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const el = listRef.current.children[selectedIndex] as HTMLElement;
      el?.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => { setOpen(false); setQuery(""); }}
      />
      <div className="relative w-full max-w-xl bg-surface-card border border-surface-border rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-surface-border">
          <Search className="w-4 h-4 text-slate-500 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search customers, campaigns, keywords, reports..."
            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-600 focus:outline-none font-mono"
          />
          {isLoading && (
            <div className="w-4 h-4 border-2 border-platform-500 border-t-transparent rounded-full animate-spin" />
          )}
          <button
            onClick={() => { setOpen(false); setQuery(""); }}
            className="p-1 hover:bg-surface-border rounded transition-colors"
          >
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>

        <div ref={listRef} className="max-h-[60vh] overflow-y-auto divide-y divide-surface-border" onKeyDown={handleKeyDown}>
          {showCommands ? (
            <>
              {recentSearches.length > 0 && (
                <div className="px-3 py-2">
                  <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider px-2 mb-1">Recent</div>
                  {recentSearches.slice(0, 5).map((s, i) => (
                    <button
                      key={s}
                      onClick={() => setQuery(s)}
                      className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-mono text-slate-400 hover:bg-surface-border rounded transition-colors"
                    >
                      <Search className="w-3 h-3" />
                      {s}
                    </button>
                  ))}
                </div>
              )}
              {(["Actions", "Navigate"] as const).map((group) => (
                <div key={group} className="px-3 py-2">
                  <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider px-2 mb-1">{group}</div>
                  {COMMANDS.filter((c) => c.group === group).map((cmd, i) => {
                    const idx = (group === "Actions" ? 0 : recentSearches.length) + i;
                    const Icon = cmd.icon;
                    return (
                      <button
                        key={cmd.id}
                        onClick={() => { router.push(cmd.path); setOpen(false); }}
                        className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs font-mono rounded transition-colors ${
                          selectedIndex === idx ? "bg-platform-600/20 text-platform-300" : "text-slate-400 hover:bg-surface-border"
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                        {cmd.label}
                      </button>
                    );
                  })}
                </div>
              ))}
            </>
          ) : query.length >= 2 && searchResults.length === 0 && !isLoading ? (
            <div className="p-6 text-center text-xs font-mono text-slate-500">No results found</div>
          ) : (
            Object.entries(groupedResults).map(([group, items]) => (
              <div key={group} className="px-3 py-2">
                <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider px-2 mb-1">{group}</div>
                {items.map((item) => {
                  const Icon = TYPE_ICONS[item.type] || Search;
                  const idx = Object.values(groupedResults).flat().indexOf(item);
                  return (
                    <button
                      key={item.id}
                      onClick={() => { router.push(item.path); setOpen(false); }}
                      className={`w-full flex items-center gap-3 px-2 py-2 rounded transition-colors ${
                        selectedIndex === idx ? "bg-platform-600/20" : "hover:bg-surface-border"
                      }`}
                    >
                      <div className="p-1 rounded bg-platform-600/10 border border-platform-500/20">
                        <Icon className="w-3.5 h-3.5 text-platform-400" />
                      </div>
                      <div className="flex-1 text-left min-w-0">
                        <p className="text-sm font-mono text-slate-200 truncate">
                          {item.label}
                        </p>
                        <p className="text-[10px] font-mono text-slate-500 truncate">{item.subtitle}</p>
                      </div>
                      <span className="text-[10px] font-mono text-slate-600 uppercase flex-shrink-0">{item.type}</span>
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div className="px-4 py-2 border-t border-surface-border bg-surface-darker/50 flex items-center gap-4 text-[10px] font-mono text-slate-600">
          <span className="flex items-center gap-1"><Command className="w-3 h-3" />K <span className="text-slate-700">open</span></span>
          <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-surface-border text-[9px]">↑↓</kbd> navigate</span>
          <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-surface-border text-[9px]">↵</kbd> select</span>
          <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 rounded bg-surface-border text-[9px]">esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
