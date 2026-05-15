import { useEffect, useRef } from "react";
import { create } from "zustand";

import { API_BASE_URL, MOCK_TENANT_ID } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WorkflowState {
  workflow_id: string;
  type: string;
  status: string;
  started_at: string;
  task_queue: string;
}

export interface ApprovalState {
  approval_id: string;
  tenant_id: string;
  summary: string;
  risk_level: string;
  status: string;
  created_at: string;
}

export interface CampaignState {
  campaign_id: string;
  tenant_id: string;
  name: string;
  status: string;
  phase: string;
  updated_at: string;
}

export interface QueueState {
  [queueName: string]: number;
}

export interface WorkerState {
  worker_id: string;
  task_queue: string;
  last_heartbeat: string;
  status: string;
}

export interface TelemetryState {
  workflows: Record<string, number>;
  approvals: Record<string, number>;
  communication: Record<string, number>;
  reports: Record<string, number>;
  infrastructure: Record<string, string>;
  timestamp: string;
}

export interface HeartbeatSummary {
  workflow_count: number;
  worker_count: number;
  queue_depths: Record<string, number>;
  infra_health: Record<string, string>;
  approval_count: number;
  campaign_count: number;
  timestamp: string;
}

interface SSEMessage {
  event_type: string;
  channel: string;
  tenant_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Realtime Store (Zustand)
// ---------------------------------------------------------------------------

export interface RealtimeStore {
  workflows: WorkflowState[];
  approvals: ApprovalState[];
  campaigns: CampaignState[];
  infrastructure: Record<string, string>;
  queues: Record<string, number>;
  workers: WorkerState[];
  telemetry: TelemetryState | null;
  isConnected: boolean;
  lastHeartbeat: number | null;
  connectionError: string | null;

