export interface APIResponse<T> {
  success: boolean;
  data: T;
  error: APIError | null;
  meta: ResponseMeta | null;
}

export interface APIError {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
  retryable: boolean;
}

export interface ResponseMeta {
  total?: number;
  offset?: number;
  limit?: number;
  has_more?: boolean;
}

export interface PaginationParams {
  offset?: number;
  limit?: number;
}

export interface TenantParams {
  tenant_id: string;
}

export interface HealthResponse {
  status: string;
  components: HealthComponent[];
}

export interface HealthComponent {
  name: string;
  status: string;
  latency_ms: number;
}

export interface ApprovalRequest {
  id: string;
  tenant_id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  status: string;
  requested_by: string;
  created_at: string;
  workflow_run_id?: string;
  category?: string;
  context_snapshot?: Record<string, unknown>;
  ai_risk_summary?: string;
  sla_deadline?: string;
  risk_level?: string;
  summary?: string;
  escalation_count?: number;
}
