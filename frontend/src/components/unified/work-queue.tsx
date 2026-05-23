"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { 
  CheckCircle2, XCircle, Clock, AlertTriangle, 
  Filter, Search, CheckSquare, Mail, GitBranch,
  FileText, Users, ChevronDown, ArrowUpRight,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useCommandCenter } from "@/hooks/use-command-center";
import { ErrorState, LoadingState } from "@/components/ui/error-state";
// Types removed - using inline types below

type QueueItemType = "approval" | "follow_up" | "reply" | "campaign_alert";
type Priority = "critical" | "high" | "medium" | "low";

interface QueueItem {
  id: string;
  type: QueueItemType;
  priority: Priority;
  title: string;
  description: string;
  customer: string;
  customerId: string;
  dueAt?: string;
  createdAt: string;
  metadata: any;
}

function getPriorityColor(priority: Priority): string {
  switch (priority) {
    case "critical": return "text-red-400 bg-red-500/10 border-red-500/20";
    case "high": return "text-orange-400 bg-orange-500/10 border-orange-500/20";
    case "medium": return "text-amber-400 bg-amber-500/10 border-amber-500/20";
    case "low": return "text-slate-400 bg-slate-500/10 border-slate-500/20";
  }
}

function getPriorityIcon(priority: Priority) {
  switch (priority) {
    case "critical": return <AlertTriangle className="w-3 h-3" />;
    case "high": return <Clock className="w-3 h-3" />;
    case "medium": return <Clock className="w-3 h-3" />;
    case "low": return <CheckCircle2 className="w-3 h-3" />;
  }
}

function getTypeIcon(type: QueueItemType) {
  switch (type) {
    case "approval": return <FileText className="w-3.5 h-3.5" />;
    case "follow_up": return <Mail className="w-3.5 h-3.5" />;
    case "reply": return <Mail className="w-3.5 h-3.5" />;
    case "campaign_alert": return <GitBranch className="w-3.5 h-3.5" />;
  }
}

