"use client";

import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import {
  parseVariables,
  VARIABLE_DEFINITIONS,
} from "@/lib/merge-variables";
import { X, Loader2, CheckCircle2, AlertTriangle, Eye } from "lucide-react";
import { safeStr, safeUpper } from "@/lib/safe";

interface TemplateData {
  title: string;
  category: string;
  subject: string;
  body: string;
  variables?: string[];
}

interface TemplateManagerProps {
  mode: "create" | "edit" | "duplicate" | "archive";
  template?: {
    id: string;
    title: string;
    category: string;
    subject: string;
    body: string;
    variables?: string[];
  };
  onClose: () => void;
  onSuccess?: () => void;
}

const CATEGORIES = [
  "outreach",
  "followup",
  "link_insertion",
  "partnership",
  "report",
];

export function TemplateManager({
  mode,
  template,
  onClose,
  onSuccess,
}: TemplateManagerProps) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(template?.title || "");
  const [category, setCategory] = useState(template?.category || "outreach");
  const [subject, setSubject] = useState(template?.subject || "");
  const [body, setBody] = useState(template?.body || "");
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    if (mode === "duplicate" && template) {
      setTitle(`${template.title} (Copy)`);
      setCategory(template.category);
      setSubject(template.subject);
      setBody(template.body);
    }
  }, [mode, template]);

  const detectedVars = parseVariables(body + subject);
  const missingVars = detectedVars.filter(
    (v) => !VARIABLE_DEFINITIONS.some((d) => d.name === v)
  );

  const createMutation = useMutation({
    mutationFn: async (data: TemplateData) => {
      if (mode === "duplicate" && template) {
        return fetchApi(
          `/communication-templates/${template.id}/duplicate?tenant_id=${MOCK_TENANT_ID}`,
          { method: "POST" }
        );
      }
      const params = new URLSearchParams({ tenant_id: MOCK_TENANT_ID });
      return fetchApi(
        `/communication-templates?${params.toString()}`,
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["communication-templates"] });
      if (onSuccess) onSuccess();
      onClose();
    },
  });

  const archiveMutation = useMutation({
    mutationFn: async () => {
      if (!template) return;
      return fetchApi(
        `/communication-templates/${template.id}?tenant_id=${MOCK_TENANT_ID}`,
        { method: "DELETE" }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["communication-templates"] });
      if (onSuccess) onSuccess();
      onClose();
    },
  });

  const handleSave = () => {
    if (mode === "archive") {
      archiveMutation.mutate();
      return;
    }
    createMutation.mutate({ title, category, subject, body });
  };

  const isEditing = mode === "edit" || mode === "duplicate";
  const isArchive = mode === "archive";
  const isSaving = createMutation.isPending || archiveMutation.isPending;

  const title_label = isArchive
    ? "Archive Template"
    : isEditing
    ? "Edit Template"
    : "Create Template";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-surface-card border border-surface-border rounded-xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border bg-surface-darker/50">
          <h2 className="text-lg font-bold text-slate-100">{title_label}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-border rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {isArchive ? (
            <div className="text-center py-12">
              <AlertTriangle className="w-16 h-16 text-amber-400 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-slate-200 mb-2">
                Archive "{template?.title}"?
              </h3>
              <p className="text-sm text-slate-400 mb-4">
                This template will be hidden but not deleted. You can restore it later.
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
                    Template Name
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Initial Outreach - Guest Post"
                    className="w-full px-3 py-2 text-sm bg-surface-darker border border-surface-border rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
                    Category
                  </label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-surface-darker border border-surface-border rounded text-slate-200 focus:outline-none focus:border-platform-500"
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {safeStr(c, "").replace("_", " ").replace(/\b\w/g, (l) => safeUpper(l))}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
                  Subject Line
                </label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g., Quick question about {{domain}}"
                  className="w-full px-3 py-2 text-sm bg-surface-darker border border-surface-border rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
                  Email Body
                </label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="Hi {{prospect_name}},&#10;&#10;I noticed {{domain}}..."
                  rows={12}
                  className="w-full px-3 py-2 text-sm bg-surface-darker border border-surface-border rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500 font-mono"
                />
              </div>

              <div className="flex items-center gap-2 text-xs">
                <button
                  onClick={() => setShowPreview(!showPreview)}
                  className="flex items-center gap-1 text-platform-400 hover:text-platform-300 transition-colors"
                >
                  <Eye className="w-3.5 h-3.5" />
                  {showPreview ? "Hide Preview" : "Show Preview"}
                </button>
              </div>

              {showPreview && (
                <div className="space-y-3 border border-surface-border rounded-lg p-4 bg-surface-darker">
                  <div>
                    <span className="text-[10px] font-mono text-slate-500 uppercase">Subject: </span>
                    <span className="text-sm text-slate-200">{subject}</span>
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none text-slate-300 whitespace-pre-wrap">
                    {body}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
                  Variable Validation
                </div>
                {detectedVars.length === 0 ? (
                  <p className="text-xs text-slate-500">No merge variables detected</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {detectedVars.map((v) => {
                      const isKnown = !missingVars.includes(v);
                      return (
                        <span
                          key={v}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono rounded-full ${
                            isKnown
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          }`}
                        >
                          {isKnown ? (
                            <CheckCircle2 className="w-2.5 h-2.5" />
                          ) : (
                            <AlertTriangle className="w-2.5 h-2.5" />
                          )}
                          {`{{${v}}}`}
                        </span>
                      );
                    })}
                  </div>
                )}
                {missingVars.length > 0 && (
                  <p className="text-[10px] text-amber-400">
                    {missingVars.length} unknown variable(s) detected
                  </p>
                )}
              </div>
            </>
          )}
        </div>

        <div className="px-6 py-4 border-t border-surface-border bg-surface-darker/50 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || (!isArchive && !title.trim())}
            className={`px-6 py-2 text-xs font-bold font-mono rounded-lg transition-colors flex items-center gap-2 ${
              isArchive
                ? "bg-red-600 hover:bg-red-500 text-white"
                : "bg-platform-600 hover:bg-platform-500 text-white"
            } disabled:opacity-50`}
          >
            {isSaving ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                {isArchive ? "Archiving..." : "Saving..."}
              </>
            ) : isArchive ? (
              "Archive Template"
            ) : isEditing ? (
              "Save Changes"
            ) : (
              "Create Template"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
