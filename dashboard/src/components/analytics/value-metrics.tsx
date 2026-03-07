"use client";

import type { Stats, FeedbackSummary } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { formatCost, formatNumber, formatTokens } from "@/lib/utils";
import { DollarSign, TrendingUp, Zap, PiggyBank } from "lucide-react";

export function ValueMetrics({
  stats,
  feedbackData,
}: {
  stats: Stats;
  feedbackData: FeedbackSummary | null;
}) {
  const apiEquivalent = stats.cost?.total_equivalent_usd ?? 0;
  const subscriptionCost = stats.cost?.subscription_monthly_usd ?? 200;
  const savings = stats.cost?.total_savings_usd ?? 0;
  const totalJobs = stats.total_processed;
  const totalTokens = stats.tokens?.total_est ?? 0;
  const approvalRate = feedbackData?.overall_approval_rate ?? 0;

  // Per-skill job counts from feedback data
  const skillCounts = feedbackData?.by_skill ?? [];

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-clay-300">
        Value Delivered
      </h3>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total jobs */}
        <Card className="border-clay-800 bg-white shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-1">
              <Zap className="h-4 w-4 text-kiln-teal" />
              <span className="text-xs text-clay-500 uppercase tracking-wider">
                Total Jobs
              </span>
            </div>
            <p className="text-2xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
              {formatNumber(totalJobs)}
            </p>
            <p className="text-xs text-clay-500 mt-0.5">
              {formatTokens(totalTokens)} tokens processed
            </p>
          </CardContent>
        </Card>

        {/* API equivalent cost */}
        <Card className="border-clay-800 bg-white shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="h-4 w-4 text-kiln-mustard" />
              <span className="text-xs text-clay-500 uppercase tracking-wider">
                API Equivalent
              </span>
            </div>
            <p className="text-2xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
              {formatCost(apiEquivalent)}
            </p>
            <p className="text-xs text-clay-500 mt-0.5">
              What this would cost on Anthropic API
            </p>
          </CardContent>
        </Card>

        {/* Subscription cost */}
        <Card className="border-clay-800 bg-white shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-1">
              <PiggyBank className="h-4 w-4 text-kiln-teal" />
              <span className="text-xs text-clay-500 uppercase tracking-wider">
                Your Cost
              </span>
            </div>
            <p className="text-2xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
              {formatCost(subscriptionCost)}
              <span className="text-sm text-clay-500 font-normal">/mo</span>
            </p>
            <p className="text-xs text-clay-500 mt-0.5">
              Flat-rate subscription
            </p>
          </CardContent>
        </Card>

        {/* Net savings */}
        <Card className="border-clay-800 bg-white shadow-sm border-kiln-teal/20">
          <CardContent className="p-5">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-kiln-teal" />
              <span className="text-xs text-clay-500 uppercase tracking-wider">
                Total Savings
              </span>
            </div>
            <p className="text-2xl font-bold text-kiln-teal font-[family-name:var(--font-mono)]">
              {formatCost(savings)}
            </p>
            <p className="text-xs text-clay-500 mt-0.5">
              {apiEquivalent > 0
                ? `${Math.round((savings / apiEquivalent) * 100)}% less than API pricing`
                : "Includes cache savings"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Per-skill job counts */}
      {skillCounts.length > 0 && (
        <div className="rounded-xl border border-clay-800 bg-white shadow-sm p-4">
          <h4 className="text-sm font-medium text-clay-300 mb-3">
            Output by Skill
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {skillCounts
              .sort((a, b) => b.total - a.total)
              .map((s) => (
                <div
                  key={s.skill}
                  className="flex items-center justify-between rounded-lg bg-clay-900/50 border border-clay-800 px-3 py-2"
                >
                  <span className="text-sm text-clay-300 truncate mr-2">
                    {s.skill}
                  </span>
                  <span className="text-sm font-medium text-clay-100 font-[family-name:var(--font-mono)]">
                    {s.total}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
