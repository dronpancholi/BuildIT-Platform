"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { X, Search, Users, GitBranch, Mail, FileText, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface GlobalSearchProps {
  onClose: () => void;
}

interface SearchResult {
  type: "customer" | "campaign" | "email" | "approval" | "report";
  items: any[];
}

export function GlobalSearch({ onClose }: GlobalSearchProps) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data, isLoading } = useQuery<any>({
    queryKey: ["global-search", debouncedQuery],
    queryFn: () => fetchApi(`/search?q=${encodeURIComponent(debouncedQuery)}`),
    enabled: debouncedQuery.length > 0,
  });

  const results: SearchResult[] = data?.data || [];

  const hasResults = results.some((group: any) => group.items.length > 0);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "customer":
        return <Users className="w-4 h-4" />;
      case "campaign":
        return <GitBranch className="w-4 h-4" />;
      case "email":
        return <Mail className="w-4 h-4" />;
      case "approval":
        return <AlertCircle className="w-4 h-4" />;
      case "report":
        return <FileText className="w-4 h-4" />;
      default:
        return <Search className="w-4 h-4" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-surface-card border border-surface-border rounded-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 p-4 border-b border-surface-border">
          <Search className="w-5 h-5 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search customers, campaigns, emails, approvals, reports..."
            className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-surface-darker text-slate-400 hover:text-slate-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-platform-500"></div>
            </div>
          ) : debouncedQuery.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              Start typing to search across all customers, campaigns, and communications
            </div>
          ) : !hasResults ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              No results found for "{debouncedQuery}"
            </div>
          ) : (
            <div className="space-y-4">
              {results.map(
                (group: any) =>
                  group.items.length > 0 && (
                    <div key={group.type} className="space-y-2">
                      <div className="flex items-center gap-2 text-xs font-medium text-slate-500 uppercase">
                        {getTypeIcon(group.type)}
                        {group.type}
                        <span className="text-slate-600">({group.items.length})</span>
                      </div>
                      <div className="space-y-1">
                        {group.items.slice(0, 5).map((item: any) => (
                          <div
                            key={item.id}
                            className="p-3 rounded-lg bg-surface-darker hover:bg-platform-500/10 transition-colors cursor-pointer"
                          >
                            <div className="text-sm font-medium text-slate-200">
                              {item.name || item.title || item.subject}
                            </div>
                            {item.description && (
                              <div className="text-xs text-slate-500 mt-1 truncate">
                                {item.description}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-surface-border text-xs text-slate-500">
          <span>Press ESC to close</span>
          <div className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 bg-surface-darker rounded">↑↓</kbd>
            <span>Navigate</span>
            <kbd className="px-1.5 py-0.5 bg-surface-darker rounded">↵</kbd>
            <span>Select</span>
          </div>
        </div>
      </div>
    </div>
  );
}
