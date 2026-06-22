"use client";

import { useState, useRef, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { TemplatePicker } from "./template-picker";
import { MergeVariableEditor } from "./merge-variable-editor";
import { SubjectEditor } from "./subject-editor";
import { SchedulePicker } from "./schedule-picker";
import { AttachmentArea } from "./attachment-area";
import { VariablePreview } from "./variable-preview";
import { parseVariables } from "@/lib/merge-variables";
import { Button } from "@/components/ui/button";
import {
  Send,
  Save,
  X,
  FileText,
  Eye,
  Loader2,
  CheckCircle2,
  ChevronRight,
  Calendar,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Draft {
  id: string;
  subject: string;
  body_html: string;
  template_id?: string;
  to_email?: string;
  variables?: Record<string, string>;
  status: string;
  created_at: string;
  updated_at: string;
}

interface EmailComposerProps {
  onClose?: () => void;
  draftId?: string;
}

export function EmailComposer({ onClose, draftId }: EmailComposerProps) {
  const queryClient = useQueryClient();
  const editorRef = useRef<any>(null);

  const [subject, setSubject] = useState("");
  const [bodyHtml, setBodyHtml] = useState("");
  const [toEmail, setToEmail] = useState("");
  const [scheduledAt, setScheduledAt] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [showDrafts, setShowDrafts] = useState(false);
  const [activeDraftId, setActiveDraftId] = useState<string | null>(draftId || null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  const { data: draftsData } = useQuery({
    queryKey: ["email-drafts"],
    queryFn: async () => {
      const data = await fetchApi(`/email-drafts?tenant_id=${MOCK_TENANT_ID}`);
      return (data as any)?.data || [];
    },
    enabled: showDrafts,
  });

  const saveDraftMutation = useMutation({
    mutationFn: async (body: { subject: string; body_html: string; template_id?: string }) => {
      setSaveStatus("saving");
      if (activeDraftId) {
        return fetchApi(`/email-drafts/${activeDraftId}?tenant_id=${MOCK_TENANT_ID}`, {
          method: "PUT",
          body: JSON.stringify(body),
        });
      }
      return fetchApi(`/email-drafts?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
    onSuccess: (data: any) => {
      setSaveStatus("saved");
      if (data?.id) setActiveDraftId(data.id);
      queryClient.invalidateQueries({ queryKey: ["email-drafts"] });
      setTimeout(() => setSaveStatus("idle"), 2000);
    },
    onError: () => {
      setSaveStatus("error");
    },
  });

  const handleTemplateSelect = useCallback((template: any) => {
    setSubject(template.subject);
    setBodyHtml(`<p>${template.body.replace(/\n/g, "<br/>")}</p>`);
    setSelectedTemplateId(template.id);
    setShowTemplatePicker(false);
  }, []);

  const handleSaveDraft = useCallback(() => {
    saveDraftMutation.mutate({
      subject,
      body_html: bodyHtml,
      template_id: selectedTemplateId || undefined,
    });
  }, [subject, bodyHtml, selectedTemplateId, saveDraftMutation]);

  const handleLoadDraft = useCallback((draft: Draft) => {
    setSubject(draft.subject || "");
    setBodyHtml(draft.body_html || "");
    setActiveDraftId(draft.id);
    setSelectedTemplateId(draft.template_id || null);
    setShowDrafts(false);
    setShowTemplatePicker(false);
  }, []);

  const handleSend = useCallback(() => {
    if (scheduledAt) {
      fetchApi(`/email-scheduling?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({
          thread_id: activeDraftId || "new",
          scheduled_at: scheduledAt,
          subject,
          body: bodyHtml,
          to_email: toEmail || "recipient@example.com",
        }),
      }).then(() => {
        queryClient.invalidateQueries({ queryKey: ["email-drafts"] });
        if (onClose) onClose();
      });
    }
  }, [scheduledAt, activeDraftId, subject, bodyHtml, toEmail, queryClient, onClose]);

  const allVariables = parseVariables(bodyHtml);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-surface-card border border-surface-border rounded-xl w-full max-w-6xl max-h-[95vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border bg-surface-darker/50">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-platform-400" />
            <h2 className="text-lg font-bold text-slate-100">
              {activeDraftId ? "Edit Draft" : "Email Composer"}
            </h2>
            {activeDraftId && (
              <span className="text-[10px] font-mono text-slate-500 bg-surface-darker px-2 py-0.5 rounded">
                {activeDraftId.slice(0, 8)}...
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {saveStatus === "saving" && (
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Loader2 className="w-3 h-3 animate-spin" /> Saving...
              </span>
            )}
            {saveStatus === "saved" && (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <CheckCircle2 className="w-3 h-3" /> Saved
              </span>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={handleSaveDraft}
              disabled={saveDraftMutation.isPending}
              className="h-8 text-xs gap-1"
            >
              <Save className="w-3.5 h-3.5" /> Save Draft
            </Button>
            {onClose && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onClose}
                className="h-8 text-xs"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-80 border-r border-surface-border overflow-y-auto p-4 space-y-4 bg-surface-darker/30">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowDrafts(!showDrafts)}
              className="w-full h-8 text-xs justify-between"
            >
              <span>{showDrafts ? "Hide Drafts" : "Load Draft"}</span>
              <ChevronRight className={`w-3 h-3 transition-transform ${showDrafts ? "rotate-90" : ""}`} />
            </Button>

            {showDrafts && (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {(draftsData as Draft[] | undefined)?.length === 0 && (
                  <p className="text-xs text-slate-500 text-center py-4">
                    No saved drafts
                  </p>
                )}
                {(draftsData as Draft[] | undefined)?.map((draft: Draft) => (
                  <button
                    key={draft.id}
                    onClick={() => handleLoadDraft(draft)}
                    className={`w-full text-left p-2 rounded border text-xs transition-colors ${
                      activeDraftId === draft.id
                        ? "border-platform-500 bg-platform-500/10"
                        : "border-surface-border hover:border-platform-500/50 bg-surface-darker"
                    }`}
                  >
                    <div className="font-medium text-slate-200 truncate">
                      {draft.subject || "No subject"}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      {new Date(draft.updated_at).toLocaleDateString()}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {showTemplatePicker ? (
              <TemplatePicker
                onSelect={handleTemplateSelect}
                onCreateNew={() => {}}
              />
            ) : (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">
                    Template: {selectedTemplateId ? "Selected" : "None"}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowTemplatePicker(true)}
                    className="h-6 text-[10px] text-platform-400"
                  >
                    Change
                  </Button>
                </div>
              </div>
            )}

            <SchedulePicker
              scheduledAt={scheduledAt}
              onChange={setScheduledAt}
            />

            <AttachmentArea
              attachments={attachments.map((f) => ({
                name: f.name,
                size: f.size,
                type: f.type,
              }))}
              onAdd={(files) =>
                setAttachments((prev) => [...prev, ...files])
              }
              onRemove={(index) =>
                setAttachments((prev) =>
                  prev.filter((_, i) => i !== index)
                )
              }
            />
          </div>

          {/* Main editor area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {/* To Email */}
              <div className="space-y-1">
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
                  To
                </label>
                <input
                  type="email"
                  placeholder="recipient@example.com"
                  value={toEmail}
                  onChange={(e) => setToEmail(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-surface-darker border border-surface-border rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
                />
              </div>

              <SubjectEditor subject={subject} onChange={setSubject} />

              <MergeVariableEditor
                ref={editorRef}
                content={bodyHtml}
                onChange={setBodyHtml}
                placeholder="Compose your email..."
              />

              {/* Preview Toggle */}
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowPreview(!showPreview)}
                  className="h-8 text-xs gap-1"
                >
                  <Eye className="w-3.5 h-3.5" />
                  {showPreview ? "Hide Preview" : "Preview"}
                </Button>
                {allVariables.length > 0 && (
                  <span className="text-[10px] font-mono text-platform-400">
                    {allVariables.length} merge variable(s) detected
                  </span>
                )}
              </div>

              {showPreview && (
                <VariablePreview
                  subject={subject}
                  body={bodyHtml}
                />
              )}
            </div>

            {/* Footer actions */}
            <div className="px-6 py-3 border-t border-surface-border bg-surface-darker/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500">
                  {bodyHtml ? `${bodyHtml.length} chars` : "Empty"}
                </span>
                {allVariables.length > 0 && (
                  <span className="text-[10px] text-platform-400">
                    {allVariables.length} variable(s)
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleSaveDraft}
                  disabled={saveDraftMutation.isPending}
                  className="h-9 text-xs gap-1"
                >
                  <Save className="w-3.5 h-3.5" /> Save Draft
                </Button>
                {scheduledAt ? (
                  <Button
                    size="sm"
                    onClick={handleSend}
                    className="h-9 text-xs gap-1 bg-platform-600 hover:bg-platform-500"
                  >
                    <Calendar className="w-3.5 h-3.5" /> Schedule Send
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    disabled
                    className="h-9 text-xs gap-1 bg-slate-600 text-slate-400"
                  >
                    <Send className="w-3.5 h-3.5" /> Send Now
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


