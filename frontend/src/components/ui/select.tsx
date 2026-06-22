"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: { label: string; value: string }[]
  placeholder?: string
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, options, placeholder, ...props }, ref) => {
    return (
      <select
        className={cn(
          "flex h-10 w-full appearance-none rounded-lg border border-surface-border bg-surface-darker px-3 py-2 pr-8 text-sm text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-platform-500/50 focus-visible:border-platform-500/50 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      >
        {placeholder && (
          <option value="" className="bg-surface-darker text-slate-500">
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            className="bg-surface-darker text-slate-200"
          >
            {option.label}
          </option>
        ))}
      </select>
    )
  }
)
Select.displayName = "Select"

export { Select }
