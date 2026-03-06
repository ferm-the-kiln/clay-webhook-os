"use client";

import { useEffect, useState, useRef } from "react";
import { fetchUsage, createJobStream } from "@/lib/api";
import type { UsageSummary } from "@/lib/types";
import { formatNumber, formatTokens } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const HEALTH_CONFIG: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  healthy: { label: "Healthy", color: "text-emerald-400", bg: "bg-emerald-500/20" },
  warning: { label: "Warning", color: "text-yellow-400", bg: "bg-yellow-500/20" },
  critical: { label: "Critical", color: "text-orange-400", bg: "bg-orange-500/20" },
  exhausted: { label: "Exhausted", color: "text-red-400", bg: "bg-red-500/20" },
};

export function SubscriptionHealth() {
  const [data, setData] = useState<UsageSummary | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let active = true;
    let pollId: ReturnType<typeof setInterval> | null = null;

    const refresh = () =>
      fetchUsage()
        .then((d) => {
          if (active) setData(d);
        })
        .catch(() => {});

    refresh();

    try {
      const es = createJobStream(() => refresh());
      esRef.current = es;
      es.onerror = () => {
        es.close();
        esRef.current = null;
        if (!pollId && active) {
          pollId = setInterval(refresh, 30000);
        }
      };
    } catch {
      pollId = setInterval(refresh, 30000);
    }

    return () => {
      active = false;
      if (esRef.current) esRef.current.close();
      if (pollId) clearInterval(pollId);
    };
  }, []);

  if (!data) {
    return (
      <Card className="border-clay-800 bg-clay-900">
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-40 bg-clay-800 rounded" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-24 w-full bg-clay-800 rounded" />
        </CardContent>
      </Card>
    );
  }

  const health = HEALTH_CONFIG[data.subscription_health] || HEALTH_CONFIG.healthy;
  const showBanner = data.subscription_health === "critical" || data.subscription_health === "exhausted";

  // Last 7 days for mini chart
  const chartData = data.daily_history.slice(-7).map((d) => ({
    date: d.date.slice(5), // MM-DD
    tokens: d.total_tokens,
    requests: d.request_count,
    errors: d.errors,
  }));

  return (
    <Card className="border-clay-800 bg-clay-900">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm text-clay-500 uppercase tracking-wide font-[family-name:var(--font-sans)]">
            Subscription Usage
          </CardTitle>
          <Badge
            variant="outline"
            className={`${health.bg} ${health.color} border-0 text-xs`}
          >
            {health.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {showBanner && (
          <div className="rounded-md bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-300">
            {data.subscription_health === "exhausted"
              ? "Subscription quota exhausted. Jobs will fail until quota resets."
              : "Subscription nearing limit. A recent error was detected."}
            {data.last_error && (
              <p className="mt-1 text-xs text-red-400/80 truncate">
                {data.last_error.message}
              </p>
            )}
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <p className="text-xs text-clay-500">Today</p>
            <p className="text-lg font-semibold text-kiln-teal font-[family-name:var(--font-mono)]">
              {formatTokens(data.today.total_tokens)}
            </p>
            <p className="text-xs text-clay-600">
              {formatNumber(data.today.request_count)} req
            </p>
          </div>
          <div>
            <p className="text-xs text-clay-500">This Week</p>
            <p className="text-lg font-semibold text-kiln-teal font-[family-name:var(--font-mono)]">
              {formatTokens(data.week.total_tokens)}
            </p>
            <p className="text-xs text-clay-600">
              {formatNumber(data.week.request_count)} req
            </p>
          </div>
          <div>
            <p className="text-xs text-clay-500">This Month</p>
            <p className="text-lg font-semibold text-kiln-teal font-[family-name:var(--font-mono)]">
              {formatTokens(data.month.total_tokens)}
            </p>
            <p className="text-xs text-clay-600">
              {formatNumber(data.month.request_count)} req
            </p>
          </div>
        </div>

        {/* Mini 7-day bar chart */}
        {chartData.length > 0 && (
          <div className="h-24">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} barCategoryGap="20%">
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis hide />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e5e5e3",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(value, name) => {
                    const v = typeof value === "number" ? value : 0;
                    const label = name === "tokens" ? "Tokens" : name === "errors" ? "Errors" : "Requests";
                    return [name === "tokens" ? formatTokens(v) : formatNumber(v), label];
                  }}
                />
                <Bar dataKey="tokens" fill="#0099ff" radius={[3, 3, 0, 0]} />
                {chartData.some((d) => d.errors > 0) && (
                  <Bar dataKey="errors" fill="#dc2626" radius={[3, 3, 0, 0]} />
                )}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
