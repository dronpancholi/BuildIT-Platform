"use client"

import { AlertTriangle, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { LoadingSpinner } from "@/components/ui/loading-spinner"

interface ErrorStateProps {
  error?: Error | null
  onRetry?: () => void
  message?: string
  className?: string
}

function ErrorState({ error, onRetry, message = "Something went wrong", className }: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center",
        className
      )}
    >
      <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
        <AlertTriangle className="w-6 h-6 text-red-400" />
      </div>
      <h3 className="text-sm font-semibold text-slate-200 mb-2">Error</h3>
      <p className="text-xs text-slate-500 mb-4 max-w-md">{message}</p>
      {error && (
        <p className="text-[10px] font-mono text-slate-600 mb-4 max-w-md break-words">
          {error.message}
        </p>
      )}
      {onRetry && (
        <Button onClick={onRetry} size="sm">
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </Button>
      )}
    </div>
  )
}

interface LoadingStateProps {
  message?: string
  size?: "sm" | "md" | "lg"
  className?: string
}

function LoadingState({ message = "Loading...", size = "md", className }: LoadingStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center",
        className
      )}
    >
      <LoadingSpinner size={size} className="mb-4" />
      <p className="text-xs text-slate-500">{message}</p>
    </div>
  )
}

export { ErrorState, LoadingState }
