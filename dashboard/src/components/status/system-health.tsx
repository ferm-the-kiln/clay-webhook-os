"use client";

import { useEffect, useState, useCallback } from "react";
import {
  fetchHealthDeep,
  fetchRetries,
  fetchSubscriptions,
  fetchStats,
} from "@/lib/api";
import type { HealthResponse, Stats } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { formatNumber, formatTokens } from "@/lib/utils";
import {
  Activity,
  Server,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Cpu,
} from "lucide-react";

interface RetryData {
  pending: number;
  items: { job_id: string; skill: string; retry_count: number; last_error: string; next_retry_at: number }[];
}

interface SubData {
  status: string;
  health: string;
  today_requests: number;
  today_tokens: number;
  today_errors: number;
}

const STATUS_BADGE: Record<string, { variant: "default" | "destructive" | "secondary"; className: string; icon: typeof CheckCircle }> = {
  healthy: { variant: "default", className: "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30", icon: CheckCircle },
  warning: { variant: "secondary", className: "bg-kiln-mustard/15 text-kiln-mustard border-kiln-mustard/30", icon: AlertTriangle },
  critical: { variant: "destructive", className: "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/30", icon: XCircle },
  exhausted: { variant: "destructive", className: "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/30", icon: XCircle },
};

export function SystemHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [retries, setRetries] = useState<RetryData | null>(null);
  const [subscription, setSubscription] = useState<SubData | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      fetchHealthDeep(),
      fetchRetries().catch(() => ({ pending: 0, items: [] })),
      fetchSubscriptions().catch(() => null),
      fetchStats(),
    ]);
    if (results[0].status === "fulfilled") setHealth(results[0].value);
    if (results[1].status === "fulfilled") setRetries(results[1].value as RetryData);
    if (results[2].status === "fulfilled" && results[2].value) setSubscription(results[2].value as SubData);
    if (results[3].status === "fulfilled") setStats(results[3].value);
    setLastRefresh(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  if (loading && !health) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i} className="border-clay-800 bg-white shadow-sm">
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-32 bg-clay-800 rounded" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-16 w-full bg-clay-800 rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const overallStatus = health?.status === "ok" ? "healthy" : "critical";
  const subHealth = subscription?.health || "healthy";
  const statusConfig = STATUS_BADGE[overallStatus] || STATUS_BADGE.healthy;
  const subConfig = STATUS_BADGE[subHealth] || STATUS_BADGE.healthy;
  const StatusIcon = statusConfig.icon;
  const SubIcon = subConfig.icon;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {lastRefresh && (
            <span className="text-xs text-clay-600">
              Updated {lastRefresh.toLocaleTimeString()}
            </span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={load}
          disabled={loading}
          className="border-clay-700 text-clay-400 hover:text-clay-200"
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Backend Health */}
        <Card className="border-clay-800 bg-white shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-clay-300 flex items-center gap-2">
                <Server className="h-4 w-4" />
                Backend
              </CardTitle>
              <Badge variant={statusConfig.variant} className={statusConfig.className}>
                <StatusIcon className="h-3 w-3 mr-1" />
                {health?.status === "ok" ? "Healthy" : "Down"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {health?.deep_check && (
              <div className="flex justify-between">
                <span className="text-clay-500">Claude Available</span>
                <span className={health.deep_check.claude_available ? "text-kiln-teal" : "text-kiln-coral"}>
                  {health.deep_check.claude_available ? "Yes" : "No"}
                </span>
              </div>
            )}
            {health?.deep_check?.latency_ms != null && (
              <div className="flex justify-between">
                <span className="text-clay-500">Latency</span>
                <span className="text-clay-300 font-mono text-xs">{health.deep_check.latency_ms}ms</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-clay-500">Skills Loaded</span>
              <span className="text-clay-300">{health?.skills_loaded?.length ?? 0}</span>
            </div>
          </CardContent>
        </Card>

        {/* Worker Pool */}
        <Card className="border-clay-800 bg-white shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-clay-300 flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Worker Pool
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-clay-500">Available</span>
              <span className="text-clay-300">{health?.workers_available ?? 0} / {health?.workers_max ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-clay-500">Queue Pending</span>
              <span className="text-clay-300">{health?.queue_pending ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-clay-500">Queue Total</span>
              <span className="text-clay-300">{health?.queue_total ?? 0}</span>
            </div>
            {stats && (
              <div className="flex justify-between">
                <span className="text-clay-500">Cache Hit Rate</span>
                <span className="text-clay-300">{(stats.cache_hit_rate * 100).toFixed(0)}%</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Subscription Status */}
        <Card className="border-clay-800 bg-white shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-clay-300 flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Subscription
              </CardTitle>
              <Badge variant={subConfig.variant} className={subConfig.className}>
                <SubIcon className="h-3 w-3 mr-1" />
                {(subHealth).charAt(0).toUpperCase() + subHealth.slice(1)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-clay-500">Today Requests</span>
              <span className="text-clay-300">{formatNumber(subscription?.today_requests ?? stats?.usage?.today_requests ?? 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-clay-500">Today Tokens</span>
              <span className="text-clay-300">{formatTokens(subscription?.today_tokens ?? stats?.usage?.today_tokens ?? 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-clay-500">Today Errors</span>
              <span className={`${(subscription?.today_errors ?? 0) > 0 ? "text-kiln-coral" : "text-clay-300"}`}>
                {subscription?.today_errors ?? stats?.usage?.today_errors ?? 0}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Retry Queue */}
        <Card className="border-clay-800 bg-white shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-clay-300 flex items-center gap-2">
              <RefreshCw className="h-4 w-4" />
              Retry Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-clay-100 font-mono">
              {retries?.pending ?? 0}
            </p>
            <p className="text-xs text-clay-500 mt-1">pending retries</p>
            {retries && retries.items.length > 0 && (
              <div className="mt-3 space-y-1.5">
                {retries.items.slice(0, 3).map((item) => (
                  <div key={item.job_id} className="text-xs text-clay-400 flex items-center gap-2">
                    <Clock className="h-3 w-3 text-clay-600 shrink-0" />
                    <span className="text-kiln-teal">{item.skill}</span>
                    <span className="text-clay-600">#{item.retry_count}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Dead Letters */}
        <Card className="border-clay-800 bg-white shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-clay-300 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Dead Letters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold font-mono ${(stats?.total_dead_letter ?? 0) > 0 ? "text-kiln-coral" : "text-clay-100"}`}>
              {stats?.total_dead_letter ?? 0}
            </p>
            <p className="text-xs text-clay-500 mt-1">permanently failed jobs</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
