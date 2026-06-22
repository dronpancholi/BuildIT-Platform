import { DEFAULT_TENANT_ID } from '@/config/constants';
import { useTenantStore } from '@/stores/tenant-store';

import { useAuthStore } from '@/stores/auth-store';
import { getApiBaseUrl } from '@/lib/api-url';

export const API_BASE_URL = getApiBaseUrl();

export const DEFAULT_TENANT_FALLBACK_ID = DEFAULT_TENANT_ID;

/**
 * @deprecated Use getTenantId() instead. Kept as an alias of the default
 * tenant UUID for pages that import it by name. Its value is the real
 * default-tenant UUID, not synthetic data.
 */
export const MOCK_TENANT_ID = DEFAULT_TENANT_ID;

export function getTenantId(): string {
  if (typeof window === "undefined") return DEFAULT_TENANT_ID;
  try {
    // Prefer the authenticated user's tenant (from the JWT/Bearer token).
    // This ensures the URL tenant_id matches the bearer tenant, which the
    // backend validates against the user row.
    const user = useAuthStore.getState().user;
    if (user?.tenant_id) return user.tenant_id;
    const id = useTenantStore.getState().currentTenantId;
    return id || DEFAULT_TENANT_ID;
  } catch {
    return process.env.NEXT_PUBLIC_TENANT_ID || DEFAULT_TENANT_ID;
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const tid = getTenantId();
  const sep = endpoint.includes("?") ? "&" : "?";
  const hasTenant = endpoint.includes("tenant_id=");
  const url = hasTenant
    ? `${API_BASE_URL}${endpoint}`
    : `${API_BASE_URL}${endpoint}${sep}tenant_id=${tid}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as any),
  };

  // Send the Bearer token obtained from /identity/dev/login (or future
  // Clerk JWT). Backend get_current_user resolves this and uses the
  // internal users row for tenant_id and role — we do NOT trust any
  // X-User-* headers.
  try {
    const token = useAuthStore.getState().token;
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  } catch {
    // Fail silently in SSR
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((e: { msg?: string; message?: string }) => e.msg || e.message || JSON.stringify(e)).join("; ")
      : data.detail || data.error?.message || response.statusText;
    throw new ApiError(response.status, detail);
  }

  return data.data !== undefined ? data.data : data;
}

// ---------------------------------------------------------------------------
// User Management
// ---------------------------------------------------------------------------

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  tenant_id: string;
  created_at: string;
}

export const userApi = {
  listUsers: () => fetchApi<User[]>("/identity/users"),
  inviteUser: (data: { name: string; email: string; role: string }) =>
    fetchApi("/identity/users/invite", { method: "POST", body: JSON.stringify(data) }),
  activateUser: (userId: string) =>
    fetchApi(`/identity/users/${userId}/activate`, { method: "POST" }),
  deactivateUser: (userId: string) =>
    fetchApi(`/identity/users/${userId}/deactivate`, { method: "POST" }),
  updateUserRole: (userId: string, role: string) =>
    fetchApi(`/identity/users/${userId}/role`, { method: "PUT", body: JSON.stringify({ role }) }),
};

// ---------------------------------------------------------------------------
// Client Management
// ---------------------------------------------------------------------------

export const clientApi = {
  archiveClient: (id: string) =>
    fetchApi<void>(`/clients/${id}/archive`, { method: "POST" }),
  restoreClient: (id: string) =>
    fetchApi<void>(`/clients/${id}/restore`, { method: "POST" }),
};

// ---------------------------------------------------------------------------
// Campaign & Provider Actions
// ---------------------------------------------------------------------------

export const cancelCampaign = (id: string) =>
  fetchApi(`/campaigns/${id}/cancel`, { method: "POST" });
export const enableProvider = (id: string) =>
  fetchApi(`/providers/${id}/enable`, { method: "POST" });
export const disableProvider = (id: string) =>
  fetchApi(`/providers/${id}/disable`, { method: "POST" });
export const testProvider = (id: string) =>
  fetchApi(`/providers/${id}/test`, { method: "POST" });

// ---------------------------------------------------------------------------
// Citation Automation (Phase 1)
// ---------------------------------------------------------------------------

export interface CitationProject {
  id: string;
  tenant_id: string;
  client_id: string | null;
  business_name: string;
  website_url: string | null;
  category: string | null;
  keywords: string[];
  phone: string | null;
  email: string | null;
  description: string | null;
  short_bio: string | null;
  long_bio: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string;
  postal_code: string | null;
  logo_url: string | null;
  facebook_url: string | null;
  twitter_url: string | null;
  linkedin_url: string | null;
  instagram_url: string | null;
  youtube_url: string | null;
  pinterest_url: string | null;
  submission_email: string | null;
  status: "active" | "paused" | "completed" | "archived";
  total_sites: number;
  pending_count: number;
  in_progress_count: number;
  already_exists_count: number;
  new_backlink_count: number;
  failed_count: number;
  stats: {
    total_sites: number;
    pending: number;
    in_progress: number;
    already_exists: number;
    new_backlink: number;
    failed: number;
    rejected: number;
    completion_pct: number;
  };
  created_at: string;
  updated_at: string | null;
}

export interface CitationSite {
  id: string;
  tenant_id: string;
  name: string;
  url: string;
  submission_url: string | null;
  registration_url: string | null;
  category: string;
  niche: string | null;
  geo_target: string | null;
  has_logo_upload: boolean;
  has_description: boolean;
  has_hours: boolean;
  has_social_links: boolean;
  has_images: boolean;
  has_video: boolean;
  requires_email_verification: boolean;
  difficulty_score: number;
  monthly_visitors: number;
  domain_authority: number;
  is_free: boolean;
  is_active: boolean;
  // Phase 6: Global expansion fields
  region: string | null;
  importance_score: number;
  is_premium: boolean;
  monthly_audience: number | null;
  language: string | null;
  submission_difficulty: string | null;
  estimated_field_count: number;
  slug: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CitationSubmission {
  id: string;
  tenant_id: string;
  project_id: string;
  site_id: string;
  status: string;
  status_notes: string | null;
  account_created: boolean;
  email_verified: boolean;
  listing_claimed: boolean;
  listing_url: string | null;
  form_data: Record<string, unknown> | null;
  started_at: string | null;
  submitted_at: string | null;
  completed_at: string | null;
  assigned_to: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  site?: CitationSite;
}

// Projects
export const citationApi = {
  listProjects: () => fetchApi<CitationProject[]>("/citations/projects"),
  getProject: (id: string) => fetchApi<CitationProject>(`/citations/projects/${id}`),
  createProject: (data: Partial<CitationProject>) =>
    fetchApi<CitationProject>("/citations/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateProject: (id: string, data: Partial<CitationProject>) =>
    fetchApi<CitationProject>(`/citations/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteProject: (id: string) =>
    fetchApi<void>(`/citations/projects/${id}`, { method: "DELETE" }),
  updateProjectStatus: (id: string, status: string) =>
    fetchApi<CitationProject>(`/citations/projects/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  // Sites
  listSites: (params?: { category?: string; search?: string; region?: string; is_premium?: boolean; limit?: number; sort_by?: string; sort_order?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.search) qs.set("search", params.search);
    if (params?.region) qs.set("region", params.region);
    if (params?.is_premium !== undefined) qs.set("is_premium", String(params.is_premium));
    if (params?.limit) qs.set("per_page", String(params.limit));
    if (params?.sort_by) qs.set("sort_by", params.sort_by);
    if (params?.sort_order) qs.set("sort_order", params.sort_order);
    const q = qs.toString();
    return fetchApi<CitationSite[]>(`/citations/sites${q ? `?${q}` : ""}`);
  },
  discoverSites: (projectId: string, region?: string) => {
    const qs = new URLSearchParams();
    if (region) qs.set("region", region);
    const q = qs.toString();
    return fetchApi<CitationSite[]>(`/citations/sites/for-project/${projectId}${q ? `?${q}` : ""}`);
  },

  // Submissions
  listSubmissions: (projectId: string) =>
    fetchApi<CitationSubmission[]>(`/citations/projects/${projectId}/submissions`),
  createSubmission: (projectId: string, data: { site_id: string; status?: string }) =>
    fetchApi<CitationSubmission>(`/citations/projects/${projectId}/submissions`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  bulkCreateSubmissions: (projectId: string, data: { site_ids: string[] }) =>
    fetchApi<CitationSubmission[]>(`/citations/projects/${projectId}/submissions/bulk`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateSubmission: (submissionId: string, data: Partial<CitationSubmission>) =>
    fetchApi<CitationSubmission>(`/citations/submissions/${submissionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  updateSubmissionStatus: (submissionId: string, status: string, notes?: string) =>
    fetchApi<CitationSubmission>(`/citations/submissions/${submissionId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, status_notes: notes }),
    }),

  // Export
  cancelCampaign: (id: string) => fetchApi(`/campaigns/${id}/cancel`, { method: "POST" }),
  enableProvider: (id: string) => fetchApi(`/providers/keys/${id}/enable`, { method: "POST" }),
  disableProvider: (id: string) => fetchApi(`/providers/keys/${id}/disable`, { method: "POST" }),
  testProvider: (id: string) => fetchApi(`/providers/keys/${id}/test`, { method: "POST" }),

  exportCsv: (projectId: string) =>
    fetchApi<Blob>(`/citations/projects/${projectId}/export?format=csv`),
  exportXlsx: (projectId: string) =>
    fetchApi<Blob>(`/citations/projects/${projectId}/export?format=xlsx`),

  // Analytics & Reports (Phase 9)
  getAnalytics: (projectId: string) =>
    fetchApi<ProjectAnalytics>(`/citations/projects/${projectId}/analytics`),
  getGrowthData: (projectId: string, days?: number) => {
    const qs = days ? `?days=${days}` : "";
    return fetchApi<GrowthDataPoint[]>(`/citations/projects/${projectId}/analytics/growth${qs}`);
  },
  getNapConsistency: (projectId: string) =>
    fetchApi<NapConsistencyResult>(`/citations/projects/${projectId}/analytics/nap`),
  getCompetitorComparison: (projectId: string) =>
    fetchApi<CompetitorComparisonResult>(`/citations/projects/${projectId}/analytics/competitors`),
  generateReport: (projectId: string, reportType: string = "monthly") => {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    return fetchApi<{ report_id: string; report_data: ReportData }>(`/citations/projects/${projectId}/reports`, {
      method: "POST",
      body: JSON.stringify({
        report_type: reportType,
        period_start: thirtyDaysAgo.toISOString().split("T")[0],
        period_end: now.toISOString().split("T")[0],
      }),
    });
  },
  listReports: (projectId: string) =>
    fetchApi<ReportListItem[]>(`/citations/projects/${projectId}/reports`),
  getReport: (reportId: string) =>
    fetchApi<ReportListItem>(`/citations/reports/${reportId}`),
  deleteReport: (reportId: string) =>
    fetchApi<void>(`/citations/reports/${reportId}`, { method: "DELETE" }),
  exportReport: (projectId: string, format: "csv" | "txt") =>
    fetchApi<Blob>(`/citations/projects/${projectId}/reports/export?format=${format}`),
  getLatestReport: (projectId: string) =>
    fetchApi<{ report: ReportListItem | null }>(`/citations/projects/${projectId}/reports/latest`),
};

// Phase 9 Types
export interface ProjectAnalytics {
  summary: {
    total_citations: number;
    live_citations: number;
    pending_citations: number;
    failed_citations: number;
    already_exists_citations: number;
    avg_domain_authority: number;
    nap_consistency_score: number;
    total_premium_sites: number;
    high_da_sites: number;
    top_sites: TopSite[];
    growth_last_30_days: number;
  };
  breakdown: {
    statuses: Record<string, number>;
    percentages: Record<string, number>;
    total: number;
  };
  quality: {
    avg_domain_authority: number;
    premium_sites_count: number;
    high_da_count: number;
    quality_score: number;
    top_performing_sites: TopSite[];
    underperforming_sites: TopSite[];
  };
  top_sites: TopSite[];
}

export interface StatusBreakdown {
  status: string;
  count: number;
  percentage: number;
}

export interface QualityMetrics {
  avg_success_rate: number;
  avg_health_score: number;
  active_credentials: number;
  avg_response_time_ms: number;
}

export interface TopSite {
  site_name: string;
  site_url: string;
  domain_authority: number;
  category: string;
  status: string;
  success_rate: number;
  health_score: number;
}

export interface GrowthDataPoint {
  date: string;
  total: number;
  verified: number;
  pending: number;
  failed: number;
}

export interface NapConsistencyResult {
  overall_score: number;
  field_scores: {
    field: string;
    consistency: number;
    expected: string;
    actual: string;
    mismatches: string[];
  }[];
}

export interface CompetitorComparisonResult {
  project: {
    domain_authority: number;
    avg_success_rate: number;
    total_sites: number;
    verified: number;
  };
  competitors: {
    domain_authority: number;
    avg_success_rate: number;
    total_sites: number;
    verified: number;
    gap_score: number;
  }[];
}

export interface ReportListItem {
  id: string;
  project_id: string;
  report_type: string;
  report_name: string;
  period_start: string;
  period_end: string;
  total_citations_start: number;
  total_citations_end: number;
  citations_added: number;
  nap_consistency_score: number;
  avg_domain_authority: number;
  status_breakdown: Record<string, number>;
  competitor_summary: Record<string, unknown>;
  top_sites: TopSite[];
  report_data: ReportData | null;
  generated_at: string;
  created_at?: string;
  generated_by?: string;
  format?: string;
}

export interface ReportData {
  project_id: string;
  period_start: string;
  period_end: string;
  generated_at: string;
  summary: ProjectAnalytics["summary"];
  nap: NapConsistencyResult;
  quality: ProjectAnalytics["quality"];
  competitors: CompetitorComparisonResult;
  growth: GrowthDataPoint[];
  breakdown: ProjectAnalytics["breakdown"];
  top_sites: TopSite[];
}

// ---------------------------------------------------------------------------
// Workflow Status
// ---------------------------------------------------------------------------

export interface WorkflowItem {
  id: string;
  type: string;
  name: string;
  status: string;
  progress: number;
  started: string;
  updated: string;
  next_action: string;
}

export interface WorkflowOverview {
  campaigns: WorkflowItem[];
  citations: WorkflowItem[];
  approvals: WorkflowItem[];
  total_active: number;
}

export const workflowApi = {
  getOverview: () => fetchApi<WorkflowOverview>("/workflow/overview"),
};

// ---------------------------------------------------------------------------
// Failure Recovery
// ---------------------------------------------------------------------------

export interface FailedItem {
  type: string;
  id: string;
  name: string;
  project?: string;
  status: string;
  error?: string;
  count?: number;
  updated_at: string;
}

export interface FailedItemsResponse {
  submissions: FailedItem[];
  credentials: FailedItem[];
  total: number;
}

export interface RetryAllResponse {
  retried_submissions: number;
  retried_credentials: number;
}

export const recoveryApi = {
  listFailedItems: () =>
    fetchApi<FailedItemsResponse>("/recovery/failed"),
  retryItem: (type: string, id: string) =>
    fetchApi(`/recovery/retry/${type}/${id}`, { method: "POST" }),
  retryAllFailed: () =>
    fetchApi<RetryAllResponse>("/recovery/retry-all", { method: "POST" }),
};
