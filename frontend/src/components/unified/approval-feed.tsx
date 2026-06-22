"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Check, 
  X, 
  Clock, 
  FileText, 
  Mail, 
  AlertCircle,
  CheckCircle,
  XCircle,
  Hourglass
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { safeArr } from "@/lib/safe";

interface ApprovalFeedProps {
  className?: string;
}

interface Approval {
  id: string;
  type: "email" | "report" | "keyword" | "prospect" | "campaign_change";
  status: "pending" | "approved" | "rejected";
  title: string;
  description: string;
  created_at: string;
  metadata: any;
}

export function ApprovalFeed({ className }: ApprovalFeedProps) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<any>({
    queryKey: ["approvals-feed"],
    queryFn: () => fetchApi("/approvals/list"),
    refetchInterval: 15000,
  });

  const approveMutation = useMutation({
    mutationFn: async ({ approvalId, action }: { approvalId: string; action: string }) => {
      return fetchApi(`/approvals/${approvalId}/${action}`, { method: "POST" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals-feed"] });
      queryClient.invalidateQueries({ queryKey: ["work-queue"] });
    },
  });

  const approvals: Approval[] = safeArr<Approval>(data?.data?.approvals);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pending":
        return <Clock className="w-4 h-4 text-amber-400" />;
      case "approved":
        return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case "rejected":
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Hourglass className="w-4 h-4 text-slate-400" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "email":
        return <Mail className="w-4 h-4 text-blue-400" />;
      case "report":
        return <FileText className="w-4 h-4 text-purple-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <Card className={cn("bg-surface-card border-surface-border", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-slate-400">Approval Feed</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-platform-500"></div>
          </div>
        ) : approvals.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No approvals pending
          </div>
        ) : (
          <div className="space-y-3">
            {approvals.map((approval) => (
              <div
                key={approval.id}
                className="p-4 rounded-lg bg-surface-darker border border-surface-border hover:border-platform-500/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-surface-darker">
                      {getTypeIcon(approval.type)}
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-slate-200">{approval.title}</h4>
                      <p className="text-xs text-slate-500">{approval.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(approval.status)}
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[10px] border-0",
                        approval.status === "pending" && "bg-amber-500/10 text-amber-400",
                        approval.status === "approved" && "bg-emerald-500/10 text-emerald-400",
                        approval.status === "rejected" && "bg-red-500/10 text-red-400"
                      )}
                    >
                      {approval.status}
                    </Badge>
                  </div>
                </div>

                {approval.status === "pending" ? (
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10"
                      onClick={() =>
                        approveMutation.mutate({ approvalId: approval.id, action: "approve" })
                      }
                      disabled={approveMutation.isPending}
                    >
                      <Check className="w-3 h-3 mr-1" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs border-red-500/50 text-red-400 hover:bg-red-500/10"
                      onClick={() =>
                        approveMutation.mutate({ approvalId: approval.id, action: "reject" })
                      }
                      disabled={approveMutation.isPending}
                    >
                      <X className="w-3 h-3 mr-1" />
                      Reject
                    </Button>
                    <div className="ml-auto text-xs text-slate-500">
                      {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-500">
                    {approval.status === "approved" ? "Approved" : "Rejected"}{" "}
                    {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
