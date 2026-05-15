"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Loader2, GitBranch, Radio, Activity, Clock, Server,
  ShieldAlert, Cpu, Database, ChevronRight, ChevronDown,
  AlertCircle, FileText, Link as LinkIcon, X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface LineageEvent {
  event_id: string;
  event_type: string;
  source_service: string;
  causation_id: string;
  correlation_id: string;
  timestamp: string;
  tenant_id: string;
  payload_summary: string;
}

interface LineageChain {
  event_id: string;
  lineage: LineageEvent[];
}

interface EventTree {
  correlation_id: string;
  event_count: number;
  tree: EventTreeNode[];
}

interface EventTreeNode extends LineageEvent {
  children: EventTreeNode[];
}

interface TimelineResponse {
  source_service: string;
  time_window_hours: number;
  events: LineageEvent[];
}

const SOURCE_COLORS: Record<string, string> = {
  workflow: "text-blue-400 border-blue-500/20 bg-blue-500/10",
  approval: "text-amber-400 border-amber-500/20 bg-amber-500/10",
  campaign: "text-emerald-400 border-emerald-500/20 bg-emerald-500/10",
  infra: "text-red-400 border-red-500/20 bg-red-500/10",
  system: "text-purple-400 border-purple-500/20 bg-purple-500/10",
};

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  workflow: <Activity className="w-3.5 h-3.5" />,
  approval: <ShieldAlert className="w-3.5 h-3.5" />,
  campaign: <GitBranch className="w-3.5 h-3.5" />,
  infra: <Server className="w-3.5 h-3.5" />,
  system: <Cpu className="w-3.5 h-3.5" />,
};

function detectSourceType(service: string): string {
  const lower = service.toLowerCase();
  if (lower.includes("workflow") || lower.includes("temporal")) return "workflow";
  if (lower.includes("approval") || lower.includes("gate")) return "approval";
  if (lower.includes("campaign")) return "campaign";
  if (lower.includes("infra") || lower.includes("redis") || lower.includes("kafka") || lower.includes("db")) return "infra";
  return "system";
}

function getSourceStyle(service: string): string {
  return SOURCE_COLORS[detectSourceType(service)] || SOURCE_COLORS.system;
}

function getSourceIcon(service: string): React.ReactNode {
  return SOURCE_ICONS[detectSourceType(service)] || SOURCE_ICONS.system;
}

