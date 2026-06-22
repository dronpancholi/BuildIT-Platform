"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, Info } from "lucide-react";

interface PageGuideProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}

export function PageGuide({ title, children, defaultOpen = false }: PageGuideProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-platform-500/20 bg-platform-500/5 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-4 py-2.5 text-left text-xs font-mono text-slate-400 hover:text-slate-300 transition-colors"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5 text-platform-400" /> : <ChevronRight className="w-3.5 h-3.5 text-platform-400" />}
        <Info className="w-3.5 h-3.5 text-platform-400" />
        <span>{title}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 text-sm text-slate-400 leading-relaxed space-y-2">
          {children}
        </div>
      )}
    </div>
  );
}
