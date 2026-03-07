"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { JobList } from "@/components/dashboard/job-list";
import { ActivityChart } from "@/components/dashboard/activity-chart";
import { OutcomeCards } from "@/components/dashboard/outcome-cards";
import { CampaignProgress } from "@/components/dashboard/campaign-progress";
import { AlertsPanel } from "@/components/dashboard/alerts-panel";
import { ApprovalChart } from "@/components/dashboard/approval-chart";
import { SubscriptionHealth } from "@/components/dashboard/subscription-health";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { fetchOutcomes, fetchStats } from "@/lib/api";
import type { OutcomeDashboard, Stats } from "@/lib/types";
import { formatNumber, formatPercent, formatCost } from "@/lib/utils";
import {
  FlaskConical,
  Layers,
  BarChart3,
  Zap,
  Target,
  DollarSign,
  Rocket,
} from "lucide-react";

export default function DashboardPage() {
  const [outcomes, setOutcomes] = useState<OutcomeDashboard | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [hasActivity, setHasActivity] = useState<boolean | null>(null);

  const load = useCallback(async () => {
    try {
      const [outcomeData, statsData] = await Promise.allSettled([
        fetchOutcomes(),
        fetchStats(),
      ]);
      if (outcomeData.status === "fulfilled") setOutcomes(outcomeData.value);
      if (statsData.status === "fulfilled") {
        setStats(statsData.value);
        setHasActivity(statsData.value.total_processed > 0);
      } else {
        setHasActivity(false);
      }
    } catch {
      setHasActivity(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  // Empty state for new clients
  if (hasActivity === false) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Dashboard" />
        <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6 flex items-center justify-center">
          <EmptyState
            title="Welcome to The Kiln"
            description="Your AI outbound engine is ready. Run your first skill to see metrics, analytics, and job history here."
            icon={Rocket}
          >
            <Button asChild className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold">
              <Link href="/getting-started">Get Started</Link>
            </Button>
            <Button variant="outline" asChild className="border-clay-700 text-clay-300 hover:bg-clay-800">
              <Link href="/run">Open Playground</Link>
            </Button>
          </EmptyState>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header title="Dashboard" />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        {/* Hero stats row */}
        {stats && stats.total_processed > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="border-clay-800 bg-white shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-1">
                  <Zap className="h-4 w-4 text-kiln-teal" />
                  <span className="text-xs text-clay-500 uppercase tracking-wider">
                    Jobs Today
                  </span>
                </div>
                <p className="text-3xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
                  {formatNumber(stats.usage?.today_requests ?? stats.total_processed)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-clay-800 bg-white shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-1">
                  <Target className="h-4 w-4 text-kiln-teal" />
                  <span className="text-xs text-clay-500 uppercase tracking-wider">
                    Success Rate
                  </span>
                </div>
                <p className="text-3xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
                  {formatPercent(stats.success_rate)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-clay-800 bg-white shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-1">
                  <DollarSign className="h-4 w-4 text-kiln-teal" />
                  <span className="text-xs text-clay-500 uppercase tracking-wider">
                    Value Delivered
                  </span>
                </div>
                <p className="text-3xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
                  {formatCost(stats.cost?.total_equivalent_usd ?? 0)}
                </p>
                <p className="text-xs text-kiln-teal mt-0.5">
                  {formatCost(stats.cost?.total_savings_usd ?? 0)} saved vs API
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Quick actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Button
            variant="outline"
            asChild
            className="h-auto py-3 px-4 border-clay-700 hover:border-kiln-teal/30 hover:bg-kiln-teal/5 justify-start"
          >
            <Link href="/run" className="flex items-center gap-3">
              <div className="flex items-center justify-center h-9 w-9 rounded-lg bg-kiln-teal/10">
                <FlaskConical className="h-4 w-4 text-kiln-teal" />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-clay-200">Run a Skill</p>
                <p className="text-xs text-clay-500">Test in Playground</p>
              </div>
            </Link>
          </Button>
          <Button
            variant="outline"
            asChild
            className="h-auto py-3 px-4 border-clay-700 hover:border-kiln-teal/30 hover:bg-kiln-teal/5 justify-start"
          >
            <Link href="/run?tab=batch" className="flex items-center gap-3">
              <div className="flex items-center justify-center h-9 w-9 rounded-lg bg-kiln-mustard/10">
                <Layers className="h-4 w-4 text-kiln-mustard" />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-clay-200">Upload Batch</p>
                <p className="text-xs text-clay-500">Process CSV rows</p>
              </div>
            </Link>
          </Button>
          <Button
            variant="outline"
            asChild
            className="h-auto py-3 px-4 border-clay-700 hover:border-kiln-teal/30 hover:bg-kiln-teal/5 justify-start"
          >
            <Link href="/settings?tab=analytics" className="flex items-center gap-3">
              <div className="flex items-center justify-center h-9 w-9 rounded-lg bg-clay-800/50">
                <BarChart3 className="h-4 w-4 text-clay-400" />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium text-clay-200">View Analytics</p>
                <p className="text-xs text-clay-500">Quality & ROI</p>
              </div>
            </Link>
          </Button>
        </div>

        {/* Phase 4: Outcome-focused metrics */}
        {outcomes && (
          <>
            <ErrorBoundary>
              <OutcomeCards data={outcomes} />
            </ErrorBoundary>

            {/* Active campaigns progress + Alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2">
                <ErrorBoundary>
                  <CampaignProgress campaigns={outcomes.campaigns} />
                </ErrorBoundary>
              </div>
              <ErrorBoundary>
                <AlertsPanel
                  alerts={outcomes.alerts}
                  recommendations={outcomes.recommendations}
                />
              </ErrorBoundary>
            </div>

            {/* Approval chart */}
            {outcomes.feedback_7d.by_skill.length > 0 && (
              <ErrorBoundary>
                <ApprovalChart feedback={outcomes.feedback_7d} />
              </ErrorBoundary>
            )}
          </>
        )}

        {/* Operational view */}
        <ErrorBoundary>
          <StatsCards />
        </ErrorBoundary>

        <ErrorBoundary>
          <SubscriptionHealth />
        </ErrorBoundary>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ErrorBoundary>
            <ActivityChart />
          </ErrorBoundary>
        </div>

        <div>
          <h3 className="text-base font-semibold text-clay-200 mb-3 font-[family-name:var(--font-sans)]">
            Recent Jobs
          </h3>
          <ErrorBoundary>
            <JobList />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