  setWorkflows: (workflows: WorkflowState[]) => void;
  setApprovals: (approvals: ApprovalState[]) => void;
  setCampaigns: (campaigns: CampaignState[]) => void;
  setInfrastructure: (infrastructure: Record<string, string>) => void;
  setQueues: (queues: Record<string, number>) => void;
  setWorkers: (workers: WorkerState[]) => void;
  setTelemetry: (telemetry: TelemetryState) => void;
  setConnected: (connected: boolean) => void;
  setHeartbeat: (timestamp: number) => void;
  setConnectionError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  workflows: [],
  approvals: [],
  campaigns: [],
  infrastructure: {},
  queues: {},
  workers: [],
  telemetry: null,
  isConnected: false,
  lastHeartbeat: null,
  connectionError: null,
};

export const useRealtimeStore = create<RealtimeStore>((set) => ({
  ...initialState,

  setWorkflows: (workflows) => set({ workflows }),
  setApprovals: (approvals) => set({ approvals }),
  setCampaigns: (campaigns) => set({ campaigns }),
  setInfrastructure: (infrastructure) => set({ infrastructure }),
  setQueues: (queues) => set({ queues }),
  setWorkers: (workers) => set({ workers }),
  setTelemetry: (telemetry) => set({ telemetry }),
  setConnected: (isConnected) => set({ isConnected }),
  setHeartbeat: (lastHeartbeat) => set({ lastHeartbeat }),
  setConnectionError: (connectionError) => set({ connectionError }),
  reset: () => set(initialState),
}));

// ---------------------------------------------------------------------------
// Event parsing helpers
// ---------------------------------------------------------------------------

function parseWorkflows(payload: Record<string, unknown>): WorkflowState[] {
  const raw = payload.workflows;
  if (Array.isArray(raw)) return raw as WorkflowState[];
  return [];
}

function parseApprovals(payload: Record<string, unknown>): ApprovalState[] {
  const raw = payload.approvals;
  if (Array.isArray(raw)) return raw as ApprovalState[];
  return [];
}

function parseCampaigns(payload: Record<string, unknown>): CampaignState[] {
  const raw = payload.campaigns;
  if (Array.isArray(raw)) return raw as CampaignState[];
  return [];
}

function parseQueues(payload: Record<string, unknown>): Record<string, number> {
  const raw = payload.queues;
  if (raw && typeof raw === "object") return raw as Record<string, number>;
  return {};
}

function parseWorkers(payload: Record<string, unknown>): WorkerState[] {
  const raw = payload.workers;
  if (Array.isArray(raw)) return raw as WorkerState[];
  return [];
}

function parseSummary(payload: Record<string, unknown>): HeartbeatSummary | null {
  const summary = payload.summary;
  if (summary && typeof summary === "object") return summary as HeartbeatSummary;
  return null;
}

// ---------------------------------------------------------------------------
// Event dispatcher
// ---------------------------------------------------------------------------

function dispatchEvent(store: RealtimeStore, msg: SSEMessage): void {
  const { event_type, payload } = msg;

  switch (event_type) {
    case "state_sync": {
      store.setWorkflows(parseWorkflows(payload));
      store.setApprovals(parseApprovals(payload));
      store.setCampaigns(parseCampaigns(payload));
      store.setQueues(parseQueues(payload));
      store.setWorkers(parseWorkers(payload));
      const infra = payload.infrastructure;
      if (infra && typeof infra === "object") {
        store.setInfrastructure(infra as Record<string, string>);
      }
      store.setConnected(true);
      store.setConnectionError(null);
      break;
    }
    case "workflow_update": {
      const data = payload.data as Record<string, unknown> | undefined;
      if (data) {
        const wf: WorkflowState = {
          workflow_id: (data.workflow_id as string) || "",
          type: (payload.workflow_type as string) || "",
          status: (payload.status as string) || "",
          started_at: new Date().toISOString(),
          task_queue: (data.task_queue as string) || "",
        };
        const existing = store.workflows.filter(
          (w) => w.workflow_id !== wf.workflow_id,
        );
        if (wf.status !== "completed" && wf.status !== "failed") {
          store.setWorkflows([...existing, wf]);
        } else {
          store.setWorkflows(existing);
        }
      }
      break;
    }
    case "approval_update": {
      const app: ApprovalState = {
        approval_id: (payload.approval_id as string) || "",
        tenant_id: msg.tenant_id,
        summary: (payload.summary as string) || "",
        risk_level: (payload.risk_level as string) || "",
        status: (payload.status as string) || "",
        created_at: msg.timestamp,
      };
      const existing = store.approvals.filter(
        (a) => a.approval_id !== app.approval_id,
      );
      if (app.status === "pending") {
        store.setApprovals([...existing, app]);
      } else {
        store.setApprovals(existing);
      }
      break;
    }
    case "campaign_update": {
      const camp: CampaignState = {
        campaign_id: (payload.campaign_id as string) || "",
        tenant_id: msg.tenant_id,
        name: (payload.name as string) || "",
        status: (payload.status as string) || "",
        phase: (payload.phase as string) || "",
        updated_at: msg.timestamp,
      };
      const existing = store.campaigns.filter(
        (c) => c.campaign_id !== camp.campaign_id,
      );
      if (camp.status !== "completed" && camp.status !== "archived") {
        store.setCampaigns([...existing, camp]);
      } else {
        store.setCampaigns(existing);
      }
      break;
    }
    case "infra_update": {
      const component = payload.component as string;
      const status = payload.status as string;
      if (component) {
        store.setInfrastructure({
          ...store.infrastructure,
          [component]: status,
        });
      }
      break;
    }
    case "queue_update": {
      const queuePayload = payload.queues;
      if (queuePayload && typeof queuePayload === "object") {
        store.setQueues(queuePayload as Record<string, number>);
      }
      break;
    }
    case "worker_update": {
      const worker: WorkerState = {
        worker_id: (payload.worker_id as string) || "",
        task_queue: (payload.task_queue as string) || "",
        last_heartbeat: msg.timestamp,
        status: "active",
      };
      const existing = store.workers.filter(
        (w) => w.worker_id !== worker.worker_id,
      );
      store.setWorkers([...existing, worker]);
      break;
    }
    case "heartbeat": {
      store.setHeartbeat(Date.now());
      store.setConnected(true);
      const summary = parseSummary(payload);
      if (summary) {
        store.setWorkflows(
          Array.from({ length: summary.workflow_count }, (_, i) => ({
            workflow_id: `placeholder-${i}`,
            type: "",
            status: "",
            started_at: "",
            task_queue: "",
          })),
        );
        store.setWorkers(
          Array.from({ length: summary.worker_count }, (_, i) => ({
            worker_id: `placeholder-${i}`,
            task_queue: "",
            last_heartbeat: "",
            status: "",
          })),
        );
        store.setInfrastructure(summary.infra_health);
        store.setQueues(summary.queue_depths);
      }
      break;
    }
    default:
      break;
  }
}

// ---------------------------------------------------------------------------
// React hook
// ---------------------------------------------------------------------------

export function useRealtime(tenantId: string = MOCK_TENANT_ID): void {
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const maxRetryDelay = 30_000;

  useEffect(() => {
    const store = useRealtimeStore.getState();
    store.reset();

    const connect = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const url = `${API_BASE_URL}/stream/${tenantId}/full`;

      try {
        const es = new EventSource(url);
        eventSourceRef.current = es;

        es.onopen = () => {
          retryCountRef.current = 0;
          useRealtimeStore.getState().setConnected(true);
          useRealtimeStore.getState().setConnectionError(null);
        };

        es.onmessage = (event) => {
          try {
            const msg: SSEMessage = JSON.parse(event.data);
            const currentStore = useRealtimeStore.getState();
            dispatchEvent(currentStore, msg);
          } catch {
            // skip unparseable messages
          }
        };

        es.onerror = () => {
          es.close();
          const currentStore = useRealtimeStore.getState();
          currentStore.setConnected(false);
          currentStore.setConnectionError("Connection lost");
          retryCountRef.current += 1;

          const delay = Math.min(
            1000 * 2 ** retryCountRef.current,
            maxRetryDelay,
          );

          setTimeout(connect, delay);
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to connect";
        useRealtimeStore.getState().setConnectionError(msg);
        useRealtimeStore.getState().setConnected(false);

        retryCountRef.current += 1;
        const delay = Math.min(
          1000 * 2 ** retryCountRef.current,
          maxRetryDelay,
        );
        setTimeout(connect, delay);
      }
    };

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      useRealtimeStore.getState().reset();
    };
  }, [tenantId]);
}
