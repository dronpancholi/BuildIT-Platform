"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { useApiList, useApiCreate, useApiDelete } from "@/services/hooks";
import { ENDPOINTS } from "@/services/endpoints";
import { toast } from "sonner";
import {
  FileText, Plus, Trash2, Copy, Eye,
  CheckCircle2, Clock, TrendingUp, Search, X
} from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface Template {
  id: string;
  title: string;
  subject: string;
  body: string;
  category: string;
  variables: string[];
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

interface CreateTemplateInput {
  title: string;
  category: string;
  subject: string;
  body: string;
  variables?: string[];
}

interface DuplicateResponse {
  success: boolean;
  message: string;
}

const CATEGORY_OPTIONS = [
  { value: "outreach", label: "Outreach" },
  { value: "guest_post", label: "Guest Post" },
  { value: "link_insertion", label: "Link Insertion" },
  { value: "partnership", label: "Partnership" },
  { value: "followup", label: "Follow-up" },
  { value: "report", label: "Report" },
];

export default function TemplateLibrary() {
  const queryClient = useQueryClient();
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [formData, setFormData] = useState<CreateTemplateInput>({
    title: "",
    category: "outreach",
    subject: "",
    body: "",
  });

  const { data: templates = [], isLoading } = useApiList<Template>(
    ENDPOINTS.COMMUNICATION_TEMPLATES,
    { include_archived: false }
  );

  const createMutation = useApiCreate<{ success: boolean; message: string }, CreateTemplateInput>(
    ENDPOINTS.COMMUNICATION_TEMPLATES,
    {
      invalidateKeys: [ENDPOINTS.COMMUNICATION_TEMPLATES],
      successMessage: "Template created successfully",
    }
  );

  const deleteMutation = useApiDelete(
    ENDPOINTS.COMMUNICATION_TEMPLATES,
    {
      invalidateKeys: [ENDPOINTS.COMMUNICATION_TEMPLATES],
      successMessage: "Template archived",
    }
  );

  const duplicateMutation = useMutation<DuplicateResponse, Error, string>({
    mutationFn: (templateId: string) =>
      fetchApi<DuplicateResponse>(`${ENDPOINTS.COMMUNICATION_TEMPLATES}/${templateId}/duplicate`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.COMMUNICATION_TEMPLATES] });
      toast.success("Template duplicated");
    },
    onError: (e: Error) => toast.error(e.message || "Duplicate failed"),
  });

  const categories = ["all", ...Array.from(new Set(safeArr<Template>(templates).map((t) => t.category)))];

  const filteredTemplates = safeArr<Template>(templates).filter((template) => {
    const matchesSearch = !searchQuery ||
      safeLower(template.title, "").includes(safeLower(searchQuery, "")) ||
      safeLower(template.subject, "").includes(safeLower(searchQuery, ""));

    const matchesCategory = categoryFilter === "all" || template.category === categoryFilter;

    return matchesSearch && matchesCategory;
  });

  const handleUseTemplate = () => {
    setSelectedTemplate(null);
  };

  const handleCreate = async () => {
    if (!formData.title || !formData.subject || !formData.body) {
      toast.error("Title, subject, and body are required");
      return;
    }
    try {
      await createMutation.mutateAsync(formData);
      setIsCreating(false);
      setFormData({ title: "", category: "outreach", subject: "", body: "" });
    } catch {
      // toast handled by hook
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Email Templates</h1>
          <p className="text-slate-400 mt-1">Reusable email templates with performance tracking</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> New Template
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Total Templates
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{safeArr<Template>(templates).length}</p>
        </div>
        <div className="glass-panel p-4 border-emerald-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-500 uppercase mb-2">
            <CheckCircle2 className="w-3.5 h-3.5" /> In Use
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">
            {safeArr<Template>(templates).filter((t) => !t.is_archived).length}
          </p>
        </div>
        <div className="glass-panel p-4 border-platform-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-platform-500 uppercase mb-2">
            <TrendingUp className="w-3.5 h-3.5" /> Categories
          </div>
          <p className="text-2xl font-bold font-mono text-platform-400">{categories.length - 1}</p>
        </div>
        <div className="glass-panel p-4 border-amber-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-amber-500 uppercase mb-2">
            <Clock className="w-3.5 h-3.5" /> Variables Tracked
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400">
            {safeArr<Template>(templates).reduce((sum, t) => sum + (t.variables?.length || 0), 0)}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-panel overflow-hidden">
        <div className="p-4 flex items-center gap-3 border-b border-surface-border">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-300 focus:outline-none focus:border-platform-500"
          >
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat === "all" ? "All Categories" : cat.replace(/_/g, " ").toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        {/* Template List */}
        <div className="p-4">
          {isLoading ? (
            <div className="text-center p-8">
              <FileText className="w-12 h-12 text-platform-500 animate-spin mx-auto mb-3" />
              <p className="text-xs font-mono text-slate-500">Loading templates...</p>
            </div>
          ) : safeArr<Template>(filteredTemplates).length === 0 ? (
            <div className="text-center p-12 glass-panel">
              <FileText className="w-16 h-16 text-slate-700 mx-auto mb-4" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Templates Found</h3>
              <p className="text-xs text-slate-500 mb-4">
                {searchQuery || categoryFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Create your first email template to get started"}
              </p>
              {!searchQuery && categoryFilter === "all" && (
                <button
                  onClick={() => setIsCreating(true)}
                  className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors"
                >
                  Create Template
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {safeArr<Template>(filteredTemplates).map((template) => (
                <div key={template.id} className="glass-panel p-4 hover:bg-surface-border/20 transition-all">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-bold font-mono text-slate-200 truncate">{template.title}</h3>
                      <p className="text-[10px] font-mono text-slate-500 truncate mt-1">{template.subject}</p>
                    </div>
                    <button
                      onClick={() => setSelectedTemplate(template)}
                      className="p-1 hover:bg-surface-border rounded transition-colors"
                    >
                      <Eye className="w-4 h-4 text-slate-400" />
                    </button>
                  </div>

                  {/* Preview */}
                  <div className="p-3 bg-slate-900 rounded mb-3 max-h-24 overflow-y-auto">
                    <div
                      className="text-[10px] text-slate-400 prose prose-invert prose-sm"
                      dangerouslySetInnerHTML={{ __html: (template.body || "").substring(0, 200) }}
                    />
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-3 text-[10px] font-mono text-slate-600 mb-3">
                    <span className="flex items-center gap-1">
                      <Copy className="w-3 h-3" />
                      {template.variables?.length || 0} vars
                    </span>
                    <span className="flex items-center gap-1 text-slate-500">
                      {template.category.replace(/_/g, " ").toUpperCase()}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleUseTemplate}
                      className="flex-1 px-3 py-1.5 bg-platform-600/20 hover:bg-platform-600/30 text-platform-400 border border-platform-500/20 rounded text-xs font-mono transition-colors"
                    >
                      Use Template
                    </button>
                    <button
                      onClick={() => duplicateMutation.mutate(template.id)}
                      disabled={duplicateMutation.isPending}
                      className="p-1.5 hover:bg-surface-border rounded transition-colors disabled:opacity-50"
                      title="Duplicate"
                    >
                      <Copy className="w-4 h-4 text-slate-400" />
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(template.id)}
                      disabled={deleteMutation.isPending}
                      className="p-1.5 hover:bg-red-500/10 rounded transition-colors disabled:opacity-50"
                    >
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Template Detail Modal */}
      {selectedTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">{selectedTemplate.title}</h2>
                <p className="text-sm text-slate-400">{selectedTemplate.subject}</p>
              </div>
              <button
                onClick={() => setSelectedTemplate(null)}
                className="p-2 hover:bg-surface-border rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <div className="space-y-4">
                <div className="glass-panel p-4">
                  <h4 className="text-xs font-bold font-mono text-slate-400 uppercase mb-2">Subject</h4>
                  <p className="text-sm text-slate-200">{selectedTemplate.subject}</p>
                </div>

                <div className="glass-panel p-4">
                  <h4 className="text-xs font-bold font-mono text-slate-400 uppercase mb-2">Body</h4>
                  <div
                    className="prose prose-invert prose-sm max-w-none text-slate-300"
                    dangerouslySetInnerHTML={{ __html: selectedTemplate.body }}
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="glass-panel p-3">
                    <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Category</div>
                    <p className="text-xs font-mono text-slate-300">
                      {selectedTemplate.category.replace(/_/g, " ").toUpperCase()}
                    </p>
                  </div>
                  <div className="glass-panel p-3">
                    <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Variables</div>
                    <p className="text-xs font-mono text-slate-300">
                      {selectedTemplate.variables?.length || 0}
                    </p>
                  </div>
                  <div className="glass-panel p-3">
                    <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Updated</div>
                    <p className="text-xs font-mono text-slate-300">
                      {selectedTemplate.updated_at?.split("T")[0] || "—"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
              <button
                onClick={() => setSelectedTemplate(null)}
                className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors"
              >
                Close
              </button>
              <button
                onClick={handleUseTemplate}
                className="flex-1 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors"
              >
                Use This Template
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Template Modal */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">Create New Template</h2>
                <p className="text-sm text-slate-400">Create a reusable email template</p>
              </div>
              <button
                onClick={() => setIsCreating(false)}
                className="p-2 hover:bg-surface-border rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Template Name</label>
                  <input
                    type="text"
                    placeholder="e.g., Guest Post Outreach - Initial"
                    value={formData.title}
                    onChange={(e) => setFormData((f) => ({ ...f, title: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData((f) => ({ ...f, category: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                  >
                    {CATEGORY_OPTIONS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Subject Line</label>
                  <input
                    type="text"
                    placeholder="Enter subject line..."
                    value={formData.subject}
                    onChange={(e) => setFormData((f) => ({ ...f, subject: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Email Body (HTML)</label>
                  <textarea
                    placeholder="Enter email body HTML..."
                    rows={10}
                    value={formData.body}
                    onChange={(e) => setFormData((f) => ({ ...f, body: e.target.value }))}
                    className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500 font-mono"
                  />
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
              <button
                onClick={() => setIsCreating(false)}
                className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createMutation.isPending}
                className="flex-1 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {createMutation.isPending ? "Creating..." : "Create Template"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
