"use client";

import { MapPin, Star, Gauge, FileText, Globe, GitCompare, Loader2, TrendingUp, CheckCircle2, AlertTriangle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface DirectoryQuality {
  directory: string;
  quality_score: number;
  citation_count: number;
  verification_rate: number;
}

interface AuthorityGauge {
  overall_authority: number;
  citation_consistency: number;
  review_score: number;
  listing_completeness: number;
}

interface NAPConsistency {
  total_listings: number;
  consistent_listings: number;
  inconsistency_count: number;
  consistency_rate: number;
  issues: string[];
}

interface GeographicCitation {
  city: string;
  state: string;
  citation_count: number;
  avg_authority: number;
}

interface CitationOpportunity {
  directory: string;
  opportunity_score: number;
  estimated_impact: string;
  priority: string;
}

interface CompetitorCitation {
  competitor_domain: string;
  total_citations: number;
  top_directories: string[];
  citation_gap: number;
}

function qualityColor(score: number): string {
  if (score >= 0.8) return "text-emerald-400";
  if (score >= 0.6) return "text-amber-400";
  return "text-red-400";
}

function qualityBg(score: number): string {
  if (score >= 0.8) return "bg-emerald-500";
  if (score >= 0.6) return "bg-amber-500";
  return "bg-red-500";
}

export default function LocalSEOPage() {
  const { data: directories, isLoading: loadingDirs } = useQuery<DirectoryQuality[]>({
    queryKey: ["local-seo", "directories", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/citations/directories?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: gauge } = useQuery<AuthorityGauge>({
    queryKey: ["local-seo", "authority", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/citations/authority?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: nap } = useQuery<NAPConsistency>({
    queryKey: ["local-seo", "nap", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/citations/nap-consistency?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: geoCitations, isLoading: loadingGeo } = useQuery<GeographicCitation[]>({
    queryKey: ["local-seo", "geographic", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/citations/geographic?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: opportunities, isLoading: loadingOpps } = useQuery<CitationOpportunity[]>({
    queryKey: ["local-seo", "opportunities", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/citations/opportunities?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: competitors, isLoading: loadingComps } = useQuery<CompetitorCitation[]>({
    queryKey: ["local-seo", "competitors", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/citations/competitors?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const dirList = directories ?? [];
  const geoList = geoCitations ?? [];
  const oppList = opportunities ?? [];
  const compList = competitors ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">LOCAL_SEO</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Local citation & directory intelligence</p>
        </div>
        <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
          <MapPin className="w-4 h-4" />
          {dirList.length} DIRECTORIES
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Directory Quality Scores */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Star className="w-5 h-5 text-amber-500" />
            DIRECTORY_QUALITY
          </h3>
          {loadingDirs ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : dirList.length === 0 ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_DIRECTORY_DATA</div>
          ) : (
            <div className="space-y-3">
              {dirList.map((d, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-300">{d.directory}</span>
                    <span className={`text-xs font-mono font-bold ${qualityColor(d.quality_score)}`}>
                      {Math.round(d.quality_score * 100)}%
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${qualityBg(d.quality_score)}`} style={{ width: `${d.quality_score * 100}%` }} />
                  </div>
                  <div className="flex justify-between text-[9px] font-mono text-slate-600">
                    <span>{d.citation_count} citations</span>
                    <span>{Math.round(d.verification_rate * 100)}% verified</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Local Authority Gauge */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Gauge className="w-5 h-5 text-platform-500" />
            LOCAL_AUTHORITY
          </h3>
          {!gauge ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_AUTHORITY_DATA</div>
          ) : (
            <div className="space-y-4">
              <div className="text-center">
                <span className={`text-5xl font-bold font-mono ${qualityColor(gauge.overall_authority)}`}>
                  {Math.round(gauge.overall_authority * 100)}
                </span>
                <p className="text-xs font-mono text-slate-500 mt-1">/ 100</p>
              </div>
              <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${qualityBg(gauge.overall_authority)}`} style={{ width: `${gauge.overall_authority * 100}%` }} />
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50">
                  <p className="text-xs font-mono text-slate-300">{Math.round(gauge.citation_consistency * 100)}%</p>
                  <p className="text-[8px] font-mono text-slate-600">CONSISTENCY</p>
                </div>
                <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50">
                  <p className="text-xs font-mono text-slate-300">{Math.round(gauge.review_score * 100)}%</p>
                  <p className="text-[8px] font-mono text-slate-600">REVIEWS</p>
                </div>
                <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50">
                  <p className="text-xs font-mono text-slate-300">{Math.round(gauge.listing_completeness * 100)}%</p>
                  <p className="text-[8px] font-mono text-slate-600">COMPLETENESS</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* NAP Consistency */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <FileText className="w-5 h-5 text-emerald-500" />
            NAP_CONSISTENCY
          </h3>
          {!nap ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_NAP_DATA</div>
          ) : (
            <div className="space-y-4">
              <div className="text-center">
                <span className={`text-4xl font-bold font-mono ${qualityColor(nap.consistency_rate)}`}>
                  {Math.round(nap.consistency_rate * 100)}%
                </span>
                <p className="text-xs font-mono text-slate-500 mt-1">CONSISTENCY RATE</p>
              </div>
              <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${nap.consistency_rate * 100}%` }} />
              </div>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50">
                  <p className="text-xs font-mono text-slate-300">{nap.consistent_listings}</p>
                  <p className="text-[8px] font-mono text-slate-600">CONSISTENT</p>
                </div>
                <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50">
                  <p className="text-xs font-mono text-red-400">{nap.inconsistency_count}</p>
                  <p className="text-[8px] font-mono text-slate-600">ISSUES</p>
                </div>
              </div>
              {(nap.issues?.length ?? 0) > 0 && (
                <div className="space-y-1">
                  <p className="text-[9px] font-mono text-slate-500 uppercase">Issues:</p>
                  {nap.issues.map((issue, i) => (
                    <p key={i} className="text-[10px] font-mono text-red-400 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> {issue}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Geographic Citation Map */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Globe className="w-5 h-5 text-cyan-500" />
            GEOGRAPHIC_CITATIONS
          </h3>
          {loadingGeo ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : geoList.length === 0 ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_GEO_DATA</div>
          ) : (
            <div className="space-y-3">
              {geoList.map((g, i) => (
                <div key={i} className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300">{g.city}, {g.state}</span>
                    <span className="text-xs font-mono text-slate-400">{g.citation_count} citations</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                      <div className="h-full bg-cyan-500 rounded-full" style={{ width: `${g.avg_authority * 100}%` }} />
                    </div>
                    <span className="text-[10px] font-mono text-cyan-400">{Math.round(g.avg_authority * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Citation Opportunity Scoring */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <TrendingUp className="w-5 h-5 text-emerald-500" />
            CITATION_OPPORTUNITIES
          </h3>
          {loadingOpps ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : oppList.length === 0 ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_OPPORTUNITY_DATA</div>
          ) : (
            <div className="space-y-2">
              {oppList.map((o, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono text-slate-300 truncate">{o.directory}</p>
                    <p className="text-[9px] font-mono text-slate-600">{o.estimated_impact}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-12 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${o.opportunity_score * 100}%` }} />
                    </div>
                    <span className={`text-[10px] font-mono ${o.opportunity_score >= 0.7 ? "text-emerald-400" : "text-amber-400"}`}>
                      {Math.round(o.opportunity_score * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Competitor Citation Comparison */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <GitCompare className="w-5 h-5 text-purple-500" />
            COMPETITOR_COMPARISON
          </h3>
          {loadingComps ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : compList.length === 0 ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_COMPETITOR_DATA</div>
          ) : (
            <div className="space-y-3">
              {compList.map((c, i) => (
                <div key={i} className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 truncate max-w-[120px]">{c.competitor_domain}</span>
                    <span className="text-xs font-mono text-slate-400">{c.total_citations} citations</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500 rounded-full" style={{ width: `${Math.min(c.citation_gap * 10, 100)}%` }} />
                    </div>
                    <span className="text-[10px] font-mono text-purple-400">GAP: {c.citation_gap}</span>
                  </div>
                  <p className="text-[9px] font-mono text-slate-600 mt-1 truncate">
                    Top: {c.top_directories.slice(0, 2).join(", ")}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
