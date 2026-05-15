export interface CampaignIntelligence {
  id: string;
  name: string;
  status: string;
  campaign_type: string;
  health_score: number;
  acquisition_rate: number;
  reply_rate: number;
  target_link_count: number;
  acquired_link_count: number;
  total_prospects: number;
  total_emails_sent: number;
  progress: number;
  trends: CampaignHealthTrend[];
  created_at: string | null;
  updated_at: string | null;
}

export interface CampaignHealthTrend {
  health_score: number;
  momentum: number;
  velocity: number;
  snapshot_data?: {
    outreach_health?: number;
    freshness_health?: number;
    keyword_health?: number;
    operational_health?: number;
    seo_health?: number;
    acquisition_score?: number;
    deliverability_score?: number;
    reply_score?: number;
    progress_score?: number;
    freshness_score?: number;
    recency_score?: number;
    cluster_coverage?: number;
    event_activity?: number;
    recommendation_flow?: number;
    seo_activity?: number;
    serp_presence?: number;
    [key: string]: any;
  };
  captured_at: string | null;
}

export interface KeywordIntelligence {
  id: string;
  keyword: string;
  search_volume: number;
  difficulty: number;
  cpc: number;
  competition: number;
  intent: string | null;
  serp_features: string[];
  cluster_id: string | null;
  is_seed: boolean;
}

export interface ClusterIntelligence {
  id: string;
  name: string;
  primary_keyword: string;
  total_volume: number;
  avg_difficulty: number;
  dominant_intent: string | null;
  keyword_count: number;
  confidence_score: number;
  status: string;
  ai_rationale: string | null;
}

export interface IntelligenceEvent {
  id: string;
  event_type: string;
  domain: string;
  severity: string;
  title: string;
  description: string;
  entity_id: string | null;
  entity_type: string | null;
  delta: Record<string, any>;
  action_required: boolean;
  acknowledged: boolean;
  occurred_at: string | null;
}

export interface Recommendation {
  id: string;
  recommendation_type: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  confidence: number;
  impact_score: number;
  effort_score: number;
  entity_id: string | null;
  entity_type: string | null;
  supporting_data: Record<string, any>;
  created_at: string | null;
  updated_at: string | null;
}

export interface SerpVolatility {
  keyword: string;
  geo: string | null;
  volatility_score: number;
  url_churn: number;
  position_changes: number;
  feature_changes: string[];
  top_10_domains: string[];
  captured_at: string | null;
}

export interface IntelligenceOverview {
  campaigns: {
    active: number;
    draft: number;
    complete: number;
    avg_health: number;
    total_links_acquired: number;
    total_prospects: number;
  };
  keywords: {
    total: number;
    avg_search_volume: number;
  };
  intelligence: {
    events_24h: number;
    pending_actions: number;
  };
  recommendations: {
    active: number;
  };
  timestamp: string;
}

export interface KeywordOpportunity {
  keyword: string;
  search_volume: number;
  difficulty: number;
  cpc: number;
  opportunity_score: number;
  serp_features: string[];
  cluster: string | null;
}

export interface ClusterAuthority {
  name: string;
  total_volume: number;
  avg_difficulty: number;
  keyword_count: number;
  authority: number;
  opportunity: number;
  primary_keyword: string;
  color: string;
}

export interface ClusterVisualizationNode {
  id: string;
  name: string;
  cluster: string;
  volume: number;
  difficulty: number;
  opportunity: number;
  x: number;
  y: number;
}

export interface ClusterVisualizationEdge {
  source: string;
  target: string;
  weight: number;
}

export interface ClusterVisualization {
  nodes: ClusterVisualizationNode[];
  edges: ClusterVisualizationEdge[];
  clusters: ClusterAuthority[];
}
