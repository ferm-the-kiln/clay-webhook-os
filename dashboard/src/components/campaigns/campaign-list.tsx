"use client";

import type { Campaign, CampaignStatus } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Play,
  Pause,
  Trash2,
  Rocket,
  Eye,
  Users,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";

const STATUS_STYLES: Record<CampaignStatus, string> = {
  draft: "bg-clay-500/15 text-clay-500 border-clay-500/30",
  active: "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30",
  paused: "bg-kiln-mustard/15 text-kiln-mustard border-kiln-mustard/30",
  completed: "bg-clay-400/15 text-clay-400 border-clay-400/30",
};

interface CampaignListProps {
  campaigns: Campaign[];
  onView: (campaign: Campaign) => void;
  onActivate: (campaign: Campaign) => void;
  onPause: (campaign: Campaign) => void;
  onRunBatch: (campaign: Campaign) => void;
  onDelete: (campaign: Campaign) => void;
}

export function CampaignList({
  campaigns,
  onView,
  onActivate,
  onPause,
  onRunBatch,
  onDelete,
}: CampaignListProps) {
  if (campaigns.length === 0) {
    return (
      <EmptyState
        title="No campaigns yet"
        description="Create your first campaign to start processing audience rows through a pipeline automatically."
      />
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {campaigns.map((campaign) => {
        const { progress, goal } = campaign;
        const goalTarget = goal.target_count || 1;
        const progressPct = Math.min(
          (progress.total_sent / goalTarget) * 100,
          100
        );
        const audienceSize = campaign.audience?.length ?? 0;

        return (
          <Card
            key={campaign.id}
            className="border-clay-800 bg-clay-900 flex flex-col hover:border-clay-700 transition-colors"
          >
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <button
                    onClick={() => onView(campaign)}
                    className="text-left group"
                  >
                    <h4 className="font-semibold text-clay-100 truncate group-hover:text-kiln-teal transition-colors">
                      {campaign.name}
                    </h4>
                  </button>
                  {campaign.description && (
                    <p className="text-xs text-clay-500 mt-0.5 line-clamp-2">
                      {campaign.description}
                    </p>
                  )}
                </div>
                <Badge
                  variant="outline"
                  className={STATUS_STYLES[campaign.status]}
                >
                  {campaign.status}
                </Badge>
              </div>

              {/* Pipeline tag */}
              <div className="mt-2">
                <Badge
                  variant="outline"
                  className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 text-xs"
                >
                  {campaign.pipeline}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="pt-0 mt-auto space-y-3">
              {/* Progress bar */}
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-clay-400">Goal Progress</span>
                  <span className="text-clay-300 font-medium">
                    {progress.total_sent} / {goalTarget}{" "}
                    <span className="text-clay-500">{goal.metric}</span>
                  </span>
                </div>
                <div className="h-2 bg-clay-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-kiln-teal rounded-full transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>

              {/* Stats row */}
              <div className="grid grid-cols-4 gap-1 text-center">
                <div className="rounded-md bg-clay-800/50 px-1 py-1.5">
                  <div className="text-xs font-medium text-clay-200">
                    {progress.total_processed}
                  </div>
                  <div className="text-[10px] text-clay-500 flex items-center justify-center gap-0.5">
                    <Clock className="h-2.5 w-2.5" />
                    proc
                  </div>
                </div>
                <div className="rounded-md bg-clay-800/50 px-1 py-1.5">
                  <div className="text-xs font-medium text-kiln-teal">
                    {progress.total_approved}
                  </div>
                  <div className="text-[10px] text-clay-500 flex items-center justify-center gap-0.5">
                    <CheckCircle className="h-2.5 w-2.5" />
                    ok
                  </div>
                </div>
                <div className="rounded-md bg-clay-800/50 px-1 py-1.5">
                  <div className="text-xs font-medium text-clay-200">
                    {progress.total_sent}
                  </div>
                  <div className="text-[10px] text-clay-500 flex items-center justify-center gap-0.5">
                    <Rocket className="h-2.5 w-2.5" />
                    sent
                  </div>
                </div>
                <div className="rounded-md bg-clay-800/50 px-1 py-1.5">
                  <div className="text-xs font-medium text-kiln-mustard">
                    {progress.total_pending_review}
                  </div>
                  <div className="text-[10px] text-clay-500 flex items-center justify-center gap-0.5">
                    <Eye className="h-2.5 w-2.5" />
                    review
                  </div>
                </div>
              </div>

              {/* Approval rate + Audience */}
              <div className="flex items-center justify-between text-xs text-clay-400">
                <span className="flex items-center gap-1">
                  {progress.approval_rate > 0 ? (
                    <>
                      <CheckCircle className="h-3 w-3 text-kiln-teal" />
                      {(progress.approval_rate * 100).toFixed(0)}% approval
                    </>
                  ) : (
                    <span className="text-clay-500">No data yet</span>
                  )}
                </span>
                <span className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {audienceSize} audience
                </span>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-1 pt-1 border-t border-clay-800">
                {(campaign.status === "draft" ||
                  campaign.status === "paused") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-kiln-teal hover:bg-kiln-teal/10 hover:text-kiln-teal"
                    onClick={() => onActivate(campaign)}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Activate
                  </Button>
                )}
                {campaign.status === "active" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-kiln-mustard hover:bg-kiln-mustard/10 hover:text-kiln-mustard"
                    onClick={() => onPause(campaign)}
                  >
                    <Pause className="h-3 w-3 mr-1" />
                    Pause
                  </Button>
                )}
                {campaign.status !== "completed" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-clay-400 hover:bg-clay-800 hover:text-clay-200"
                    onClick={() => onRunBatch(campaign)}
                  >
                    <Rocket className="h-3 w-3 mr-1" />
                    Run Batch
                  </Button>
                )}
                <div className="flex-1" />
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-clay-400 hover:bg-clay-800 hover:text-clay-200"
                  onClick={() => onView(campaign)}
                >
                  <Eye className="h-3 w-3 mr-1" />
                  View
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-clay-500 hover:text-kiln-coral"
                  onClick={() => onDelete(campaign)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
