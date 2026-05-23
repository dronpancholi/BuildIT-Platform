"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

export function ErrorState({ 
  error, 
  onRetry, 
  message = "Something went wrong" 
}: { 
  error?: Error | null; 
  onRetry?: () => void; 
  message?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
        <AlertTriangle className="w-6 h-6 text-red-400" />
      </div>
      <h3 className="text-sm font-bold font-mono text-slate-200 mb-2">Error</h3>
      <p className="text-xs text-slate-500 mb-4">{message}</p>
      {error && (
        <p className="text-[10px] font-mono text-slate-600 mb-4 max-w-md break-words">
          {error.message}
        </p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-2"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ 
  icon, 
  title, 
  description, 
  action 
}: { 
  icon?: React.ReactNode; 
  title: string; 
  description: string; 
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      {icon || (
        <div className="w-12 h-12 rounded-full bg-slate-700/50 border border-slate-600/50 flex items-center justify-center mb-4">
          <AlertTriangle className="w-6 h-6 text-slate-500" />
        </div>
      )}
      <h3 className="text-sm font-bold font-mono text-slate-200 mb-2">{title}</h3>
      <p className="text-xs text-slate-500 mb-4 max-w-md">{description}</p>
      {action}
    </div>
  );
}

export function LoadingState({ message = "Loading...", size = "md" }: { message?: string; size?: "sm" | "md" | "lg" }) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6", 
    lg: "w-8 h-8"
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <RefreshCw className={`${sizeClasses[size]} text-platform-500 animate-spin mb-4`} />
      <p className="text-xs font-mono text-slate-500">{message}</p>
    </div>
  );
}