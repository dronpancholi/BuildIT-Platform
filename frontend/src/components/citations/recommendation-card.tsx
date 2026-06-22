"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Check, ExternalLink, X, Star, MapPin, Building2 } from "lucide-react";

interface Recommendation {
  site_id: string;
  site_name: string;
  site_url: string;
  site_category: string | null;
  site_importance: number | null;
  site_region: string | null;
  priority_score: number;
  priority: string;
  reasons: string[];
  scoring_breakdown: {
    location_score: number;
    authority_score: number;
    industry_score: number;
    competitor_score: number;
    tier_score: number;
  };
}

interface RecommendationCardProps {
  recommendation: Recommendation;
  onAccept: (siteId: string) => void;
  onReject: (siteId: string) => void;
  isProcessing?: boolean;
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/20",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/20",
  medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/20",
  low: "bg-slate-500/15 text-slate-400 border-slate-500/20",
};

const PRIORITY_DOTS: Record<string, string> = {
  critical: "bg-red-400",
  high: "bg-orange-400",
  medium: "bg-yellow-400",
  low: "bg-slate-400",
};

export function RecommendationCard({
  recommendation,
  onAccept,
  onReject,
  isProcessing = false,
}: RecommendationCardProps) {
  const { site_name, site_url, site_category, site_importance, site_region, priority_score, priority, reasons, scoring_breakdown } = recommendation;

  return (
    <Card className="border-surface-border bg-surface-card hover:border-platform-500/30 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full shrink-0 ${PRIORITY_DOTS[priority] || "bg-slate-400"}`} />
              <h3 className="text-sm font-medium text-slate-100 truncate">{site_name}</h3>
              <Badge variant="outline" className={`text-[10px] font-mono ${PRIORITY_COLORS[priority] || ""}`}>
                {priority.toUpperCase()}
              </Badge>
            </div>

            {/* URL */}
            <a
              href={site_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-platform-400 hover:underline flex items-center gap-1 mb-2"
            >
              {site_url.replace(/https?:\/\//, "").slice(0, 50)}
              <ExternalLink className="w-3 h-3" />
            </a>

            {/* Meta */}
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500 mb-2">
              {site_category && (
                <span className="flex items-center gap-1">
                  <Building2 className="w-3 h-3" />
                  {site_category}
                </span>
              )}
              {site_region && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {site_region}
                </span>
              )}
              {site_importance != null && (
                <span className="flex items-center gap-1">
                  <Star className="w-3 h-3" />
                  {site_importance}/100
                </span>
              )}
              <span className="font-mono font-bold text-platform-400">
                Score: {priority_score}
              </span>
            </div>

            {/* Reasons */}
            {reasons.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {reasons.map((reason, i) => (
                  <span key={i} className="text-[10px] bg-surface-hover text-slate-400 px-2 py-0.5 rounded">
                    {reason}
                  </span>
                ))}
              </div>
            )}

            {/* Scoring Breakdown */}
            <div className="flex gap-3 text-[10px] text-slate-500">
              <span>Loc: {scoring_breakdown.location_score}</span>
              <span>Auth: {scoring_breakdown.authority_score}</span>
              <span>Ind: {scoring_breakdown.industry_score}</span>
              <span>Comp: {scoring_breakdown.competitor_score}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-1 shrink-0">
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-green-400 border-green-500/20 hover:bg-green-500/10"
              onClick={() => onAccept(recommendation.site_id)}
              disabled={isProcessing}
            >
              <Check className="w-3 h-3" />
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-red-400 border-red-500/20 hover:bg-red-500/10"
              onClick={() => onReject(recommendation.site_id)}
              disabled={isProcessing}
            >
              <X className="w-3 h-3" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
