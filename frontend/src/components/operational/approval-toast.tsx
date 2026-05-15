"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, Clock, ArrowRight, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useSSE } from "@/hooks/use-sse";
import { MOCK_TENANT_ID } from "@/lib/api";

interface SSEApprovalEvent {
  event_type: string;
  channel: string;
  payload: {
    approval_id?: string;
    summary?: string;
    risk_level?: string;
    status?: string;
    sla_deadline?: string;
  };
}

interface ApprovalToastItem {
  id: string;
  summary: string;
  riskLevel: string;
  slaDeadline: string | null;
  createdAt: number;
}

const RISK_STYLES: Record<string, { bg: string; border: string; icon: string; text: string }> = {
  critical: {
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    icon: "text-red-400",
    text: "text-red-300",
  },
  high: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    icon: "text-amber-400",
    text: "text-amber-300",
  },
  medium: {
    bg: "bg-orange-500/10",
    border: "border-orange-500/30",
    icon: "text-orange-400",
    text: "text-orange-300",
  },
};

function formatSla(deadline: string | null): string {
  if (!deadline) return "No deadline";
  const diff = new Date(deadline).getTime() - Date.now();
  if (diff <= 0) return "OVERDUE";
  const hours = Math.floor(diff / 3600000);
  const mins = Math.floor((diff % 3600000) / 60000);
  return `${hours}h ${mins}m remaining`;
}

export function ApprovalToast() {
  const router = useRouter();
  const [toasts, setToasts] = useState<ApprovalToastItem[]>([]);
  const { lastEvent } = useSSE<SSEApprovalEvent>(MOCK_TENANT_ID, "approvals");

  useEffect(() => {
    if (
      lastEvent?.event_type === "approval_update" &&
      lastEvent?.payload?.status === "pending"
    ) {
      const newToast: ApprovalToastItem = {
        id: lastEvent.payload.approval_id || `toast-${Date.now()}`,
        summary: lastEvent.payload.summary || "New approval request",
        riskLevel: lastEvent.payload.risk_level || "medium",
        slaDeadline: lastEvent.payload.sla_deadline || null,
        createdAt: Date.now(),
      };

      setToasts((prev) => {
        if (prev.some((t) => t.id === newToast.id)) return prev;
        return [newToast, ...prev].slice(0, 5);
      });
    }
  }, [lastEvent]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col-reverse gap-2 max-w-sm">
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onDismiss={dismissToast}
            onReview={() => {
              dismissToast(toast.id);
              router.push("/dashboard/approvals");
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
  onReview,
}: {
  toast: ApprovalToastItem;
  onDismiss: (id: string) => void;
  onReview: () => void;
}) {
  const [remaining, setRemaining] = useState(15);

  useEffect(() => {
    if (remaining <= 0) {
      onDismiss(toast.id);
      return;
    }
    const timer = setInterval(() => setRemaining((r) => r - 1), 1000);
    return () => clearInterval(timer);
  }, [remaining, toast.id, onDismiss]);

  const style = RISK_STYLES[toast.riskLevel] || RISK_STYLES.medium;

  return (
    <motion.div
      initial={{ opacity: 0, x: 100, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.9 }}
      transition={{ type: "spring", damping: 20, stiffness: 200 }}
      className={`p-4 rounded-lg border ${style.bg} ${style.border} bg-surface-card shadow-xl backdrop-blur-sm`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-1.5 rounded-full ${style.bg} ${style.icon}`}>
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-bold uppercase tracking-wider ${style.text}`}>
              {toast.riskLevel}
            </span>
            <span className="text-xs font-mono text-slate-500 uppercase">{toast.riskLevel} Risk</span>
          </div>
          <p className="text-sm text-slate-200 font-medium truncate">{toast.summary}</p>
          <div className="flex items-center gap-4 mt-2">
            <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatSla(toast.slaDeadline)}
            </span>
            <span className="text-[10px] font-mono text-slate-600">
              auto-dismiss in {remaining}s
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onReview}
            className="p-1.5 rounded-md bg-platform-500/10 hover:bg-platform-500/20 text-platform-400 transition-colors"
            title="Review Now"
          >
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDismiss(toast.id)}
            className="p-1.5 rounded-md hover:bg-surface-border text-slate-500 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}
