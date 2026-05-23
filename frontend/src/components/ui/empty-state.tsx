"use client";

import { type ReactNode } from "react";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action, secondaryAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-16 h-16 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-4 text-slate-500">
        {icon}
      </div>
      <h3 className="text-lg font-medium text-slate-300 mb-2">{title}</h3>
      <p className="text-sm text-slate-500 max-w-md mb-6 leading-relaxed">{description}</p>
      <div className="flex items-center gap-3">
        {action && (
          <button
            onClick={action.onClick}
            className="px-5 py-2.5 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-all shadow-lg shadow-platform-900/30 flex items-center gap-2"
          >
            {action.label}
          </button>
        )}
        {secondaryAction && (
          <button
            onClick={secondaryAction.onClick}
            className="px-5 py-2.5 bg-surface-darker border border-surface-border text-slate-300 hover:text-slate-200 rounded-lg text-xs font-bold font-mono transition-all"
          >
            {secondaryAction.label}
          </button>
        )}
      </div>
    </div>
  );
}
