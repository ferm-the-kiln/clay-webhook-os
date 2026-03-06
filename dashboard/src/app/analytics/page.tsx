"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { AnalyticsSummary } from "@/components/analytics/analytics-summary";
import { SkillPerformanceTable } from "@/components/analytics/skill-performance-table";
import { ApprovalChart } from "@/components/analytics/approval-chart";
import { ClientBreakdown } from "@/components/analytics/client-breakdown";
import type { FeedbackSummary } from "@/lib/types";
import { fetchFeedbackAnalytics, fetchSkills } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

const TIME_RANGES = [
  { label: "7 days", value: "7" },
  { label: "30 days", value: "30" },
  { label: "90 days", value: "90" },
  { label: "All time", value: "all" },
];

export default function AnalyticsPage() {
  const [data, setData] = useState<FeedbackSummary | null>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [skillFilter, setSkillFilter] = useState("all");
  const [timeRange, setTimeRange] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: { skill?: string; days?: number } = {};
      if (skillFilter !== "all") params.skill = skillFilter;
      if (timeRange !== "all") params.days = parseInt(timeRange);
      const summary = await fetchFeedbackAnalytics(params);
      setData(summary);
    } catch {
      toast.error("Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [skillFilter, timeRange]);

  useEffect(() => {
    fetchSkills()
      .then((res) => setSkills(res.skills))
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-col h-full">
      <Header title="Analytics" />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <Select value={skillFilter} onValueChange={setSkillFilter}>
            <SelectTrigger className="w-44 border-clay-700 bg-clay-900 text-clay-200 h-9 text-sm">
              <SelectValue placeholder="All skills" />
            </SelectTrigger>
            <SelectContent className="border-clay-700 bg-clay-900">
              <SelectItem value="all">All skills</SelectItem>
              {skills.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-36 border-clay-700 bg-clay-900 text-clay-200 h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="border-clay-700 bg-clay-900">
              {TIME_RANGES.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={load}
            disabled={loading}
            className="border-clay-700 text-clay-400 hover:text-clay-200 h-9"
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {/* Summary cards */}
        <AnalyticsSummary data={data} />

        {/* Charts + Table */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ApprovalChart skills={data?.by_skill || []} />
          <ClientBreakdown byClient={data?.by_client || {}} />
        </div>

        {/* Performance table */}
        <div>
          <h3 className="text-sm font-medium text-clay-300 mb-3">
            Skill Performance
          </h3>
          <SkillPerformanceTable skills={data?.by_skill || []} />
        </div>
      </div>
    </div>
  );
}
