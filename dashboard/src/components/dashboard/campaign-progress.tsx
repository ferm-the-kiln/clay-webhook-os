"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Megaphone, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, formatNumber, formatPercent } from "@/lib/utils";
import type { OutcomeDashboard, CampaignStatus } from "@/lib/types";

interface CampaignProgressProps {
  campaigns: OutcomeDashboard["campaigns"];
}

const STATUS_STYLES: Record<CampaignStatus, string> = {
  draft: "bg-clay-700 text-clay-300 border-clay-600",
  active: "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30",
  paused: "bg-kiln-mustard/15 text-kiln-mustard border-kiln-mustard/30",
  completed: "bg-clay-700 text-clay-400 border-clay-600",
};

export function CampaignProgress({ campaigns }: CampaignProgressProps) {
  const activeCampaigns = campaigns.filter(
    (c) => c.status === "active" || c.status === "paused"
  );

  if (activeCampaigns.length === 0) {
    return (
      <Card className="bg-clay-800 border-clay-700">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Megaphone className="h-8 w-8 text-clay-600 mb-3" />
            <p className="text-clay-400 text-sm mb-1">
              No active campaigns
            </p>
            <p className="text-clay-500 text-xs mb-4">
              Create a campaign to start tracking outcomes
            </p>
            <Link
              href="/campaigns"
              className="inline-flex items-center gap-1.5 text-xs text-kiln-teal hover:text-kiln-teal-light transition-colors"
            >
              Go to Campaigns
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-xs text-clay-500 uppercase tracking-wide font-[family-name:var(--font-sans)]">
        Active Campaigns
      </h3>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {activeCampaigns.map((campaign, index) => {
          const targetCount = campaign.goal.target_count || 1;
          const progressPercent = Math.min(
            (campaign.progress.total_sent / targetCount) * 100,
            100
          );

          return (
            <motion.div
              key={campaign.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <Card className="bg-clay-800 border-clay-700 hover:border-clay-600 transition-all duration-200">
                <CardContent className="p-5">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="min-w-0 flex-1">
                      <h4 className="text-sm font-medium text-clay-100 truncate font-[family-name:var(--font-sans)]">
                        {campaign.name}
                      </h4>
                      <p className="text-xs text-clay-500 mt-0.5 truncate">
                        {campaign.pipeline}
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className={cn(
                        "ml-2 shrink-0",
                        STATUS_STYLES[campaign.status]
                      )}
                    >
                      {campaign.status}
                    </Badge>
                  </div>

                  {/* Progress bar */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs text-clay-400">
                        {formatNumber(campaign.progress.total_sent)} /{" "}
                        {formatNumber(targetCount)}{" "}
                        {campaign.goal.metric || "sent"}
                      </span>
                      <span className="text-xs text-clay-400 font-[family-name:var(--font-mono)]">
                        {progressPercent.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-clay-700 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-kiln-teal rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${progressPercent}%` }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                      />
                    </div>
                  </div>

                  {/* Stats row */}
                  <div className="grid grid-cols-4 gap-3">
                    <div>
                      <p className="text-[10px] text-clay-500 uppercase tracking-wider">
                        Processed
                      </p>
                      <p className="text-sm font-medium text-clay-200 font-[family-name:var(--font-mono)]">
                        {formatNumber(campaign.progress.total_processed)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-clay-500 uppercase tracking-wider">
                        Sent
                      </p>
                      <p className="text-sm font-medium text-kiln-teal font-[family-name:var(--font-mono)]">
                        {formatNumber(campaign.progress.total_sent)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-clay-500 uppercase tracking-wider">
                        Approval
                      </p>
                      <p
                        className={cn(
                          "text-sm font-medium font-[family-name:var(--font-mono)]",
                          campaign.progress.approval_rate >= 0.8
                            ? "text-kiln-teal"
                            : campaign.progress.approval_rate >= 0.6
                              ? "text-kiln-mustard"
                              : "text-kiln-coral"
                        )}
                      >
                        {formatPercent(campaign.progress.approval_rate)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-clay-500 uppercase tracking-wider">
                        Review
                      </p>
                      <p
                        className={cn(
                          "text-sm font-medium font-[family-name:var(--font-mono)]",
                          campaign.progress.total_pending_review > 0
                            ? "text-kiln-mustard"
                            : "text-clay-400"
                        )}
                      >
                        {formatNumber(campaign.progress.total_pending_review)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
