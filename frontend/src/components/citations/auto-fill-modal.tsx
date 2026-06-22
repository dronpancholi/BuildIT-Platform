"use client";

import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Globe,
  Loader2,
  Play,
  Pause,
  RotateCcw,
  Camera,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fetchApi } from "@/lib/api";

interface AutoFillResult {
  filled_fields: string[];
  unfilled_fields: string[];
  screenshot_before: string | null;
  screenshot_after: string | null;
  page_url: string;
  listing_url: string | null;
}

interface AutoFillModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  submissionId: string;
  siteName: string;
  siteUrl: string;
  onComplete?: () => void;
}

export function AutoFillModal({
  open,
  onOpenChange,
  submissionId,
  siteName,
  siteUrl,
  onComplete,
}: AutoFillModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AutoFillResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showBefore, setShowBefore] = useState(false);

  const handleAutoFill = async () => {
    try {
      setIsLoading(true);
      setError(null);
      setResult(null);

      const response = await fetchApi<{ success: boolean; data: AutoFillResult }>(
        `/citations/automation/submissions/${submissionId}/auto-fill?take_screenshot=true`,
        { method: "POST", body: JSON.stringify({ take_screenshot: true }) }
      );

      setResult(response.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Auto-fill failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setResult(null);
    setError(null);
    onOpenChange(false);
    onComplete?.();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="font-mono flex items-center gap-2">
            <Globe className="w-5 h-5 text-platform-400" />
            AUTO-FILL: {siteName}
          </DialogTitle>
          <DialogDescription>
            Semi-automated form filling for this citation site.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4">
          {/* Site Info */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-200">{siteName}</p>
                  <div className="flex items-center gap-1 text-xs text-slate-500 mt-1">
                    <Globe className="w-3 h-3" />
                    <a
                      href={siteUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-platform-400"
                    >
                      {siteUrl}
                    </a>
                    <ExternalLink className="w-3 h-3" />
                  </div>
                </div>
                <Badge variant="outline" className="text-xs">
                  Phase 2
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Browser Preview (placeholder) */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-400">
                Browser Preview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="aspect-video bg-surface-darker rounded-lg border border-surface-border flex items-center justify-center">
                {isLoading ? (
                  <div className="text-center">
                    <Loader2 className="w-8 h-8 text-platform-400 animate-spin mx-auto" />
                    <p className="text-sm text-slate-400 mt-2">
                      Launching browser and navigating...
                    </p>
                  </div>
                ) : result ? (
                  <div className="text-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                    <p className="text-sm text-slate-400 mt-2">
                      Form filled successfully
                    </p>
                    {result.page_url && (
                      <a
                        href={result.page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-platform-400 hover:underline mt-1 inline-block"
                      >
                        Open in browser →
                      </a>
                    )}
                  </div>
                ) : (
                  <div className="text-center">
                    <Globe className="w-8 h-8 text-slate-600 mx-auto" />
                    <p className="text-sm text-slate-500 mt-2">
                      Click &quot;Auto-Fill Form&quot; to begin
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Field Mapping Status */}
          {result && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-400">
                  Field Mapping Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {result.filled_fields.map((field) => (
                  <div key={field} className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-slate-300">{field}</span>
                    <Badge variant="outline" className="text-[10px] ml-auto">
                      Filled
                    </Badge>
                  </div>
                ))}
                {result.unfilled_fields.map((field) => (
                  <div key={field} className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span className="text-sm text-slate-400">{field}</span>
                    <Badge variant="outline" className="text-[10px] ml-auto border-amber-500/30 text-amber-400">
                      Not Found
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Screenshots */}
          {result?.screenshot_after && (
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs font-mono uppercase tracking-wider text-slate-400">
                    Screenshot
                  </CardTitle>
                  {result.screenshot_before && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowBefore(!showBefore)}
                      className="text-xs"
                    >
                      <RotateCcw className="w-3 h-3 mr-1" />
                      {showBefore ? "After" : "Before"}
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <img
                  src={`data:image/png;base64,${
                    showBefore ? result.screenshot_before : result.screenshot_after
                  }`}
                  alt="Browser screenshot"
                  className="w-full rounded-lg border border-surface-border"
                />
              </CardContent>
            </Card>
          )}

          {/* Error */}
          {error && (
            <Card className="border-red-500/20 bg-red-500/5">
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-red-400" />
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose}>
            Close
          </Button>
          {!result && (
            <Button onClick={handleAutoFill} disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Auto-Fill Form
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
