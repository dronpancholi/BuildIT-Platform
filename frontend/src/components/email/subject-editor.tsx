"use client";

import { Input } from "@/components/ui/input";

interface SubjectEditorProps {
  subject: string;
  onChange: (subject: string) => void;
}

export function SubjectEditor({ subject, onChange }: SubjectEditorProps) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wide">
        Subject
      </label>
      <Input
        type="text"
        placeholder="Enter email subject..."
        value={subject}
        onChange={(e) => onChange(e.target.value)}
        className="bg-surface-darker border-surface-border text-slate-200 placeholder-slate-600"
      />
    </div>
  );
}
