"use client"

import * as React from "react"
import { TrendingUp, TrendingDown } from "lucide-react"
import { cn } from "@/lib/utils"

interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string
  value: string | number
  change?: {
    value: number
    direction: "up" | "down"
  }
  icon?: React.ReactNode
}

const MetricCard = React.forwardRef<HTMLDivElement, MetricCardProps>(
  ({ label, value, change, icon, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-xl border border-surface-border bg-surface-card/80 backdrop-blur-md p-6 shadow-xl shadow-black/20",
          className
        )}
        {...props}
      >
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-400">{label}</p>
            <p className="text-2xl font-bold text-slate-100">{value}</p>
          </div>
          {icon && (
            <div className="rounded-lg bg-surface-darker border border-surface-border p-2.5 text-slate-400">
              {icon}
            </div>
          )}
        </div>
        {change && (
          <div className="mt-3 flex items-center gap-1.5">
            {change.direction === "up" ? (
              <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <TrendingDown className="h-3.5 w-3.5 text-red-400" />
            )}
            <span
              className={cn(
                "text-xs font-medium",
                change.direction === "up" ? "text-emerald-400" : "text-red-400"
              )}
            >
              {change.direction === "up" ? "+" : ""}
              {change.value}%
            </span>
            <span className="text-xs text-slate-500">vs last period</span>
          </div>
        )}
      </div>
    )
  }
)
MetricCard.displayName = "MetricCard"

export { MetricCard }
