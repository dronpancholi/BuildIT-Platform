"use client";

import { useState } from "react";
import {
  CheckCircle2,
  Clock,
  ExternalLink,
  Inbox,
  Loader2,
  Mail,
  Play,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fetchApi } from "@/lib/api";

interface VerificationPanelProps {
  submissionId: string;
  siteName: string;
  siteDomain: string;
  emailVerified: boolean;
  onVerified?: () => void;
}

interface CheckEmailResult {
  email_found: boolean;
  links: string[];
  confirmation_text: string | null;
  error_text: string | null;
}

interface VerifyEmailResult {
  success: boolean;
  status: string;
  email_found: boolean;
  link_clicked: boolean;
  link_url: string | null;
  confirmation_text: string | null;
  error_text: string | null;
  verification_time_seconds: number;
  screenshot: string | null;
  redirect_chain: string[];
}

export function VerificationPanel({
  submissionId,
  siteName,
  siteDomain,
  emailVerified,
  onVerified,
}: VerificationPanelProps) {
  const [isChecking, setIsChecking] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [checkResult, setCheckResult] = useState<CheckEmailResult | null>(null);
  const [verifyResult, setVerifyResult] = useState<VerifyEmailResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showScreenshot, setShowScreenshot] = useState(false);

  const handleCheckEmail = async () => {
    try {
      setIsChecking(true);
      setError(null);
      setCheckResult(null);

      const result = await fetchApi<CheckEmailResult>(
        `/citations/verification/submissions/${submissionId}/check-email`,
        { method: "POST" }
      );

      setCheckResult(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to check email");
    } finally {
      setIsChecking(false);
    }
  };

  const handleVerifyEmail = async () => {
    try {
      setIsVerifying(true);
      setError(null);
      setVerifyResult(null);

      const result = await fetchApi<VerifyEmailResult>(
        `/citations/verification/submissions/${submissionId}/verify-email?max_wait_seconds=300&poll_interval_seconds=30`,
        {
          method: "POST",
          body: JSON.stringify({ max_wait_seconds: 300, poll_interval_seconds: 30 }),
        }
      );

      setVerifyResult(result);
      if (result.success) {
        onVerified?.();
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setIsVerifying(false);
    }
  };

  if (emailVerified) {
    return (
      <Card className="border-emerald-500/20 bg-emerald-500/5">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <div>
              <p className="text-sm font-medium text-emerald-400">Email Verified</p>
              <p className="text-xs text-slate-500">
                Verification completed for {siteName}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Mail className="w-4 h-4" />
          Email Verification
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status */}
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-400" />
          <span className="text-sm text-slate-300">Awaiting Verification</span>
          <Badge variant="outline" className="text-[10px] ml-auto">
            {siteDomain}
          </Badge>
        </div>

        {/* Verification Result */}
        {verifyResult && (
          <div
            className={`p-3 rounded-lg border ${
              verifyResult.success
                ? "border-emerald-500/20 bg-emerald-500/5"
                : "border-red-500/20 bg-red-500/5"
            }`}
          >
            <div className="flex items-center gap-2">
              {verifyResult.success ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="text-sm font-medium">
                {verifyResult.success ? "Verified" : "Failed"}
              </span>
            </div>
            {verifyResult.confirmation_text && (
              <p className="text-xs text-slate-400 mt-1">
                {verifyResult.confirmation_text}
              </p>
            )}
            {verifyResult.error_text && (
              <p className="text-xs text-red-400/70 mt-1">{verifyResult.error_text}</p>
            )}
            {verifyResult.link_url && (
              <a
                href={verifyResult.link_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-platform-400 hover:underline mt-1 inline-flex items-center gap-1"
              >
                <ExternalLink className="w-3 h-3" />
                Verification Link
              </a>
            )}
            {verifyResult.verification_time_seconds > 0 && (
              <p className="text-[10px] text-slate-500 mt-2">
                Completed in {verifyResult.verification_time_seconds.toFixed(1)}s
              </p>
            )}
          </div>
        )}

        {/* Check Result */}
        {checkResult && !verifyResult && (
          <div className="p-3 rounded-lg border border-surface-border bg-surface-darker/50">
            {checkResult.email_found ? (
              <>
                <div className="flex items-center gap-2">
                  <Inbox className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm text-emerald-400">
                    Verification email found
                  </span>
                </div>
                {checkResult.links.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-slate-500">Links extracted:</p>
                    {checkResult.links.map((link, i) => (
                      <a
                        key={i}
                        href={link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-platform-400 hover:underline block truncate"
                      >
                        {link}
                      </a>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Inbox className="w-4 h-4 text-slate-500" />
                <span className="text-sm text-slate-400">
                  No verification email found yet
                </span>
              </div>
            )}
          </div>
        )}

        {/* Screenshot */}
        {verifyResult?.screenshot && showScreenshot && (
          <div className="mt-2">
            <img
              src={`data:image/png;base64,${verifyResult.screenshot}`}
              alt="Verification screenshot"
              className="w-full rounded-lg border border-surface-border"
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg border border-red-500/20 bg-red-500/5">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleCheckEmail}
            disabled={isChecking || isVerifying}
          >
            {isChecking ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Inbox className="w-4 h-4 mr-1" />
            )}
            Check Inbox
          </Button>
          <Button
            size="sm"
            onClick={handleVerifyEmail}
            disabled={isChecking || isVerifying}
          >
            {isVerifying ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Play className="w-4 h-4 mr-1" />
            )}
            Auto-Verify
          </Button>
          {verifyResult?.screenshot && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowScreenshot(!showScreenshot)}
            >
              {showScreenshot ? "Hide" : "Show"} Screenshot
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
