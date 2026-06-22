"use client";

import { useState, useRef, useEffect } from "react";
import { VariableDefinition, getVariableByCategory } from "@/lib/merge-variables";
import { Button } from "@/components/ui/button";
import { AtSign, ChevronRight, Search } from "lucide-react";
import { safeArr, safeLower } from "@/lib/safe";

interface VariableInsertMenuProps {
  onInsert: (variableName: string) => void;
}

export function VariableInsertMenu({ onInsert }: VariableInsertMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);

  const grouped = getVariableByCategory();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleInsert = (name: string) => {
    onInsert(name);
    setIsOpen(false);
    setSearchQuery("");
  };

  const filtered: Record<string, VariableDefinition[]> = {};
  for (const [category, vars] of Object.entries(grouped)) {
    const matched = safeArr<VariableDefinition>(vars).filter(
      (v) =>
        safeLower(v.name, "").includes(safeLower(searchQuery, "")) ||
        safeLower(v.label, "").includes(safeLower(searchQuery, ""))
    );
    if (matched.length > 0) filtered[category] = matched;
  }

  return (
    <div ref={menuRef} className="relative">
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="h-8 border-platform-500/50 text-platform-400 hover:bg-platform-500/10 text-xs gap-1"
      >
        <AtSign className="w-3.5 h-3.5" />
        Insert Variable
      </Button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-surface-card border border-surface-border rounded-lg shadow-xl z-50 max-h-96 overflow-hidden flex flex-col">
          <div className="p-2 border-b border-surface-border">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search variables..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-surface-darker border border-surface-border rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
              />
            </div>
          </div>

          <div className="overflow-y-auto flex-1 p-1">
            {Object.entries(filtered).length === 0 ? (
              <div className="text-xs text-slate-500 text-center py-4">
                No variables found
              </div>
            ) : (
              Object.entries(filtered).map(([category, vars]) => (
                <div key={category}>
                  <div className="flex items-center gap-1 px-3 py-1.5 text-[10px] font-mono text-slate-600 uppercase tracking-wide">
                    <ChevronRight className="w-3 h-3" />
                    {category}
                  </div>
                  {vars.map((v) => (
                    <button
                      key={v.name}
                      onClick={() => handleInsert(v.name)}
                      className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-surface-border rounded transition-colors group"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-platform-400 font-mono">
                          {`{{${v.name}}}`}
                        </span>
                      </div>
                      <span className="text-slate-500 group-hover:text-slate-400 text-[10px]">
                        {v.label}
                      </span>
                    </button>
                  ))}
                </div>
              ))
            )}
          </div>

          <div className="p-2 border-t border-surface-border text-[10px] text-slate-600 text-center">
            Click to insert merge variable at cursor
          </div>
        </div>
      )}
    </div>
  );
}
