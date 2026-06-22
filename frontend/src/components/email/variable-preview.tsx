"use client";

import { useState } from "react";
import {
  resolveVariables,
  validateVariables,
  buildVariableData,
  parseVariables,
  VARIABLE_DEFINITIONS,
} from "@/lib/merge-variables";
import { Eye, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

interface VariablePreviewProps {
  subject: string;
  body: string;
}

export function VariablePreview({ subject, body }: VariablePreviewProps) {
  const [showPreview, setShowPreview] = useState(false);
  const [variableOverrides, setVariableOverrides] = useState<
    Record<string, string>
  >({});

  const allVariables = [
    ...new Set([...parseVariables(subject), ...parseVariables(body)]),
  ];

  const validation = validateVariables(body, allVariables);

  const resolvedSubject = showPreview
    ? resolveVariables(subject, buildVariableData(allVariables, variableOverrides))
    : subject;

  const resolvedBody = showPreview
    ? resolveVariables(body, buildVariableData(allVariables, variableOverrides))
    : body;

  const handleOverrideChange = (name: string, value: string) => {
    setVariableOverrides((prev) => ({ ...prev, [name]: value }));
  };

  const hasIssues = validation.missing.length > 0 || validation.unknown.length > 0;

  return (
    <div className="space-y-3">
      <button
        onClick={() => setShowPreview(!showPreview)}
        className="flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
      >
        <Eye className="w-3.5 h-3.5" />
        {showPreview ? "Hide Preview" : "Show Preview"}
        {hasIssues && (
          <span className="flex items-center gap-1 text-amber-400">
            <AlertTriangle className="w-3 h-3" />
            {validation.missing.length + validation.unknown.length} issue(s)
          </span>
        )}
      </button>

      {showPreview && (
        <div className="space-y-4 border border-surface-border rounded-lg bg-surface-darker p-4">
          {allVariables.length > 0 && (
            <div className="space-y-2">
              <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
                Variable Values
              </div>
              <div className="grid grid-cols-2 gap-2">
                {allVariables.map((name) => {
                  const def = VARIABLE_DEFINITIONS.find((d) => d.name === name);
                  return (
                    <div key={name} className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-platform-400 w-28 truncate">
                        {`{{${name}}}`}
                      </span>
                      <input
                        type="text"
                        placeholder={def?.sample ?? ""}
                        value={variableOverrides[name] ?? ""}
                        onChange={(e) => handleOverrideChange(name, e.target.value)}
                        className="flex-1 px-2 py-1 text-[10px] bg-surface-card border border-surface-border rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
              Subject Preview
            </div>
            <div className="p-3 bg-surface-card border border-surface-border rounded text-sm text-slate-200">
              {resolvedSubject}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
              Body Preview
            </div>
            <div
              className="p-3 bg-surface-card border border-surface-border rounded prose prose-invert prose-sm max-w-none text-slate-200"
              dangerouslySetInnerHTML={{ __html: resolvedBody }}
            />
          </div>
        </div>
      )}

      <div className="space-y-2">
        <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
          Variable Validation
        </div>
        <div className="flex flex-wrap gap-2">
          {allVariables.map((name) => {
            const inDefs = VARIABLE_DEFINITIONS.some((d) => d.name === name);
            return (
              <span
                key={name}
                className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono rounded-full ${
                  inDefs
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}
              >
                {inDefs ? (
                  <CheckCircle2 className="w-2.5 h-2.5" />
                ) : (
                  <XCircle className="w-2.5 h-2.5" />
                )}
                {`{{${name}}}`}
              </span>
            );
          })}
          {allVariables.length === 0 && (
            <span className="text-[10px] text-slate-500">No variables in content</span>
          )}
        </div>
      </div>
    </div>
  );
}