export function WorkQueue() {
  const { openCommand } = useCommandCenter();
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<QueueItemType | "all">("all");
  const [filterPriority, setFilterPriority] = useState<Priority | "all">("all");
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Fetch approvals
  const { data: approvals = [], isLoading: loadingApprovals, error: approvalsError } = useQuery<any[]>({
    queryKey: ["approvals", "pending"],
    queryFn: () => fetchApi(`/approvals?tenant_id=${MOCK_TENANT_ID}&status=pending`),
    refetchInterval: 30000,
  });

  // Fetch campaigns needing attention
  const { data: campaigns = [], isLoading: loadingCampaigns, error: campaignsError } = useQuery<any[]>({
    queryKey: ["campaigns", "attention"],
    queryFn: () => fetchApi(`/campaigns?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 60000,
  });

  const isLoading = loadingApprovals || loadingCampaigns;
  const error = approvalsError || campaignsError;

  // Build unified queue
  const queueItems = useMemo(() => {
    const items: QueueItem[] = [];

    // Add approvals
    approvals.forEach(approval => {
      items.push({
        id: `approval-${approval.id}`,
        type: "approval",
        priority: approval.risk_level === "critical" ? "critical" : 
                  approval.risk_level === "high" ? "high" : "medium",
        title: `${approval.category.replace("_", " ").toUpperCase()} Approval`,
        description: approval.summary || "Pending approval decision",
        customer: approval.customer_name || "Unknown",
        customerId: approval.customer_id,
        dueAt: approval.sla_deadline,
        createdAt: approval.created_at,
        metadata: approval,
      });
    });

    // Add campaign alerts
    campaigns.forEach(campaign => {
      if (campaign.health_score < 0.5 || campaign.status === "stalled") {
        items.push({
          id: `alert-${campaign.id}`,
          type: "campaign_alert",
          priority: campaign.health_score < 0.3 ? "critical" : "high",
          title: `Campaign: ${campaign.name}`,
          description: `Health: ${(campaign.health_score * 100).toFixed(0)}% - Needs attention`,
          customer: campaign.client_name || "Unknown",
          customerId: campaign.client_id,
          createdAt: campaign.updated_at,
          metadata: campaign,
        });
      }
    });

    return items;
  }, [approvals, campaigns]);

  // Filter items
  const filteredItems = useMemo(() => {
    return queueItems.filter(item => {
      const matchesSearch = !searchQuery || 
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.customer.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesType = filterType === "all" || item.type === filterType;
      const matchesPriority = filterPriority === "all" || item.priority === filterPriority;
      return matchesSearch && matchesType && matchesPriority;
    });
  }, [queueItems, searchQuery, filterType, filterPriority]);

  // Group by priority
  const groupedItems = useMemo(() => {
    const groups: Record<Priority, QueueItem[]> = {
      critical: [],
      high: [],
      medium: [],
      low: [],
    };
    filteredItems.forEach(item => {
      groups[item.priority].push(item);
    });
    return groups;
  }, [filteredItems]);

  const toggleSelect = (id: string) => {
    setSelectedItems(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleExpand = (id: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalItems = filteredItems.length;
  const criticalCount = groupedItems.critical.length;
  const highCount = groupedItems.high.length;

  if (error) {
    return (
      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-3 border-b border-surface-border bg-surface-darker/50">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-platform-400" />
            <h3 className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
              Work Queue
            </h3>
          </div>
        </div>
        <ErrorState 
          error={error} 
          message="Failed to load work queue"
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-3 border-b border-surface-border bg-surface-darker/50">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-platform-400" />
            <h3 className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
              Work Queue
            </h3>
          </div>
        </div>
        <LoadingState message="Loading work queue..." />
      </div>
    );
  }

  return (
    <div className="glass-panel overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border bg-surface-darker/50">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-platform-400" />
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
            Work Queue
          </h3>
          <span className="text-[9px] font-mono text-slate-600">
            {totalItems} items • {criticalCount} critical • {highCount} high
          </span>
        </div>
        <div className="flex items-center gap-2">
{selectedItems.size > 0 && (
              <div className="flex items-center gap-2">
                <button 
                  className="px-2 py-1 text-[9px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1 hover:bg-emerald-500/20 transition-colors"
                  onClick={() => openCommand("approve_item")}
                >
                  <CheckSquare className="w-3 h-3" /> Approve
                </button>
                <button 
                  className="px-2 py-1 text-[9px] font-mono rounded bg-red-500/10 text-red-400 border border-red-500/20 flex items-center gap-1 hover:bg-red-500/20 transition-colors"
                  onClick={() => openCommand("reject_item")}
                >
                  <XCircle className="w-3 h-3" /> Reject
                </button>
                <span className="text-[9px] font-mono text-slate-600">
                  {selectedItems.size} selected
                </span>
              </div>
            )}
        </div>
      </div>

      {/* Filters */}
      <div className="px-4 py-2 border-b border-surface-border flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500" />
          <input
            type="text"
            placeholder="Search queue..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-2 py-1 bg-surface-darker border border-surface-border rounded text-[10px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500 transition-colors"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as any)}
          className="px-2 py-1 bg-surface-darker border border-surface-border rounded text-[10px] text-slate-300 focus:outline-none focus:border-platform-500"
        >
          <option value="all">All Types</option>
          <option value="approval">Approvals</option>
          <option value="follow_up">Follow-ups</option>
          <option value="reply">Replies</option>
          <option value="campaign_alert">Alerts</option>
        </select>
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value as any)}
          className="px-2 py-1 bg-surface-darker border border-surface-border rounded text-[10px] text-slate-300 focus:outline-none focus:border-platform-500"
        >
          <option value="all">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Queue Items */}
      <div className="divide-y divide-surface-border">
        {totalItems === 0 ? (
          <div className="p-8 text-center">
            <CheckCircle2 className="w-8 h-8 text-slate-700 mx-auto mb-2" />
            <p className="text-[10px] font-mono text-slate-600">No items in queue</p>
          </div>
        ) : (
          <>
            {criticalCount > 0 && (
              <div>
                <div className="px-4 py-1.5 bg-red-500/5 border-b border-red-500/10 flex items-center gap-2">
                  <AlertTriangle className="w-3 h-3 text-red-400" />
                  <span className="text-[9px] font-mono font-bold text-red-400 uppercase">Critical</span>
                </div>
                {groupedItems.critical.map((item, i) => (
                  <QueueItemRow
                    key={item.id}
                    item={item}
                    isSelected={selectedItems.has(item.id)}
                    isExpanded={expandedItems.has(item.id)}
                    onSelect={() => toggleSelect(item.id)}
                    onExpand={() => toggleExpand(item.id)}
                  />
                ))}
              </div>
            )}

            {highCount > 0 && (
              <div>
                <div className="px-4 py-1.5 bg-orange-500/5 border-b border-orange-500/10 flex items-center gap-2">
                  <Clock className="w-3 h-3 text-orange-400" />
                  <span className="text-[9px] font-mono font-bold text-orange-400 uppercase">High Priority</span>
                </div>
                {groupedItems.high.map((item) => (
                  <QueueItemRow
                    key={item.id}
                    item={item}
                    isSelected={selectedItems.has(item.id)}
                    isExpanded={expandedItems.has(item.id)}
                    onSelect={() => toggleSelect(item.id)}
                    onExpand={() => toggleExpand(item.id)}
                  />
                ))}
              </div>
            )}

            {groupedItems.medium.length > 0 && (
              <div>
                <div className="px-4 py-1.5 bg-amber-500/5 border-b border-amber-500/10 flex items-center gap-2">
                  <Clock className="w-3 h-3 text-amber-400" />
                  <span className="text-[9px] font-mono font-bold text-amber-400 uppercase">Medium Priority</span>
                </div>
                {groupedItems.medium.map((item) => (
                  <QueueItemRow
                    key={item.id}
                    item={item}
                    isSelected={selectedItems.has(item.id)}
                    isExpanded={expandedItems.has(item.id)}
                    onSelect={() => toggleSelect(item.id)}
                    onExpand={() => toggleExpand(item.id)}
                  />
                ))}
              </div>
            )}

            {groupedItems.low.length > 0 && (
              <div>
                <div className="px-4 py-1.5 bg-slate-500/5 border-b border-slate-500/10 flex items-center gap-2">
                  <CheckCircle2 className="w-3 h-3 text-slate-400" />
                  <span className="text-[9px] font-mono font-bold text-slate-400 uppercase">Low Priority</span>
                </div>
                {groupedItems.low.map((item) => (
                  <QueueItemRow
                    key={item.id}
                    item={item}
                    isSelected={selectedItems.has(item.id)}
                    isExpanded={expandedItems.has(item.id)}
                    onSelect={() => toggleSelect(item.id)}
                    onExpand={() => toggleExpand(item.id)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function QueueItemRow({ 
  item, 
  isSelected, 
  isExpanded,
  onSelect, 
  onExpand 
}: { 
  item: QueueItem;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onExpand: () => void;
}) {
  const priorityColor = getPriorityColor(item.priority);
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`border-b border-surface-border/50 ${isSelected ? "bg-platform-500/5" : ""}`}
    >
      <div 
        className="px-4 py-2 flex items-start gap-3 hover:bg-surface-border/20 transition-colors cursor-pointer"
        onClick={onExpand}
      >
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => { e.stopPropagation(); onSelect(); }}
          className="mt-0.5 w-3 h-3 rounded border-surface-border bg-surface-darker text-platform-600 focus:ring-platform-500"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-1.5 py-0.5 text-[8px] font-mono rounded border flex items-center gap-1 ${priorityColor}`}>
              {getPriorityIcon(item.priority)}
              {item.priority.toUpperCase()}
            </span>
            <span className="px-1.5 py-0.5 text-[8px] font-mono rounded border border-surface-border bg-surface-darker text-slate-500 flex items-center gap-1">
              {getTypeIcon(item.type)}
              {item.type.replace("_", " ").toUpperCase()}
            </span>
            <span className="text-xs font-mono text-slate-200 truncate flex-1">{item.title}</span>
            <ChevronDown className={`w-3 h-3 text-slate-500 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
          </div>
          <p className="text-[10px] text-slate-500 truncate">{item.description}</p>
          <div className="flex items-center gap-3 mt-1 text-[9px] font-mono text-slate-600">
            <span className="flex items-center gap-1">
              <Users className="w-2.5 h-2.5" />
              {item.customer}
            </span>
            {item.dueAt && (
              <span className="flex items-center gap-1 text-amber-500">
                <Clock className="w-2.5 h-2.5" />
                Due: {new Date(item.dueAt).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      </div>

      {isExpanded && (
        <div className="px-4 pb-3 ml-6 border-l border-surface-border/50 pl-6">
          <div className="mt-2 p-3 bg-surface-darker/50 rounded border border-surface-border/50">
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <div>
                <span className="text-slate-600">Customer:</span>
                <span className="ml-2 text-slate-300">{item.customer}</span>
              </div>
              <div>
                <span className="text-slate-600">Created:</span>
                <span className="ml-2 text-slate-300">{new Date(item.createdAt).toLocaleString()}</span>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <button 
                onClick={(e) => { e.stopPropagation(); openCommand("approve_item"); }}
                className="px-2 py-1 text-[9px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
              >
                Approve
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); openCommand("reject_item"); }}
                className="px-2 py-1 text-[9px] font-mono rounded bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors"
              >
                Reject
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); }}
                className="px-2 py-1 text-[9px] font-mono rounded bg-surface-darker text-slate-400 border border-surface-border hover:text-slate-300 transition-colors"
              >
                View Details
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); }}
                className="ml-auto px-2 py-1 text-[9px] font-mono text-platform-400 hover:text-platform-300 flex items-center gap-1"
              >
                Go to Customer <ArrowUpRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}