"use client";

import { useState, useEffect, useCallback } from "react";
import type {
  Campaign,
  CampaignStatus,
  BatchRunResult,
} from "@/lib/types";
import {
  fetchCampaignProgress,
  activateCampaign,
  pauseCampaign,
  runCampaignBatch,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Play,
  Pause,
  Rocket,
  ArrowLeft,
  Users,
  Target,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  Loader2,
  RefreshCw,
  CalendarClock,
  Send,
} from "lucide-react";
import { toast } from "sonner";

const STATUS_STYLES: Record<CampaignStatus, string> = {
  draft: "bg-clay-500/15 text-clay-500 border-clay-500/30",
  active: "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30",
  paused: "bg-kiln-mustard/15 text-kiln-mustard border-kiln-mustard/30",
  completed: "bg-clay-400/15 text-clay-400 border-clay-400/30",
};

interface CampaignDetailProps {
  campaign: Campaign;
  onBack: () => void;
  onRefresh: () => void;
}

export function CampaignDetail({
  campaign,
  onBack,
  onRefresh,
}: CampaignDetailProps) {
  const [status, setStatus] = useState<CampaignStatus>(campaign.status);
  const [progress, setProgress] = useState(campaign.progress);
  const [audienceTotal, setAudienceTotal] = useState(
    campaign.audience?.length ?? 0
  );
  const [audienceCursor, setAudienceCursor] = useState(
    campaign.audience_cursor
  );
  const [audienceRemaining, setAudienceRemaining] = useState(0);
  const [reviewStats, setReviewStats] = useState(campaign.review_stats);
  const [runningBatch, setRunningBatch] = useState(false);
  const [activating, setActivating] = useState(false);
  const [lastBatchResult, setLastBatchResult] =
    useState<BatchRunResult | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadProgress = useCallback(async () => {
    try {
      const data = await fetchCampaignProgress(campaign.id);
      setStatus(data.status as CampaignStatus);
      setProgress(data.progress);
      setAudienceTotal(data.audience_total);
      setAudienceCursor(data.audience_cursor);
      setAudienceRemaining(data.audience_remaining);
      setReviewStats(data.review_stats);
    } catch {
      // Silently fail on progress refresh
    }
  }, [campaign.id]);

  useEffect(() => {
    loadProgress();
    const interval = setInterval(loadProgress, 10000);
    return () => clearInterval(interval);
  }, [loadProgress]);

  const handleActivate = async () => {
    setActivating(true);
    try {
      const res = await activateCampaign(campaign.id);
      setStatus(res.status as CampaignStatus);
      toast.success("Campaign activated");
      onRefresh();
    } catch (e) {
      toast.error("Failed to activate", {
        description: (e as Error).message,
      });
    } finally {
      setActivating(false);
    }
  };

  const handlePause = async () => {
    setActivating(true);
    try {
      const res = await pauseCampaign(campaign.id);
      setStatus(res.status as CampaignStatus);
      toast.success("Campaign paused");
      onRefresh();
    } catch (e) {
      toast.error("Failed to pause", {
        description: (e as Error).message,
      });
    } finally {
      setActivating(false);
    }
  };

  const handleRunBatch = async () => {
    setRunningBatch(true);
    try {
      const result = await runCampaignBatch(campaign.id);
      setLastBatchResult(result);
      toast.success("Batch run complete", {
        description: `${result.auto_sent} auto-sent, ${result.queued_for_review} queued for review`,
      });
      loadProgress();
      onRefresh();
    } catch (e) {
      toast.error("Batch run failed", {
        description: (e as Error).message,
      });
    } finally {
      setRunningBatch(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadProgress();
    setRefreshing(false);
  };

  const goalTarget = campaign.goal.target_count || 1;
  const goalPct = Math.min((progress.total_sent / goalTarget) * 100, 100);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={onBack}
            className="h-8 w-8 text-clay-400 hover:text-clay-200"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold text-clay-100 font-[family-name:var(--font-sans)]">
                {campaign.name}
              </h3>
              <Badge variant="outline" className={STATUS_STYLES[status]}>
                {status}
              </Badge>
            </div>
            {campaign.description && (
              <p className="text-sm text-clay-500 mt-0.5">
                {campaign.description}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            className="h-8 w-8 text-clay-400 hover:text-clay-200"
            disabled={refreshing}
          >
            <RefreshCw
              className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
            />
          </Button>
          {(status === "draft" || status === "paused") && (
            <Button
              size="sm"
              onClick={handleActivate}
              disabled={activating}
              className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              {activating ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5 mr-1.5" />
              )}
              Activate
            </Button>
          )}
          {status === "active" && (
            <Button
              size="sm"
              variant="outline"
              onClick={handlePause}
              disabled={activating}
              className="border-kiln-mustard/30 text-kiln-mustard hover:bg-kiln-mustard/10"
            >
              {activating ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <Pause className="h-3.5 w-3.5 mr-1.5" />
              )}
              Pause
            </Button>
          )}
          {status !== "completed" && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleRunBatch}
              disabled={runningBatch}
              className="border-clay-700 text-clay-300 hover:bg-clay-800 hover:text-clay-100"
            >
              {runningBatch ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <Rocket className="h-3.5 w-3.5 mr-1.5" />
              )}
              Run Batch
            </Button>
          )}
        </div>
      </div>

      {/* Progress Section */}
      <Card className="border-clay-800 bg-clay-900">
        <CardContent className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-clay-300 uppercase tracking-wide">
              Goal Progress
            </h4>
            <span className="text-sm text-clay-400">
              {progress.total_sent} / {goalTarget}{" "}
              <span className="text-clay-500">{campaign.goal.metric}</span>
            </span>
          </div>

          <div className="h-3 bg-clay-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-kiln-teal rounded-full transition-all duration-700"
              style={{ width: `${goalPct}%` }}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="rounded-lg bg-clay-800/50 p-3 text-center">
              <div className="text-2xl font-bold text-clay-100">
                {progress.total_processed}
              </div>
              <div className="text-xs text-clay-500 flex items-center justify-center gap-1 mt-1">
                <Clock className="h-3 w-3" />
                Processed
              </div>
            </div>
            <div className="rounded-lg bg-clay-800/50 p-3 text-center">
              <div className="text-2xl font-bold text-kiln-teal">
                {progress.total_approved}
              </div>
              <div className="text-xs text-clay-500 flex items-center justify-center gap-1 mt-1">
                <CheckCircle className="h-3 w-3" />
                Approved
              </div>
            </div>
            <div className="rounded-lg bg-clay-800/50 p-3 text-center">
              <div className="text-2xl font-bold text-clay-100">
                {progress.total_sent}
              </div>
              <div className="text-xs text-clay-500 flex items-center justify-center gap-1 mt-1">
                <Send className="h-3 w-3" />
                Sent
              </div>
            </div>
            <div className="rounded-lg bg-clay-800/50 p-3 text-center">
              <div className="text-2xl font-bold text-kiln-coral">
                {progress.total_rejected}
              </div>
              <div className="text-xs text-clay-500 flex items-center justify-center gap-1 mt-1">
                <XCircle className="h-3 w-3" />
                Rejected
              </div>
            </div>
            <div className="rounded-lg bg-clay-800/50 p-3 text-center">
              <div className="text-2xl font-bold text-kiln-mustard">
                {progress.total_pending_review}
              </div>
              <div className="text-xs text-clay-500 flex items-center justify-center gap-1 mt-1">
                <Eye className="h-3 w-3" />
                Pending Review
              </div>
            </div>
          </div>

          {/* Approval Rate */}
          {progress.total_processed > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <CheckCircle className="h-4 w-4 text-kiln-teal" />
              <span className="text-clay-300">
                Approval Rate:{" "}
                <span className="font-semibold text-kiln-teal">
                  {(progress.approval_rate * 100).toFixed(1)}%
                </span>
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Audience + Schedule row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Audience */}
        <Card className="border-clay-800 bg-clay-900">
          <CardContent className="p-5 space-y-3">
            <h4 className="text-sm font-medium text-clay-300 uppercase tracking-wide flex items-center gap-1.5">
              <Users className="h-4 w-4" />
              Audience
            </h4>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="text-xl font-bold text-clay-100">
                  {audienceTotal}
                </div>
                <div className="text-[10px] text-clay-500 uppercase">Total</div>
              </div>
              <div>
                <div className="text-xl font-bold text-kiln-teal">
                  {audienceCursor}
                </div>
                <div className="text-[10px] text-clay-500 uppercase">
                  Cursor
                </div>
              </div>
              <div>
                <div className="text-xl font-bold text-clay-300">
                  {audienceRemaining}
                </div>
                <div className="text-[10px] text-clay-500 uppercase">
                  Remaining
                </div>
              </div>
            </div>
            {audienceTotal > 0 && (
              <div className="h-1.5 bg-clay-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-kiln-teal/60 rounded-full transition-all duration-500"
                  style={{
                    width: `${
                      audienceTotal > 0
                        ? ((audienceCursor / audienceTotal) * 100).toFixed(1)
                        : 0
                    }%`,
                  }}
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Schedule + Config */}
        <Card className="border-clay-800 bg-clay-900">
          <CardContent className="p-5 space-y-3">
            <h4 className="text-sm font-medium text-clay-300 uppercase tracking-wide flex items-center gap-1.5">
              <CalendarClock className="h-4 w-4" />
              Configuration
            </h4>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-clay-500">Pipeline</span>
                <Badge
                  variant="outline"
                  className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 text-xs"
                >
                  {campaign.pipeline}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-clay-500">Frequency</span>
                <span className="text-clay-200">
                  {campaign.schedule.frequency}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-clay-500">Batch Size</span>
                <span className="text-clay-200">
                  {campaign.schedule.batch_size}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-clay-500">Confidence Threshold</span>
                <span className="text-clay-200">
                  {(campaign.confidence_threshold * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-clay-500">Model</span>
                <span className="text-clay-200">{campaign.model}</span>
              </div>
              {campaign.client_slug && (
                <div className="flex items-center justify-between">
                  <span className="text-clay-500">Client</span>
                  <span className="text-clay-200">{campaign.client_slug}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Review Stats */}
      {reviewStats && reviewStats.total > 0 && (
        <Card className="border-clay-800 bg-clay-900">
          <CardContent className="p-5 space-y-3">
            <h4 className="text-sm font-medium text-clay-300 uppercase tracking-wide flex items-center gap-1.5">
              <Eye className="h-4 w-4" />
              Review Queue
            </h4>
            <div className="grid grid-cols-5 gap-2 text-center">
              <div>
                <div className="text-lg font-bold text-clay-100">
                  {reviewStats.total}
                </div>
                <div className="text-[10px] text-clay-500 uppercase">Total</div>
              </div>
              <div>
                <div className="text-lg font-bold text-kiln-mustard">
                  {reviewStats.pending}
                </div>
                <div className="text-[10px] text-clay-500 uppercase">
                  Pending
                </div>
              </div>
              <div>
                <div className="text-lg font-bold text-kiln-teal">
                  {reviewStats.approved}
                </div>
                <div className="text-[10px] text-clay-500 uppercase">
                  Approved
                </div>
              </div>
              <div>
                <div className="text-lg font-bold text-kiln-coral">
                  {reviewStats.rejected}
                </div>
                <div className="text-[10px] text-clay-500 uppercase">
                  Rejected
                </div>
              </div>
              <div>
                <div className="text-lg font-bold text-clay-300">
                  {reviewStats.revised}
                </div>
                <div className="text-[10px] text-clay-500 uppercase">
                  Revised
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Last Batch Result */}
      {lastBatchResult && (
        <Card className="border-clay-800 bg-clay-900">
          <CardContent className="p-5 space-y-3">
            <h4 className="text-sm font-medium text-clay-300 uppercase tracking-wide flex items-center gap-1.5">
              <Rocket className="h-4 w-4" />
              Last Batch Result
            </h4>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg bg-clay-800/50 p-3">
                <div className="text-xl font-bold text-clay-100">
                  {lastBatchResult.batch_size}
                </div>
                <div className="text-xs text-clay-500">Batch Size</div>
              </div>
              <div className="rounded-lg bg-clay-800/50 p-3">
                <div className="text-xl font-bold text-kiln-teal">
                  {lastBatchResult.auto_sent}
                </div>
                <div className="text-xs text-clay-500">Auto-Sent</div>
              </div>
              <div className="rounded-lg bg-clay-800/50 p-3">
                <div className="text-xl font-bold text-kiln-mustard">
                  {lastBatchResult.queued_for_review}
                </div>
                <div className="text-xs text-clay-500">Queued for Review</div>
              </div>
            </div>

            {/* Individual results */}
            {lastBatchResult.results.length > 0 && (
              <div className="mt-3 max-h-48 overflow-y-auto space-y-1">
                {lastBatchResult.results.map((r, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-xs px-2 py-1.5 rounded bg-clay-800/30"
                  >
                    <span className="text-clay-400">Row {r.row_index}</span>
                    <div className="flex items-center gap-2">
                      {r.confidence !== undefined && (
                        <span className="text-clay-500">
                          {(r.confidence * 100).toFixed(0)}% conf
                        </span>
                      )}
                      <Badge
                        variant="outline"
                        className={
                          r.routing === "auto_sent"
                            ? "bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30"
                            : r.routing === "review"
                              ? "bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30"
                              : "bg-kiln-coral/10 text-kiln-coral border-kiln-coral/30"
                        }
                      >
                        {r.routing}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Campaign metadata */}
      <div className="flex items-center justify-between text-xs text-clay-600">
        <span>
          Created{" "}
          {new Date(campaign.created_at * 1000).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
        <span>
          Updated{" "}
          {new Date(campaign.updated_at * 1000).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
      </div>
    </div>
  );
}
