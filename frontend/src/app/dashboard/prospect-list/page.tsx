"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { 
  Users, Search, Download, Filter, Check, X, 
  Mail, Link2, TrendingUp, Star, ChevronDown,
  Eye, Edit2, Trash2, Plus, ArrowRight
} from "lucide-react";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { safeArr, safeNum, safeLower, safeFixed } from "@/lib/safe";

interface Prospect {
  id: string;
  domain: string;
  email: string;
  name: string;
  company: string;
  domain_authority: number;
  page_authority: number;
  relevance_score: number;
  composite_score: number;
  status: "new" | "contacted" | "replied" | "converted" | "rejected";
  campaign_id: string;
  campaign_name: string;
  last_contacted: string | null;
  notes: string;
  tags: string[];
  created_at: string;
}

export default function ProspectListPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [minDA, setMinDA] = useState<number>(0);
  const [selectedProspects, setSelectedProspects] = useState<string[]>([]);
  const [showExportModal, setShowExportModal] = useState(false);
  const [selectedProspect, setSelectedProspect] = useState<Prospect | null>(null);

  const { data: prospects = [], isLoading } = useQuery<Prospect[]>({
    queryKey: ["prospects-list", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/prospects?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 30000,
  });

  const filteredProspects = useMemo(() => {
    return prospects.filter((p) => {
      const lowerSearch = safeLower(searchQuery, "");
      const matchesSearch = !searchQuery ||
        safeLower(p.domain, "").includes(lowerSearch) ||
        safeLower(p.name, "").includes(lowerSearch) ||
        safeLower(p.company, "").includes(lowerSearch);

      const matchesStatus = statusFilter === "all" || p.status === statusFilter;
      const matchesDA = safeNum(p.domain_authority) >= minDA;

      return matchesSearch && matchesStatus && matchesDA;
    });
  }, [prospects, searchQuery, statusFilter, minDA]);

  const toggleSelect = (id: string) => {
    setSelectedProspects(prev => 
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedProspects.length === filteredProspects.length) {
      setSelectedProspects([]);
    } else {
      setSelectedProspects(filteredProspects.map(p => p.id));
    }
  };

  const exportData = {
    total: prospects.length,
    filtered: filteredProspects.length,
    selected: selectedProspects.length,
  };

  const getStatusColor = (status: string) => {
    const colors = {
      new: "bg-slate-500/10 text-slate-400 border-slate-500/20",
      contacted: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      replied: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      converted: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    return colors[status as keyof typeof colors] || colors.new;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Prospects</h1>
          <p className="text-slate-400 mt-1">Manage and export your prospect database</p>
        </div>
        <div className="flex items-center gap-3">
          {selectedProspects.length > 0 && (
            <span className="px-3 py-1.5 bg-platform-500/10 border border-platform-500/30 rounded-md text-xs font-mono text-platform-400">
              {selectedProspects.length} selected
            </span>
          )}
          <button
            onClick={() => setShowExportModal(true)}
            className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center gap-2"
          >
            <Download className="w-4 h-4" /> Export
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Users className="w-3.5 h-3.5" /> Total Prospects
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{prospects.length}</p>
        </div>
        <div className="glass-panel p-4 border-emerald-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-500 uppercase mb-2">
            <Check className="w-3.5 h-3.5" /> Converted
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">
            {prospects.filter(p => p.status === "converted").length}
          </p>
        </div>
        <div className="glass-panel p-4 border-amber-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-amber-500 uppercase mb-2">
            <Mail className="w-3.5 h-3.5" /> Contacted
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400">
            {prospects.filter(p => p.status === "contacted").length}
          </p>
        </div>
        <div className="glass-panel p-4 border-purple-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-purple-500 uppercase mb-2">
            <TrendingUp className="w-3.5 h-3.5" /> Avg DA
          </div>
          <p className="text-2xl font-bold font-mono text-purple-400">
            {prospects.length > 0
              ? Math.round(prospects.reduce((sum, p) => sum + safeNum(p.domain_authority), 0) / prospects.length)
              : 0}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-panel overflow-hidden">
        <div className="p-4 flex items-center gap-3 border-b border-surface-border flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search domains, names, companies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-300 focus:outline-none focus:border-platform-500"
          >
            <option value="all">All Status</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="replied">Replied</option>
            <option value="converted">Converted</option>
            <option value="rejected">Rejected</option>
          </select>
          <div className="flex items-center gap-2">
            <label className="text-xs font-mono text-slate-500">Min DA:</label>
            <input
              type="number"
              min={0}
              max={100}
              value={minDA}
              onChange={(e) => setMinDA(parseInt(e.target.value) || 0)}
              className="w-16 px-2 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-300 focus:outline-none focus:border-platform-500 text-center"
            />
          </div>
          <button
            onClick={() => {
              setSearchQuery("");
              setStatusFilter("all");
              setMinDA(0);
            }}
            className="px-3 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-400 rounded-lg text-xs font-mono transition-colors"
          >
            Clear
          </button>
        </div>

        {/* Prospect Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="text-[10px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
              <tr>
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={selectedProspects.length === filteredProspects.length && filteredProspects.length > 0}
                    onChange={toggleSelectAll}
                    className="rounded bg-slate-800 border-slate-700 text-platform-600 focus:ring-platform-500"
                  />
                </th>
                <th className="px-4 py-3 text-left font-mono">Prospect</th>
                <th className="px-4 py-3 text-left font-mono">Campaign</th>
                <th className="px-4 py-3 text-right font-mono">DA</th>
                <th className="px-4 py-3 text-right font-mono">PA</th>
                <th className="px-4 py-3 text-right font-mono">Relevance</th>
                <th className="px-4 py-3 text-right font-mono">Score</th>
                <th className="px-4 py-3 font-mono">Status</th>
                <th className="px-4 py-3 font-mono">Tags</th>
                <th className="px-4 py-3 w-20"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="px-4 py-12 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-5 h-5 border-2 border-platform-500 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-xs font-mono text-slate-500">Loading prospects...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredProspects.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-12 text-center">
                    <Users className="w-12 h-12 text-slate-700 mx-auto mb-3" />
                    <p className="text-xs font-mono text-slate-500">No prospects found matching your filters.</p>
                  </td>
                </tr>
              ) : (
                filteredProspects.map((prospect) => (
                  <tr
                    key={prospect.id}
                    className={`hover:bg-surface-border/30 transition-colors cursor-pointer ${
                      selectedProspects.includes(prospect.id) ? "bg-platform-500/5" : ""
                    }`}
                    onClick={() => setSelectedProspect(prospect)}
                  >
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedProspects.includes(prospect.id)}
                        onChange={() => toggleSelect(prospect.id)}
                        className="rounded bg-slate-800 border-slate-700 text-platform-600 focus:ring-platform-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-mono text-slate-200">{prospect.domain}</p>
                        <p className="text-[10px] text-slate-500">{prospect.name} @ {prospect.company}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-mono text-platform-400">{prospect.campaign_name}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm">{prospect.domain_authority}</td>
                    <td className="px-4 py-3 text-right font-mono text-sm">{prospect.page_authority}</td>
                    <td className="px-4 py-3 text-right font-mono text-sm">
                      {safeFixed(safeNum(prospect.relevance_score) * 100, 0)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm font-bold text-emerald-400">
                      {safeFixed(safeNum(prospect.composite_score) * 100, 0)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-[9px] font-mono rounded-full border uppercase ${getStatusColor(prospect.status)}`}>
                        {prospect.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {safeArr<string>(prospect.tags).slice(0, 2).map((tag) => (
                          <span key={tag} className="px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded text-[9px] font-mono">
                            {tag}
                          </span>
                        ))}
                        {safeArr<string>(prospect.tags).length > 2 && (
                          <span className="px-1.5 py-0.5 bg-slate-800 text-slate-500 rounded text-[9px] font-mono">
                            +{safeArr<string>(prospect.tags).length - 2}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedProspect(prospect);
                        }}
                        className="p-1 hover:bg-surface-border rounded transition-colors"
                      >
                        <ArrowRight className="w-4 h-4 text-slate-400" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Prospect Detail Modal */}
      {selectedProspect && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">{selectedProspect.domain}</h2>
                <p className="text-sm text-slate-400">{selectedProspect.name} — {selectedProspect.company}</p>
              </div>
              <button
                onClick={() => setSelectedProspect(null)}
                className="p-2 hover:bg-surface-border rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="glass-panel p-4">
                  <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Domain Authority</div>
                  <p className="text-2xl font-bold font-mono text-purple-400">{selectedProspect.domain_authority}</p>
                </div>
                <div className="glass-panel p-4">
                  <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Page Authority</div>
                  <p className="text-2xl font-bold font-mono text-blue-400">{selectedProspect.page_authority}</p>
                </div>
                <div className="glass-panel p-4">
                  <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Relevance Score</div>
                  <p className="text-2xl font-bold font-mono text-amber-400">
                    {safeFixed(safeNum(selectedProspect.relevance_score) * 100, 1)}
                  </p>
                </div>
                <div className="glass-panel p-4 border-emerald-500/20">
                  <div className="text-[10px] font-mono text-emerald-500 uppercase mb-1">Composite Score</div>
                  <p className="text-2xl font-bold font-mono text-emerald-400">
                    {safeFixed(safeNum(selectedProspect.composite_score) * 100, 1)}
                  </p>
                </div>
              </div>

              <div className="glass-panel p-4">
                <h4 className="text-xs font-mono text-slate-400 uppercase mb-2">Contact Info</h4>
                <div className="space-y-1 text-sm">
                  <p className="text-slate-300"><span className="text-slate-500">Email:</span> {selectedProspect.email}</p>
                  <p className="text-slate-300"><span className="text-slate-500">Domain:</span> {selectedProspect.domain}</p>
                  <p className="text-slate-300"><span className="text-slate-500">Company:</span> {selectedProspect.company}</p>
                </div>
              </div>

              <div className="glass-panel p-4">
                <h4 className="text-xs font-mono text-slate-400 uppercase mb-2">Campaign</h4>
                <p className="text-sm text-slate-300">{selectedProspect.campaign_name}</p>
              </div>

              <div className="glass-panel p-4">
                <h4 className="text-xs font-mono text-slate-400 uppercase mb-2">Status</h4>
                <span className={`px-3 py-1 text-xs font-mono rounded-full border uppercase ${getStatusColor(selectedProspect.status)}`}>
                  {selectedProspect.status}
                </span>
              </div>

              <div className="glass-panel p-4">
                <h4 className="text-xs font-mono text-slate-400 uppercase mb-2">Tags</h4>
                <div className="flex flex-wrap gap-1">
                  {safeArr<string>(selectedProspect.tags).map((tag) => (
                    <span key={tag} className="px-2 py-1 bg-slate-800 text-slate-400 rounded text-xs font-mono">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {selectedProspect.notes && (
                <div className="glass-panel p-4">
                  <h4 className="text-xs font-mono text-slate-400 uppercase mb-2">Notes</h4>
                  <p className="text-sm text-slate-300">{selectedProspect.notes}</p>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
              <button
                onClick={() => setSelectedProspect(null)}
                className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors"
              >
                Close
              </button>
              <button className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center gap-2">
                <Mail className="w-4 h-4" /> Send Email
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">Export Prospects</h2>
                <p className="text-sm text-slate-400">Download your prospect data</p>
              </div>
              <button
                onClick={() => setShowExportModal(false)}
                className="p-2 hover:bg-surface-border rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="glass-panel p-4 bg-slate-900/50">
                <h4 className="text-xs font-mono text-slate-400 uppercase mb-3">Export Summary</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Total Prospects:</span>
                    <span className="text-slate-300 font-mono">{exportData.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Filtered Results:</span>
                    <span className="text-slate-300 font-mono">{exportData.filtered}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Selected:</span>
                    <span className="text-platform-400 font-mono">{exportData.selected}</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Export Scope</label>
                <div className="space-y-2">
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-surface-border hover:bg-surface-border/30 cursor-pointer">
                    <input
                      type="radio"
                      name="exportScope"
                      defaultChecked
                      className="text-platform-600 focus:ring-platform-500"
                    />
                    <span className="text-sm text-slate-300">Filtered Results ({exportData.filtered})</span>
                  </label>
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-surface-border hover:bg-surface-border/30 cursor-pointer">
                    <input
                      type="radio"
                      name="exportScope"
                      className="text-platform-600 focus:ring-platform-500"
                    />
                    <span className="text-sm text-slate-300">Selected Only ({exportData.selected})</span>
                  </label>
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-surface-border hover:bg-surface-border/30 cursor-pointer">
                    <input
                      type="radio"
                      name="exportScope"
                      className="text-platform-600 focus:ring-platform-500"
                    />
                    <span className="text-sm text-slate-300">All Prospects ({exportData.total})</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Format</label>
                <div className="space-y-2">
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-platform-500/30 bg-platform-500/10 cursor-pointer">
                    <input
                      type="radio"
                      name="format"
                      defaultChecked
                      className="text-platform-600 focus:ring-platform-500"
                    />
                    <span className="text-sm text-slate-300">CSV (Excel)</span>
                  </label>
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-surface-border hover:bg-surface-border/30 cursor-pointer">
                    <input
                      type="radio"
                      name="format"
                      className="text-platform-600 focus:ring-platform-500"
                    />
                    <span className="text-sm text-slate-300">JSON</span>
                  </label>
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-surface-border hover:bg-surface-border/30 cursor-pointer">
                    <input
                      type="radio"
                      name="format"
                      className="text-platform-600 focus:ring-platform-500"
                    />
                    <span className="text-sm text-slate-300">Excel (.xlsx)</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Fields to Include</label>
                <div className="grid grid-cols-2 gap-2">
                  {["Domain", "Email", "Name", "Company", "DA", "PA", "Score", "Status", "Tags", "Notes"].map((field) => (
                    <label key={field} className="flex items-center gap-2 p-2 rounded bg-slate-900/50">
                      <input type="checkbox" defaultChecked className="rounded bg-slate-800 border-slate-700 text-platform-600 focus:ring-platform-500" />
                      <span className="text-xs text-slate-300">{field}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
              <button
                onClick={() => setShowExportModal(false)}
                className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  // Would trigger actual export
                  setShowExportModal(false);
                }}
                className="flex-1 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" /> Download Export
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}