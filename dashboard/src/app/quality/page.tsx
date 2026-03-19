"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Header } from "@/components/layout/header";
import { QualityAlerts } from "@/components/quality/quality-alerts";
import { SkillPerformance } from "@/components/quality/skill-performance";
import type { FeedbackSummary, QualityAlert, UsageSummary } from "@/lib/types";
import {
  fetchFeedbackAnalytics,
  fetchQualityAlerts,
  fetchUsage,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  BarChart3,
  Activity,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const TIME_RANGES = [
  { label: "7d", value: 7 },
  { label: "30d", value: 30 },
  { label: "90d", value: 90 },
];

export default function QualityPage() {
  const [analytics, setAnalytics] = useState<FeedbackSummary | null>(null);
  const [alerts, setAlerts] = useState<QualityAlert[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [analyticsRes, alertsRes, usageRes] = await Promise.all([
        fetchFeedbackAnalytics({ days }),
        fetchQualityAlerts(0.7),
        fetchUsage(),
      ]);
      setAnalytics(analyticsRes);
      setAlerts(alertsRes.alerts);
      setUsage(usageRes);
      setLastUpdated(new Date());
    } catch {
      toast.error("Failed to load quality data");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      loadData();
    }, 30000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loadData]);

  // Build approval rate over time data from usage daily_history
  const approvalChartData = usage?.daily_history
    ?.slice(-days)
    .map((d) => ({
      date: d.date,
      requests: d.request_count,
      errors: d.errors,
      errorRate: d.request_count > 0 ? Math.round((d.errors / d.request_count) * 100) : 0,
    })) ?? [];

  // Summary stat cards
  const overallApproval = analytics
    ? Math.round(analytics.overall_approval_rate * 100)
    : 0;
  const totalUp = analytics
    ? analytics.by_skill.reduce((sum, s) => sum + s.thumbs_up, 0)
    : 0;
  const totalDown = analytics
    ? analytics.by_skill.reduce((sum, s) => sum + s.thumbs_down, 0)
    : 0;
  const alertCount = alerts.length;
  const criticalCount = alerts.filter((a) => a.severity === "critical").length;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Quality"
        lastUpdated={lastUpdated}
        onRefresh={loadData}
      />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 rounded-lg border border-clay-500 p-0.5">
            {TIME_RANGES.map((range) => (
              <Button
                key={range.value}
                variant="ghost"
                size="sm"
                onClick={() => setDays(range.value)}
                className={cn(
                  "h-7 px-3 text-xs font-medium transition-all",
                  days === range.value
                    ? "bg-kiln-teal/10 text-kiln-teal hover:bg-kiln-teal/15 hover:text-kiln-teal"
                    : "text-clay-300 hover:text-clay-100"
                )}
              >
                {range.label}
              </Button>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            disabled={loading}
            className="border-clay-700 text-clay-200 hover:text-clay-200 h-7"
          >
            <RefreshCw
              className={cn("h-3.5 w-3.5 mr-1.5", loading && "animate-spin")}
            />
            Refresh
          </Button>

          <span className="text-xs text-clay-400 ml-auto">
            Auto-refreshes every 30s
          </span>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <Card className="border-clay-500">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="h-4 w-4 text-kiln-teal" />
                <span className="text-xs text-clay-200 uppercase tracking-wider">
                  Total Ratings
                </span>
              </div>
              <p className="text-2xl font-bold text-clay-100">
                {analytics?.total_ratings ?? 0}
              </p>
            </CardContent>
          </Card>

          <Card className="border-clay-500">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-2">
                {overallApproval >= 70 ? (
                  <TrendingUp className="h-4 w-4 text-kiln-teal" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-kiln-coral" />
                )}
                <span className="text-xs text-clay-200 uppercase tracking-wider">
                  Approval Rate
                </span>
              </div>
              <p
                className={cn(
                  "text-2xl font-bold",
                  overallApproval >= 70 ? "text-kiln-teal" : "text-kiln-coral"
                )}
              >
                {overallApproval}%
              </p>
            </CardContent>
          </Card>

          <Card className="border-clay-500">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-2">
                <ThumbsUp className="h-4 w-4 text-kiln-teal" />
                <span className="text-xs text-clay-200 uppercase tracking-wider">
                  Thumbs Up
                </span>
              </div>
              <p className="text-2xl font-bold text-kiln-teal">{totalUp}</p>
            </CardContent>
          </Card>

          <Card className="border-clay-500">
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-2">
                <ThumbsDown className="h-4 w-4 text-kiln-coral" />
                <span className="text-xs text-clay-200 uppercase tracking-wider">
                  Thumbs Down
                </span>
              </div>
              <p className="text-2xl font-bold text-kiln-coral">{totalDown}</p>
            </CardContent>
          </Card>

          <Card
            className={cn(
              "border-clay-500",
              criticalCount > 0 && "border-kiln-coral/40"
            )}
          >
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-2">
                <Activity
                  className={cn(
                    "h-4 w-4",
                    alertCount > 0 ? "text-kiln-coral" : "text-kiln-teal"
                  )}
                />
                <span className="text-xs text-clay-200 uppercase tracking-wider">
                  Alerts
                </span>
              </div>
              <p
                className={cn(
                  "text-2xl font-bold",
                  alertCount > 0 ? "text-kiln-coral" : "text-clay-100"
                )}
              >
                {alertCount}
              </p>
              {criticalCount > 0 && (
                <p className="text-xs text-kiln-coral mt-0.5">
                  {criticalCount} critical
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quality Alerts */}
        <div>
          <h3 className="text-sm font-medium text-clay-300 mb-3">
            Quality Alerts
          </h3>
          <QualityAlerts alerts={alerts} />
        </div>

        {/* Approval Rate Over Time Chart */}
        {approvalChartData.length > 0 && (
          <div className="rounded-xl border border-clay-500 p-4">
            <h4 className="text-sm font-medium text-clay-300 mb-4">
              Request Volume & Error Rate ({days}d)
            </h4>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart
                data={approvalChartData}
                margin={{ left: 10, right: 20, top: 5, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#3a3a38"
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#a8a8a5", fontSize: 11 }}
                  tickFormatter={(v: string) => {
                    const parts = v.split("-");
                    return `${parts[1]}/${parts[2]}`;
                  }}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fill: "#a8a8a5", fontSize: 11 }}
                  label={{
                    value: "Requests",
                    angle: -90,
                    position: "insideLeft",
                    style: { fill: "#737371", fontSize: 11 },
                  }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={[0, 100]}
                  tick={{ fill: "#a8a8a5", fontSize: 11 }}
                  tickFormatter={(v: number) => `${v}%`}
                  label={{
                    value: "Error %",
                    angle: 90,
                    position: "insideRight",
                    style: { fill: "#737371", fontSize: 11 },
                  }}
                />
                <Tooltip
                  contentStyle={{
                    background: "#1a1a19",
                    border: "1px solid #3a3a38",
                    borderRadius: 8,
                    color: "#e5e5e3",
                  }}
                  labelStyle={{ color: "#a8a8a5" }}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="requests"
                  stroke="#015870"
                  strokeWidth={2}
                  dot={false}
                  name="Requests"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="errorRate"
                  stroke="#f03603"
                  strokeWidth={2}
                  dot={false}
                  name="Error Rate %"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Skill Performance Table */}
        <div>
          <h3 className="text-sm font-medium text-clay-300 mb-3">
            Skill Performance
          </h3>
          <SkillPerformance skills={analytics?.by_skill ?? []} />
        </div>
      </div>
    </div>
  );
}
