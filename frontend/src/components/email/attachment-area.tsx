"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Paperclip, X, FileText, File } from "lucide-react";

interface Attachment {
  name: string;
  size: number;
  type: string;
}

interface AttachmentAreaProps {
  attachments: Attachment[];
  onAdd: (files: File[]) => void;
  onRemove: (index: number) => void;
  disabled?: boolean;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export function AttachmentArea({
  attachments,
  onAdd,
  onRemove,
  disabled,
}: AttachmentAreaProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onAdd(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      onAdd(Array.from(e.dataTransfer.files));
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          className="h-8 border-platform-500/50 text-platform-400 hover:bg-platform-500/10 text-xs gap-1"
        >
          <Paperclip className="w-3.5 h-3.5" />
          Attach Files
        </Button>
        <span className="text-[10px] text-slate-500">
          {attachments.length} file{attachments.length !== 1 ? "s" : ""}
        </span>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileSelect}
        className="hidden"
      />

      {attachments.length > 0 && (
        <div
          className={`border-2 border-dashed rounded-lg p-3 transition-colors ${
            isDragOver
              ? "border-platform-500 bg-platform-500/5"
              : "border-surface-border"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
        >
          <div className="space-y-2">
            {attachments.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between px-3 py-2 bg-surface-card rounded border border-surface-border"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {file.type.includes("image") ? (
                    <FileText className="w-4 h-4 text-platform-400 flex-shrink-0" />
                  ) : (
                    <File className="w-4 h-4 text-slate-500 flex-shrink-0" />
                  )}
                  <span className="text-xs text-slate-300 truncate">
                    {file.name}
                  </span>
                  <span className="text-[10px] text-slate-500 flex-shrink-0">
                    {formatSize(file.size)}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(index)}
                  className="text-slate-500 hover:text-red-400 transition-colors flex-shrink-0 ml-2"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-slate-600 text-center mt-2">
            Drop files here to attach
          </p>
        </div>
      )}
    </div>
  );
}