export default function LineagePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState<"event" | "correlation">("event");
  const [activeTab, setActiveTab] = useState<"lineage" | "timeline">("lineage");
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedEvent, setSelectedEvent] = useState<LineageEvent | null>(null);

  const [submittedQuery, setSubmittedQuery] = useState("");

  const { data: lineageData, isLoading: isLoadingLineage, isError: isLineageError } = useQuery<LineageChain>({
    queryKey: ["lineage", "event", submittedQuery],
    queryFn: () => fetchApi(`/event-lineage/${submittedQuery}`),
    enabled: submittedQuery.length > 0 && searchMode === "event",
    retry: false,
  });

  const { data: treeData, isLoading: isLoadingTree, isError: isTreeError } = useQuery<EventTree>({
    queryKey: ["lineage", "tree", submittedQuery],
    queryFn: () => fetchApi(`/event-lineage/tree/${submittedQuery}`),
    enabled: submittedQuery.length > 0 && searchMode === "correlation",
    retry: false,
  });

  const { data: timelineData } = useQuery<TimelineResponse>({
    queryKey: ["lineage", "timeline"],
    queryFn: () => fetchApi(`/event-lineage/timeline?source_service=system&hours=24`),
    refetchInterval: 30000,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setSubmittedQuery(searchQuery.trim());
    }
  };

  const toggleNode = (eventId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) next.delete(eventId);
      else next.add(eventId);
      return next;
    });
  };

  const renderTreeNode = (node: EventTreeNode, depth: number = 0) => {
    const isExpanded = expandedNodes.has(node.event_id);
    const hasChildren = node.children && node.children.length > 0;
    const sourceType = detectSourceType(node.source_service);

    return (
      <div key={node.event_id}>
        <div
          className={`flex items-center gap-2 py-2 px-3 rounded-md hover:bg-surface-darker/50 cursor-pointer transition-colors group ${
            selectedEvent?.event_id === node.event_id ? "bg-platform-500/10 border border-platform-500/20" : ""
          }`}
          style={{ marginLeft: `${depth * 20}px` }}
          onClick={() => setSelectedEvent(node)}
        >
          {hasChildren ? (
            <button onClick={(e) => { e.stopPropagation(); toggleNode(node.event_id); }} className="text-slate-500 hover:text-slate-300">
              {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
          ) : (
            <div className="w-3.5 h-3.5 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-500" />
            </div>
          )}
          <span className={getSourceStyle(node.source_service)}>
            {getSourceIcon(node.source_service)}
          </span>
          <span className="text-xs font-mono text-slate-300 flex-1 truncate">{node.event_type}</span>
          <span className="text-[10px] font-mono text-slate-500">{node.source_service}</span>
          <span className="text-[10px] font-mono text-slate-600">
            {new Date(node.timestamp).toLocaleTimeString()}
          </span>
        </div>
        <AnimatePresence>
          {isExpanded && hasChildren && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              {node.children.map((child) => renderTreeNode(child, depth + 1))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  const renderLineageChain = () => {
    if (!lineageData?.lineage) return null;
    const chain = lineageData.lineage;

    return (
      <div className="space-y-1">
        {chain.map((event, idx) => (
          <div key={event.event_id}>
            <div
              className={`flex items-center gap-3 p-3 rounded-md cursor-pointer hover:bg-surface-darker/50 transition-colors ${
                selectedEvent?.event_id === event.event_id ? "bg-platform-500/10 border border-platform-500/20" : ""
              }`}
              onClick={() => setSelectedEvent(event)}
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-surface-darker border border-surface-border">
                {getSourceIcon(event.source_service)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-mono px-1.5 py-0.5 rounded border ${getSourceStyle(event.source_service)}`}>
                    {event.source_service}
                  </span>
                  <span className="text-xs font-mono text-slate-300 truncate">{event.event_type}</span>
                  <span className="text-[10px] font-mono text-slate-600 ml-auto">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {event.payload_summary && (
                  <p className="text-[10px] font-mono text-slate-500 mt-1 truncate">{event.payload_summary}</p>
                )}
              </div>
            </div>
            {idx < chain.length - 1 && (
              <div className="flex justify-center py-1">
                <div className="w-px h-4 bg-slate-700" />
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">EVENT_LINEAGE</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Event causality & trace explorer</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400">
            {timelineData?.events?.length || 0} events (24h)
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="glass-panel p-4">
        <form onSubmit={handleSearch} className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-surface-darker rounded-lg border border-surface-border p-1">
            <button
              type="button"
              onClick={() => setSearchMode("event")}
              className={`px-3 py-1.5 text-xs font-mono rounded-md transition-colors ${
                searchMode === "event"
                  ? "bg-platform-500/20 text-platform-300 border border-platform-500/30"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              Event ID
            </button>
            <button
              type="button"
              onClick={() => setSearchMode("correlation")}
              className={`px-3 py-1.5 text-xs font-mono rounded-md transition-colors ${
                searchMode === "correlation"
                  ? "bg-platform-500/20 text-platform-300 border border-platform-500/30"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              Correlation ID
            </button>
          </div>
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={searchMode === "event" ? "Search by event ID..." : "Search by correlation ID..."}
              className="w-full pl-10 pr-4 py-2 bg-surface-darker border border-surface-border rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500 focus:ring-1 focus:ring-platform-500 transition-all font-mono text-sm"
            />
          </div>
          <button
            type="submit"
            className="px-6 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-platform-900/30"
          >
            Trace
          </button>
        </form>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lineage / Tree Panel */}
        <div className="lg:col-span-2 glass-panel overflow-hidden flex flex-col">
          <div className="px-6 py-3 border-b border-surface-border flex items-center gap-4 bg-surface-darker/50">
            <button
              onClick={() => setActiveTab("lineage")}
              className={`px-3 py-1.5 text-xs font-mono rounded-md transition-colors ${
                activeTab === "lineage"
                  ? "bg-platform-500/20 text-platform-300 border border-platform-500/30"
                  : "text-slate-500"
              }`}
            >
              CHAIN
            </button>
            <button
              onClick={() => setActiveTab("timeline")}
              className={`px-3 py-1.5 text-xs font-mono rounded-md transition-colors ${
                activeTab === "timeline"
                  ? "bg-platform-500/20 text-platform-300 border border-platform-500/30"
                  : "text-slate-500"
              }`}
            >
              TIMELINE
            </button>
            <span className="ml-auto text-[10px] font-mono text-slate-600">
              {searchMode === "event" ? "CAUSALITY CHAIN" : "CORRELATION TREE"}
            </span>
          </div>

          <div className="flex-1 overflow-auto max-h-[600px] p-4 custom-scrollbar">
            {activeTab === "lineage" ? (
              <>
                {searchMode === "event" && submittedQuery && (
                  isLoadingLineage ? (
                    <div className="flex items-center justify-center py-16">
                      <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
                    </div>
                  ) : isLineageError ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <AlertCircle className="w-8 h-8 text-red-400 mb-3" />
                      <p className="text-sm text-slate-400 font-mono">Event not found</p>
                    </div>
                  ) : lineageData?.lineage ? (
                    <div>
                      <div className="text-xs font-mono text-slate-500 mb-3">
                        {lineageData.lineage.length} event{lineageData.lineage.length !== 1 ? "s" : ""} in chain
                      </div>
                      {renderLineageChain()}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <GitBranch className="w-12 h-12 text-slate-600 mb-4" />
                      <p className="text-sm text-slate-500 font-mono">
                        Enter an event ID to trace its causality chain
                      </p>
                    </div>
                  )
                )}

                {searchMode === "correlation" && submittedQuery && (
                  isLoadingTree ? (
                    <div className="flex items-center justify-center py-16">
                      <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
                    </div>
                  ) : isTreeError ? (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <AlertCircle className="w-8 h-8 text-red-400 mb-3" />
                      <p className="text-sm text-slate-400 font-mono">No events found for this correlation ID</p>
                    </div>
                  ) : treeData?.tree ? (
                    <div>
                      <div className="text-xs font-mono text-slate-500 mb-3">
                        {treeData.event_count} events in correlation tree
                      </div>
                      {treeData.tree.map((node) => renderTreeNode(node))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                      <LinkIcon className="w-12 h-12 text-slate-600 mb-4" />
                      <p className="text-sm text-slate-500 font-mono">
                        Enter a correlation ID to view its event tree
                      </p>
                    </div>
                  )
                )}

                {!submittedQuery && (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <Radio className="w-12 h-12 text-slate-600 mb-4" />
                    <p className="text-sm text-slate-500 font-mono">
                      Search for an event or correlation ID to begin tracing
                    </p>
                  </div>
                )}
              </>
            ) : (
              /* Timeline View */
              <div className="space-y-2">
                <div className="text-xs font-mono text-slate-500 mb-3">
                  Recent events across all services
                </div>
                {timelineData?.events?.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <Clock className="w-12 h-12 text-slate-600 mb-4" />
                    <p className="text-sm text-slate-500 font-mono">No events in the last 24 hours</p>
                  </div>
                ) : (
                  (timelineData?.events || []).map((event) => (
                    <div
                      key={event.event_id}
                      className={`flex items-center gap-3 p-2.5 rounded-md cursor-pointer hover:bg-surface-darker/50 transition-colors ${
                        selectedEvent?.event_id === event.event_id ? "bg-platform-500/10 border border-platform-500/20" : ""
                      }`}
                      onClick={() => setSelectedEvent(event)}
                    >
                      <span className={`p-1.5 rounded ${getSourceStyle(event.source_service)}`}>
                        {getSourceIcon(event.source_service)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-slate-300">{event.event_type}</span>
                          <span className="text-[10px] font-mono text-slate-600">{event.source_service}</span>
                        </div>
                        {event.payload_summary && (
                          <p className="text-[10px] font-mono text-slate-500 truncate">{event.payload_summary}</p>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-slate-600">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Event Detail Panel */}
        <div className="glass-panel p-6 flex flex-col">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <FileText className="w-5 h-5 text-platform-500" />
            Event Detail
          </h3>
          {selectedEvent ? (
            <div className="space-y-4 flex-1">
              <div className="p-3 rounded-md bg-surface-darker border border-surface-border">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Event ID</span>
                <code className="text-xs font-mono text-platform-400 break-all">{selectedEvent.event_id}</code>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-md bg-surface-darker border border-surface-border">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Type</span>
                  <span className="text-xs font-mono text-slate-300">{selectedEvent.event_type}</span>
                </div>
                <div className="p-3 rounded-md bg-surface-darker border border-surface-border">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Service</span>
                  <span className={`text-xs font-mono px-1.5 py-0.5 rounded border ${getSourceStyle(selectedEvent.source_service)}`}>
                    {selectedEvent.source_service}
                  </span>
                </div>
              </div>
              <div className="p-3 rounded-md bg-surface-darker border border-surface-border">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Timestamp</span>
                <span className="text-xs font-mono text-slate-300">{new Date(selectedEvent.timestamp).toLocaleString()}</span>
              </div>
              {selectedEvent.causation_id && (
                <div className="p-3 rounded-md bg-surface-darker border border-surface-border">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Causation ID</span>
                  <code className="text-xs font-mono text-slate-300 break-all">{selectedEvent.causation_id}</code>
                </div>
              )}
              {selectedEvent.correlation_id && (
                <div className="p-3 rounded-md bg-surface-darker border border-surface-border">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Correlation ID</span>
                  <code className="text-xs font-mono text-slate-300 break-all">{selectedEvent.correlation_id}</code>
                </div>
              )}
              {selectedEvent.payload_summary && (
                <div className="p-3 rounded-md bg-surface-darker border border-surface-border">
                  <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Payload</span>
                  <p className="text-xs font-mono text-slate-400">{selectedEvent.payload_summary}</p>
                </div>
              )}
              <div className="p-3 rounded-md bg-surface-darker border border-surface-border">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Tenant ID</span>
                <code className="text-xs font-mono text-slate-500">{selectedEvent.tenant_id}</code>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center">
              <FileText className="w-10 h-10 text-slate-600 mb-3" />
              <p className="text-sm text-slate-500 font-mono">Select an event</p>
              <p className="text-xs text-slate-600 mt-1">Click on any event to view its full details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
