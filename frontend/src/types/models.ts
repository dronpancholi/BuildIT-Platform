export interface Client {
  id: string;
  tenant_id: string;
  name: string;
  industry: string;
  status: 'active' | 'inactive' | 'archived';
  created_at: string;
  updated_at: string;
}

export interface Campaign {
  id: string;
  tenant_id: string;
  client_id: string;
  name: string;
  platform: string;
  status: 'draft' | 'active' | 'paused' | 'completed';
  budget?: number;
  start_date?: string;
  end_date?: string;
  created_at: string;
  updated_at: string;
}

export interface Keyword {
  id: string;
  tenant_id: string;
  client_id: string;
  campaign_id?: string;
  keyword: string;
  volume?: number;
  difficulty?: number;
  intent?: string;
  created_at: string;
  updated_at: string;
}

export interface Plan {
  id: string;
  tenant_id: string;
  client_id: string;
  name: string;
  status: 'draft' | 'pending_approval' | 'approved' | 'executing' | 'completed';
  objectives?: Record<string, unknown>;
  steps?: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface Approval {
  id: string;
  tenant_id: string;
  plan_id: string;
  status: 'pending' | 'approved' | 'rejected';
  reviewer_id?: string;
  comments?: string;
  created_at: string;
  updated_at: string;
}

export interface Report {
  id: string;
  tenant_id: string;
  client_id: string;
  campaign_id?: string;
  title: string;
  report_type: string;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ReportMetrics {
  total_campaigns: number;
  active_campaigns: number;
  draft_campaigns: number;
  total_prospects: number;
  total_emails_sent: number;
  total_replies: number;
  total_follow_ups: number;
  links_acquired: number;
  target_links: number;
  acquisition_rate: number;
  reply_rate: number;
  avg_health_score: number;
  total_keywords: number;
  total_clusters: number;
}

export interface ReportCampaign {
  id: string;
  name: string;
  status: string;
  campaign_type: string;
  target_link_count: number;
  acquired_link_count: number;
  health_score: number;
  total_prospects: number;
  emails_sent: number;
  replies: number;
  follow_ups: number;
  created_at: string | null;
}

export interface ReportProspect {
  domain: string;
  domain_authority: number;
  relevance_score: number;
  composite_score: number;
  status: string;
  contact_email: string | null;
}

export interface ReportEmail {
  prospect_domain: string;
  subject: string;
  status: string;
  sent_at: string | null;
  replied_at: string | null;
  follow_up_count: number;
}

export interface ReportAcquiredLink {
  source_url: string;
  target_url: string;
  anchor_text: string;
  link_type: string;
  status: string;
  domain_authority: number;
  verified_at: string | null;
}

export interface ReportKeyword {
  keyword: string;
  search_volume: number;
  difficulty: number;
  cpc: number;
  competition: number;
  intent: string;
}

export interface ReportDetail extends Report {
  generated_at: string;
  metrics: ReportMetrics;
  campaigns: ReportCampaign[];
  prospects: ReportProspect[];
  emails: ReportEmail[];
  acquired_links: ReportAcquiredLink[];
  keywords: ReportKeyword[];
  executive_summary: string;
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  name: string;
  role: string;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: 'active' | 'inactive';
  settings?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Goal {
  id: string;
  tenant_id: string;
  client_id: string;
  name: string;
  type: string;
  target_value?: number;
  current_value?: number;
  status: 'active' | 'achieved' | 'expired';
  created_at: string;
  updated_at: string;
}

export interface WorkflowEvent {
  id: string;
  tenant_id: string;
  plan_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  tenant_id: string;
  user_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}
