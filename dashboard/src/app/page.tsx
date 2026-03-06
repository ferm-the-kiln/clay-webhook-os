"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { JobList } from "@/components/dashboard/job-list";
import { ActivityChart } from "@/components/dashboard/activity-chart";
import { OutcomeCards } from "@/components/dashboard/outcome-cards";
import { CampaignProgress } from "@/components/dashboard/campaign-progress";
import { AlertsPanel } from "@/components/dashboard/alerts-panel";
import { ApprovalChart } from "@/components/dashboard/approval-chart";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { fetchOutcomes } from "@/lib/api";
import type { OutcomeDashboard } from "@/lib/types";

export default function DashboardPage() {
  const [outcomes, setOutcomes] = useState<OutcomeDashboard | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchOutcomes();
      setOutcomes(data);
    } catch {
      // Outcomes endpoint may not be available yet — that's OK
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  return (
    <div className="flex flex-col h-full">
      <Header title="Dashboard" />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ErrorBoundary>
            <ActivityChart />
          </ErrorBoundary>
        </div>

        <div>
          <h3 className="text-sm text-clay-500 uppercase tracking-wide mb-3 font-[family-name:var(--font-sans)]">
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
