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
import { AnimatePresence, motion } from "framer-motion";
import {
  Zap,
  Target,
  DollarSign,
  Rocket,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function DashboardPage() {
  const [outcomes, setOutcomes] = useState<OutcomeDashboard | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [hasActivity, setHasActivity] = useState<boolean | null>(null);
  const [onboardingDismissed, setOnboardingDismissed] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("kiln_onboarding_dismissed") === "true";
    }
    return false;
  });
  const [techDetailsOpen, setTechDetailsOpen] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

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
      setLastUpdated(new Date());
    } catch {
      setHasActivity(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  // Auto-dismiss onboarding when activity is detected
  useEffect(() => {
    if (hasActivity && !onboardingDismissed) {
      localStorage.setItem("kiln_onboarding_dismissed", "true");
      setOnboardingDismissed(true);
    }
  }, [hasActivity, onboardingDismissed]);

  // Empty state for new clients
  if (hasActivity === false && !onboardingDismissed) {
    const dismissOnboarding = () => {
      localStorage.setItem("kiln_onboarding_dismissed", "true");
      setOnboardingDismissed(true);
    };
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
            <button
              onClick={dismissOnboarding}
              className="text-xs text-clay-500 hover:text-clay-300 transition-colors mt-2"
            >
              Skip — I've used this before
            </button>
          </EmptyState>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header title="Dashboard" lastUpdated={lastUpdated} onRefresh={load} />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">

        {/* ─── Overview ─── */}
        <section>
          <h2 className="text-lg font-semibold text-clay-100 mb-4">Overview</h2>

          {/* Hero stats row */}
          {stats && stats.total_processed > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Card className="border-clay-800 bg-white shadow-sm">
                <CardContent className="p-6">
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
                <CardContent className="p-6">
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
                <CardContent className="p-6">
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
        </section>

        {/* ─── Campaigns ─── */}
        {outcomes ? (
          <section className="pt-8">
            <h2 className="text-lg font-semibold text-clay-100 mb-4">Campaigns</h2>
            <div className="space-y-6">
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
            </div>
          </section>
        ) : (
          stats && stats.total_processed > 0 && (
            <section className="pt-8">
              <Card className="border-clay-800 bg-white shadow-sm">
                <CardContent className="p-6 text-center">
                  <Rocket className="h-8 w-8 text-clay-600 mx-auto mb-3" />
                  <h3 className="text-sm font-medium text-clay-200 mb-1">No campaigns yet</h3>
                  <p className="text-xs text-clay-500 mb-4">Create your first campaign to see results here.</p>
                  <Button asChild size="sm" className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold">
                    <Link href="/outbound/campaigns">Create Campaign</Link>
                  </Button>
                </CardContent>
              </Card>
            </section>
          )
        )}

        {/* ─── Recent Activity ─── */}
        <section className="pt-8">
          <h2 className="text-lg font-semibold text-clay-100 mb-4">Recent Activity</h2>
          <ErrorBoundary>
            <JobList />
          </ErrorBoundary>
        </section>

        {/* ─── Technical Details (collapsed by default) ─── */}
        <section className="pt-8 pb-2">
          <button
            onClick={() => setTechDetailsOpen(!techDetailsOpen)}
            className="flex items-center gap-2 text-lg font-semibold text-clay-100 hover:text-clay-50 transition-colors mb-4"
          >
            {techDetailsOpen ? (
              <ChevronUp className="h-5 w-5 text-clay-400" />
            ) : (
              <ChevronDown className="h-5 w-5 text-clay-400" />
            )}
            Technical Details
          </button>
          <AnimatePresence initial={false}>
            {techDetailsOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: "easeInOut" }}
                className="overflow-hidden"
              >
                <div className="space-y-6">
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
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </div>
    </div>
  );
}
