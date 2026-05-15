"use client";

import { MapPin, Building2, Plus, Loader2, Search, CheckCircle2, XCircle, Clock, AlertTriangle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { useCommandCenter } from "@/hooks/use-command-center";

export default function CitationsPage() {
  const { openCommand } = useCommandCenter();
  // Citation engine has no backend API yet — display operational empty state
  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">LOCAL_PRESENCE</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Citation & Listing Engine</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => openCommand('citation_submission')}
            className="px-4 py-2 bg-platform-500 hover:bg-platform-400 text-white rounded-lg text-sm font-mono font-bold transition-colors shadow-lg shadow-platform-500/20"
          >
            NEW_SUBMISSION
          </button>
        </div>
      </div>

      {/* Operational Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="glass-panel p-5 flex flex-col justify-center items-center">
          <p className="text-sm font-mono text-slate-400 uppercase mb-2">Total Citations</p>
          <p className="text-4xl font-bold text-slate-100 font-mono">0</p>
        </div>

        <div className="glass-panel p-5 flex flex-col justify-center items-center">
          <p className="text-sm font-mono text-slate-400 uppercase mb-2">NAP Consistency</p>
          <div className="flex items-end gap-1">
            <p className="text-4xl font-bold text-slate-500 font-mono">—</p>
          </div>
        </div>

        <div className="glass-panel p-5 flex flex-col justify-center items-center">
          <p className="text-sm font-mono text-slate-400 uppercase mb-2">Pending Submissions</p>
          <p className="text-4xl font-bold text-slate-100 font-mono">0</p>
        </div>
      </div>

      {/* Empty State */}
      <div className="flex-1 glass-panel overflow-hidden flex flex-col items-center justify-center p-12 text-center">
        <div className="w-16 h-16 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-4">
          <MapPin className="text-slate-600" size={32} />
        </div>
        <h3 className="text-lg font-medium text-slate-300 font-mono">No Citations Configured</h3>
        <p className="text-sm text-slate-500 mt-2 max-w-md">
          Add a client and configure their canonical business profile to begin automated citation submission across local directories.
        </p>

      </div>
    </div>
  );
}
