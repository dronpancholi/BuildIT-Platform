"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-platform-500/50",
  {
    variants: {
      variant: {
        default: "bg-platform-600 text-white border-transparent",
        secondary: "bg-slate-600 text-white border-transparent",
        destructive: "bg-red-600 text-white border-transparent",
        outline: "border border-surface-border text-slate-300 bg-transparent",
        success: "bg-emerald-600 text-white border-transparent",
        warning: "bg-amber-600 text-white border-transparent",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(badgeVariants({ variant }), className)}
        {...props}
      />
    )
  }
)
Badge.displayName = "Badge"

export { Badge, badgeVariants }
