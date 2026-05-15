export interface HealthComponent {
  name: string;
  status: "healthy" | "degraded" | "unhealthy";
  latency_ms?: number;
  error?: string;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  environment: string;
  timestamp: string;
  components: HealthComponent[];
}

export interface ApprovalRequest {
  id: string;
  tenant_id: string;
  workflow_run_id: string;
  category: string;
  risk_level: string;
  status: string;
  summary: string;
  ai_risk_summary: string;
  sla_deadline: string | null;
  escalation_count: number;
  context_snapshot: Record<string, any>;
}

export interface Campaign {
  id: string;
  tenant_id: string;
  client_id: string;
  name: string;
  campaign_type: string;
  status: string;
  target_link_count: number;
  acquired_link_count: number;
  health_score: number;
  workflow_run_id: string | null;
}

export interface Client {
  id: string;
  name: string;
  domain: string;
  created_at: string;
}

export interface TenantTelemetry {
  workflows: {
    total_campaigns: number;
    active_campaigns: number;
    total_clusters: number;
    workflows_running: number;
  };
  approvals: {
    pending_approvals: number;
    approved_today: number;
    rejected_today: number;
  };
  communication: {
    emails_sent: number;
    emails_delivered: number;
    emails_bounced: number;
  };
  reports: {
    total_reports: number;
  };
  infrastructure: Record<string, string>;
  timestamp: string;
}

export interface TelemetryResponse {
  success: boolean;
  data: TenantTelemetry;
}
