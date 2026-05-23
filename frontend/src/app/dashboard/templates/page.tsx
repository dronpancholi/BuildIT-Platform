"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { 
  FileText, Plus, Edit2, Trash2, Copy, Eye, 
  CheckCircle2, Clock, TrendingUp, Search, X
} from "lucide-react";

interface Template {
  id: string;
  name: string;
  subject: string;
  body_html: string;
  category: string;
  usage_count: number;
  avg_reply_rate: number;
  created_at: string;
  updated_at: string;
}

export default function TemplateLibrary() {
  const queryClient = useQueryClient();
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  // Fetch templates
  const { data: templates = [], isLoading } = useQuery<Template[]>({
    queryKey: ["email-templates"],
    queryFn: async () => {
      // Placeholder - would use real template endpoint
      return [];
    },
  });

  const categories = ["all", ...Array.from(new Set(templates.map(t => t.category)))];

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = !searchQuery || 
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.subject.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesCategory = categoryFilter === "all" || template.category === categoryFilter;
    
    return matchesSearch && matchesCategory;
  });

  const createTemplateMutation = useMutation({
    mutationFn: async (template: Omit<Template, "id" | "created_at" | "updated_at" | "usage_count" | "avg_reply_rate">) => {
      // Placeholder - would use real create template endpoint
      return template;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      setIsCreating(false);
    },
  });

  const deleteTemplateMutation = useMutation({
    mutationFn: async (templateId: string) => {
      // Placeholder - would use real delete template endpoint
      return templateId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-templates"] });
      setSelectedTemplate(null);
    },
  });

  const handleUseTemplate = (template: Template) => {
    // Would open compose window with template content
    console.log("Using template:", template);
    setSelectedTemplate(null);
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
          <p className="text-2xl font-bold font-mono text-slate-100">{templates.length}</p>
        </div>
        <div className="glass-panel p-4 border-emerald-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-500 uppercase mb-2">
            <CheckCircle2 className="w-3.5 h-3.5" /> Avg Reply Rate
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">
            {templates.length > 0 
              ? (templates.reduce((sum, t) => sum + t.avg_reply_rate, 0) / templates.length * 100).toFixed(1) + "%"
              : "0%"}
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
            <Clock className="w-3.5 h-3.5" /> Total Uses
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400">
            {templates.reduce((sum, t) => sum + t.usage_count, 0)}
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
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat === "all" ? "All Categories" : cat.replace("_", " ").toUpperCase()}
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
          ) : filteredTemplates.length === 0 ? (
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
              {filteredTemplates.map((template) => (
                <div key={template.id} className="glass-panel p-4 hover:bg-surface-border/20 transition-all">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-bold font-mono text-slate-200 truncate">{template.name}</h3>
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
                      dangerouslySetInnerHTML={{ __html: template.body_html.substring(0, 200) }}
                    />
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-3 text-[10px] font-mono text-slate-600 mb-3">
                    <span className="flex items-center gap-1">
                      <Copy className="w-3 h-3" />
                      {template.usage_count} uses
                    </span>
                    <span className="flex items-center gap-1 text-emerald-500">
                      <TrendingUp className="w-3 h-3" />
                      {(template.avg_reply_rate * 100).toFixed(1)}% reply
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleUseTemplate(template)}
                      className="flex-1 px-3 py-1.5 bg-platform-600/20 hover:bg-platform-600/30 text-platform-400 border border-platform-500/20 rounded text-xs font-mono transition-colors"
                    >
                      Use Template
                    </button>
                    <button className="p-1.5 hover:bg-surface-border rounded transition-colors">
                      <Edit2 className="w-4 h-4 text-slate-400" />
                    </button>
                    <button
                      onClick={() => deleteTemplateMutation.mutate(template.id)}
                      className="p-1.5 hover:bg-red-500/10 rounded transition-colors"
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
                <h2 className="text-xl font-bold text-slate-100">{selectedTemplate.name}</h2>
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
                    dangerouslySetInnerHTML={{ __html: selectedTemplate.body_html }}
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="glass-panel p-3">
                    <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Category</div>
                    <p className="text-xs font-mono text-slate-300">{selectedTemplate.category}</p>
                  </div>
                  <div className="glass-panel p-3">
                    <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Usage</div>
                    <p className="text-xs font-mono text-slate-300">{selectedTemplate.usage_count} times</p>
                  </div>
                  <div className="glass-panel p-3">
                    <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Reply Rate</div>
                    <p className="text-xs font-mono text-emerald-400">{(selectedTemplate.avg_reply_rate * 100).toFixed(1)}%</p>
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
                onClick={() => handleUseTemplate(selectedTemplate)}
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
                    className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Category</label>
                  <select className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500">
                    <option value="outreach">Outreach</option>
                    <option value="follow-up">Follow-up</option>
                    <option value="guest-post">Guest Post</option>
                    <option value="resource-page">Resource Page</option>
                    <option value="broken-link">Broken Link</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Subject Line</label>
                  <input
                    type="text"
                    placeholder="Enter subject line..."
                    className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Email Body</label>
                  <textarea
                    placeholder="Enter email body HTML..."
                    rows={10}
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
                onClick={() => {
                  // Would call create mutation
                  setIsCreating(false);
                }}
                className="flex-1 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors"
              >
                Create Template
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}