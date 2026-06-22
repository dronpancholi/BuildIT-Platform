"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { EmailComposer } from "@/components/email/email-composer";
import { TemplateManager } from "@/components/email/template-manager";
import {
  Mail, FileText, Clock, CheckCircle2, AlertTriangle,
  Send, Edit2, Trash2, Filter, Search, Plus,
  ChevronDown, ChevronUp, Paperclip, Calendar, CheckSquare,
  Eye, X, Loader2, Archive, Copy, ExternalLink,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────
interface Draft {
  id: string;
  template_id?: string;
  subject: string;
  body_html: string;
  to_email?: string;
  variables?: Record<string, string>;
  status: string;
  created_at: string;
  updated_at: string;
}

interface Template {
  id: string;
  title: string;
  category: string;
  subject: string;
  body: string;
  variables: string[];
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

interface ScheduledEmail {
  id: string;
  thread_id: string;
  subject: string;
  to_email: string;
  scheduled_at: string;
  status: string;
  created_at: string;
}

// ── Helpers ────────────────────────────────────────────
const statusConfig: Record<string, { color: string; label: string; icon: any }> = {
  draft: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20", label: "DRAFT", icon: FileText },
  pending: { color: "bg-blue-500/10 text-blue-400 border-blue-500/20", label: "PENDING", icon: Clock },
  sent: { color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20", label: "SENT", icon: Send },
  cancelled: { color: "bg-red-500/10 text-red-400 border-red-500/20", label: "CANCELLED", icon: X },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = statusConfig[status] || statusConfig.draft;
  const Icon = cfg.icon;
  return (
    <span className={`px-2 py-1 text-[10px] font-mono rounded border ${cfg.color} flex items-center gap-1`}>
      <Icon className="w-3 h-3" /> {cfg.label}
    </span>
  );
}

// ── Page ───────────────────────────────────────────────
export default function CommunicationHub() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"compose" | "drafts" | "scheduled" | "sent" | "templates">("drafts");
  const [showComposer, setShowComposer] = useState(false);
  const [composerDraftId, setComposerDraftId] = useState<string | undefined>();
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [templateManagerMode, setTemplateManagerMode] = useState<"create" | "edit" | "duplicate" | "archive" | null>(null);

  // ── Drafts ──
  const { data: drafts = [], isLoading: loadingDrafts } = useQuery<Draft[]>({
    queryKey: ["email-drafts"],
    queryFn: async () => {
      const res = await fetchApi(`/email-drafts?tenant_id=${MOCK_TENANT_ID}`);
      return (res as any)?.data || [];
    },
    refetchInterval: 10000,
  });

  // ── Templates ──
  const { data: templatesData, isLoading: loadingTemplates } = useQuery({
    queryKey: ["communication-templates", "all", false],
    queryFn: async () => {
      const params = new URLSearchParams({ tenant_id: MOCK_TENANT_ID });
      const res = await fetch(`/api/v1/communication-templates?${params}`);
      const json = await res.json();
      return json.data || [];
    },
  });

  // ── Scheduled ──
  const { data: scheduled = [], isLoading: loadingScheduled } = useQuery<ScheduledEmail[]>({
    queryKey: ["email-scheduled"],
    queryFn: async () => {
      const res = await fetchApi(`/email-scheduling?tenant_id=${MOCK_TENANT_ID}`);
      return (res as any)?.data || [];
    },
  });

  // ── Delete draft ──
  const deleteDraftMutation = useMutation({
    mutationFn: (id: string) =>
      fetchApi(`/email-drafts/${id}?tenant_id=${MOCK_TENANT_ID}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["email-drafts"] }),
  });

  // ── Cancel schedule ──
  const cancelScheduleMutation = useMutation({
    mutationFn: (id: string) =>
      fetchApi(`/email-scheduling/${id}/cancel?tenant_id=${MOCK_TENANT_ID}`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["email-scheduled"] }),
  });

  // ── Archive template ──
  const archiveTemplateMutation = useMutation({
    mutationFn: (id: string) =>
      fetchApi(`/communication-templates/${id}?tenant_id=${MOCK_TENANT_ID}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["communication-templates"] });
    },
  });

  // ── Duplicate template ──
  const duplicateTemplateMutation = useMutation({
    mutationFn: (id: string) =>
      fetchApi(`/communication-templates/${id}/duplicate?tenant_id=${MOCK_TENANT_ID}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["communication-templates"] });
    },
  });

  // ── Stats ──
  const stats = {
    drafts: drafts.length,
    scheduled: scheduled.filter((s) => s.status === "pending").length,
    sent: scheduled.filter((s) => s.status === "sent").length,
    templates: (templatesData as Template[] | undefined)?.length || 0,
  };

  // ── Handlers ──
  const handleCompose = (draftId?: string) => {
    setComposerDraftId(draftId);
    setShowComposer(true);
  };

  const handleEditDraft = (draft: Draft) => {
    setComposerDraftId(draft.id);
    setShowComposer(true);
  };

  // ── Render ──
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Communication Hub</h1>
          <p className="text-slate-400 mt-1">Unified email management for all outreach activities</p>
        </div>
        <button
          onClick={() => handleCompose()}
          className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> Compose Email
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Drafts
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{stats.drafts}</p>
        </div>
        <div className="glass-panel p-4 border-blue-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-blue-500 uppercase mb-2">
            <Clock className="w-3.5 h-3.5" /> Scheduled
          </div>
          <p className="text-2xl font-bold font-mono text-blue-400">{stats.scheduled}</p>
        </div>
        <div className="glass-panel p-4 border-indigo-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-indigo-500 uppercase mb-2">
            <Send className="w-3.5 h-3.5" /> Sent
          </div>
          <p className="text-2xl font-bold font-mono text-indigo-400">{stats.sent}</p>
        </div>
        <div className="glass-panel p-4 border-platform-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-platform-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Templates
          </div>
          <p className="text-2xl font-bold font-mono text-platform-400">{stats.templates}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="glass-panel overflow-hidden">
        <div className="flex items-center gap-1 p-1 bg-surface-darker/50 border-b border-surface-border">
          {[
            { id: "compose" as const, label: "Compose", icon: Edit2 },
            { id: "drafts" as const, label: "Drafts", icon: FileText },
            { id: "scheduled" as const, label: "Scheduled", icon: Clock },
            { id: "sent" as const, label: "Sent", icon: Send },
            { id: "templates" as const, label: "Templates", icon: FileText },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 text-xs font-mono rounded-md transition-all ${
                  activeTab === tab.id
                    ? "bg-platform-600 text-white"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-border"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
                {tab.id === "drafts" && stats.drafts > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-slate-700 rounded-full">{stats.drafts}</span>
                )}
              </button>
            );
          })}
        </div>

        <div className="p-4">
          {/* ── Compose Tab ── */}
          {activeTab === "compose" && (
            <div className="text-center py-12">
              <Edit2 className="w-16 h-16 text-slate-700 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-slate-300 mb-2">Start Composing</h3>
              <p className="text-sm text-slate-500 mb-4">Create a new email or select a draft to continue</p>
              <button
                onClick={() => handleCompose()}
                className="px-6 py-3 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-sm font-bold font-mono transition-colors"
              >
                Open Email Composer
              </button>
            </div>
          )}

          {/* ── Drafts Tab ── */}
          {activeTab === "drafts" && (
            <div className="space-y-3">
              {loadingDrafts ? (
                <div className="text-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-platform-500 mx-auto mb-3" />
                  <p className="text-xs text-slate-500">Loading drafts...</p>
                </div>
              ) : drafts.length === 0 ? (
                <div className="text-center py-12 glass-panel">
                  <FileText className="w-16 h-16 text-slate-700 mx-auto mb-4" />
                  <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Drafts</h3>
                  <p className="text-xs text-slate-500 mb-4">Save a draft in the email composer to see it here</p>
                  <button
                    onClick={() => handleCompose()}
                    className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors"
                  >
                    Create Draft
                  </button>
                </div>
              ) : (
                drafts.map((draft) => (
                  <div
                    key={draft.id}
                    className="glass-panel p-4 hover:bg-surface-border/20 transition-all cursor-pointer"
                    onClick={() => handleEditDraft(draft)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-bold font-mono text-slate-200">
                            {draft.subject || "Untitled Draft"}
                          </h3>
                          <StatusBadge status={draft.status} />
                        </div>
                        <p className="text-[10px] font-mono text-slate-500">
                          {draft.to_email || "No recipient"} · {new Date(draft.updated_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteDraftMutation.mutate(draft.id);
                        }}
                        className="p-1.5 hover:bg-red-500/10 rounded transition-colors"
                      >
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* ── Scheduled Tab ── */}
          {activeTab === "scheduled" && (
            <div className="space-y-3">
              {loadingScheduled ? (
                <div className="text-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-platform-500 mx-auto mb-3" />
                  <p className="text-xs text-slate-500">Loading scheduled emails...</p>
                </div>
              ) : scheduled.length === 0 ? (
                <div className="text-center py-12 glass-panel">
                  <Clock className="w-16 h-16 text-slate-700 mx-auto mb-4" />
                  <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Scheduled Emails</h3>
                  <p className="text-xs text-slate-500 mb-4">Schedule an email from the composer to see it here</p>
                </div>
              ) : (
                scheduled.map((email) => (
                  <div key={email.id} className="glass-panel p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-bold font-mono text-slate-200">{email.subject}</h3>
                          <StatusBadge status={email.status} />
                        </div>
                        <p className="text-[10px] font-mono text-slate-500">
                          To: {email.to_email} · {new Date(email.scheduled_at).toLocaleString()}
                        </p>
                      </div>
                      {email.status === "pending" && (
                        <button
                          onClick={() => cancelScheduleMutation.mutate(email.id)}
                          className="p-1.5 hover:bg-red-500/10 rounded transition-colors"
                        >
                          <X className="w-4 h-4 text-red-400" />
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* ── Sent Tab ── */}
          {activeTab === "sent" && (
            <div className="space-y-3">
              {scheduled.filter(s => s.status === "sent").length === 0 ? (
                <div className="text-center py-12 glass-panel">
                  <Send className="w-16 h-16 text-slate-700 mx-auto mb-4" />
                  <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Sent Emails</h3>
                  <p className="text-xs text-slate-500">Sent emails will appear here</p>
                </div>
              ) : (
                scheduled.filter(s => s.status === "sent").map((email) => (
                  <div key={email.id} className="glass-panel p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-bold font-mono text-slate-200">{email.subject}</h3>
                          <StatusBadge status="sent" />
                        </div>
                        <p className="text-[10px] font-mono text-slate-500">
                          To: {email.to_email}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* ── Templates Tab ── */}
          {activeTab === "templates" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold font-mono text-slate-300">
                  Template Library ({stats.templates})
                </h3>
                <button
                  onClick={() => {
                    setEditingTemplate(null);
                    setTemplateManagerMode("create");
                  }}
                  className="px-3 py-1.5 bg-platform-600 hover:bg-platform-500 text-white rounded text-xs font-mono transition-colors flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> New Template
                </button>
              </div>

              {loadingTemplates ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-platform-500 mx-auto" />
                </div>
              ) : !templatesData || (templatesData as Template[]).length === 0 ? (
                <div className="text-center py-12 glass-panel">
                  <FileText className="w-16 h-16 text-slate-700 mx-auto mb-4" />
                  <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Templates</h3>
                  <p className="text-xs text-slate-500 mb-4">Create your first email template</p>
                  <button
                    onClick={() => {
                      setEditingTemplate(null);
                      setTemplateManagerMode("create");
                    }}
                    className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors"
                  >
                    Create Template
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {(templatesData as Template[]).map((tpl) => (
                    <div
                      key={tpl.id}
                      className="glass-panel p-4 hover:bg-surface-border/20 transition-all border border-surface-border"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-bold font-mono text-slate-200 truncate">{tpl.title}</h4>
                          <span className="text-[10px] font-mono text-slate-500">{tpl.category}</span>
                        </div>
                      </div>
                      <p className="text-[10px] text-slate-500 truncate mb-2">{tpl.subject}</p>
                      <div className="flex flex-wrap gap-1 mb-3">
                        {(tpl.variables || []).slice(0, 4).map((v) => (
                          <span key={v} className="text-[9px] text-platform-400 bg-platform-500/10 px-1 rounded">
                            {`{{${v}}}`}
                          </span>
                        ))}
                        {(tpl.variables || []).length > 4 && (
                          <span className="text-[9px] text-slate-500">+{tpl.variables.length - 4}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => {
                            setEditingTemplate(tpl);
                            setTemplateManagerMode("edit");
                          }}
                          className="p-1.5 hover:bg-surface-border rounded transition-colors"
                          title="Edit"
                        >
                          <Edit2 className="w-3.5 h-3.5 text-slate-400" />
                        </button>
                        <button
                          onClick={() => duplicateTemplateMutation.mutate(tpl.id)}
                          className="p-1.5 hover:bg-surface-border rounded transition-colors"
                          title="Duplicate"
                        >
                          <Copy className="w-3.5 h-3.5 text-slate-400" />
                        </button>
                        <button
                          onClick={() => {
                            setEditingTemplate(tpl);
                            setTemplateManagerMode("archive");
                          }}
                          className="p-1.5 hover:bg-red-500/10 rounded transition-colors"
                          title="Archive"
                        >
                          <Archive className="w-3.5 h-3.5 text-red-400" />
                        </button>
                        <button
                          onClick={() => {
                            setEditingTemplate(tpl);
                            setTemplateManagerMode("duplicate");
                          }}
                          className="p-1.5 hover:bg-surface-border rounded transition-colors"
                          title="Use in Composer"
                        >
                          <ExternalLink className="w-3.5 h-3.5 text-platform-400" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Email Composer Modal */}
      {showComposer && (
        <EmailComposer
          draftId={composerDraftId}
          onClose={() => {
            setShowComposer(false);
            setComposerDraftId(undefined);
            queryClient.invalidateQueries({ queryKey: ["email-drafts"] });
          }}
        />
      )}

      {/* Template Manager Modal */}
      {templateManagerMode && (
        <TemplateManager
          mode={templateManagerMode}
          template={editingTemplate || undefined}
          onClose={() => {
            setTemplateManagerMode(null);
            setEditingTemplate(null);
          }}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ["communication-templates"] });
            setActiveTab("drafts");
          }}
        />
      )}
    </div>
  );
}
