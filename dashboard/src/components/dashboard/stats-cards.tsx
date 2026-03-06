"use client";

import { useEffect, useState, useRef } from "react";
import { fetchStats, createJobStream } from "@/lib/api";
import type { Stats } from "@/lib/types";
import { formatSmartDuration, formatNumber, formatPercent, formatCost } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Rocket, Target, BarChart3, Filter, Clock, Compass, DollarSign, TrendingUp, type LucideIcon } from "lucide-react";

const METRIC_TOOLTIPS: Record<string, string> = {
  total_processed: "Total number of webhook jobs processed since the server started.",
  active_workers: "Number of Claude worker processes currently handling jobs.",
  queue_depth: "Jobs waiting in the queue to be picked up by a worker.",
  avg_duration_ms: "Average time to complete a job, from queue pickup to response.",
  success_rate: "Percentage of jobs that completed without errors.",
  cache_hit_rate: "Percentage of requests served from cache instead of calling Claude.",
  api_equivalent: "What you would pay using the Anthropic API for the same usage.",
  net_savings: "Total savings vs. API pricing, including cache savings.",
};

interface CardDef {
  key: string;
  label: string;
  icon: LucideIcon;
  format: "number" | "duration" | "percent" | "cost";
  group: "health" | "volume" | "performance" | "cost";
}

const CARDS: CardDef[] = [
  { key: "active_workers", label: "Active Workers", icon: Rocket, format: "number", group: "health" },
  { key: "success_rate", label: "Success Rate", icon: Target, format: "percent", group: "health" },
  { key: "total_processed", label: "Processed", icon: BarChart3, format: "number", group: "volume" },
  { key: "queue_depth", label: "Queue Depth", icon: Filter, format: "number", group: "volume" },
  { key: "avg_duration_ms", label: "Avg Duration", icon: Clock, format: "duration", group: "performance" },
  { key: "cache_hit_rate", label: "Cache Hit Rate", icon: Compass, format: "percent", group: "performance" },
  { key: "api_equivalent", label: "API Equivalent", icon: DollarSign, format: "cost", group: "cost" },
  { key: "net_savings", label: "Net Savings", icon: TrendingUp, format: "cost", group: "cost" },
];

function formatValue(value: number, format: string): string {
  if (format === "duration") return formatSmartDuration(value);
  if (format === "percent") return formatPercent(value);
  if (format === "cost") return formatCost(value);
  return formatNumber(value);
}

function AnimatedNumber({ value, format }: { value: number; format: string }) {
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);

  useEffect(() => {
    const from = prevRef.current;
    const to = value;
    if (from === to) return;
    prevRef.current = to;

    const duration = 400;
    const start = performance.now();

    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setDisplay(from + (to - from) * eased);
      if (progress < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [value]);

  return <>{formatValue(display, format)}</>;
}

// Mini sparkline using SVG
function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 80;
  const h = 24;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * (h - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={w} height={h} className="mt-1 opacity-60">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function getStatValue(stats: Stats, key: string): number {
  if (key === "api_equivalent") return stats.cost?.total_equivalent_usd ?? 0;
  if (key === "net_savings") return stats.cost?.total_savings_usd ?? 0;
  return (stats[key as keyof Stats] as number) ?? 0;
}

export function StatsCards() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [stale, setStale] = useState(false);
  const [history, setHistory] = useState<Record<string, number[]>>({});
  const esRef = useRef<EventSource | null>(null);
  const lastUpdateRef = useRef<number>(Date.now());

  useEffect(() => {
    let active = true;
    let pollId: ReturnType<typeof setInterval> | null = null;
    let staleId: ReturnType<typeof setInterval> | null = null;

    const refresh = () =>
      fetchStats()
        .then((s) => {
          if (!active) return;
          setStats(s);
          setStale(false);
          lastUpdateRef.current = Date.now();
          // Accumulate history for sparklines (keep last 12 data points)
          setHistory((prev) => {
            const next: Record<string, number[]> = {};
            for (const c of CARDS) {
              const val = getStatValue(s, c.key);
              const arr = prev[c.key] || [];
              next[c.key] = [...arr.slice(-11), val];
            }
            return next;
          });
        })
        .catch(() => {});

    refresh();

    try {
      const es = createJobStream(() => {
        refresh();
      });
      esRef.current = es;

      es.onerror = () => {
        es.close();
        esRef.current = null;
        if (!pollId && active) {
          pollId = setInterval(refresh, 5000);
        }
      };
    } catch {
      pollId = setInterval(refresh, 5000);
    }

    // Check staleness every 15s
    staleId = setInterval(() => {
      if (Date.now() - lastUpdateRef.current > 30000) {
        setStale(true);
      }
    }, 15000);

    return () => {
      active = false;
      if (esRef.current) esRef.current.close();
      if (pollId) clearInterval(pollId);
      if (staleId) clearInterval(staleId);
    };
  }, []);

  if (!stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4" aria-live="polite">
        {Array.from({ length: 8 }).map((_, i) => (
          <Card key={i} className="border-clay-800 bg-clay-900">
            <CardContent className="p-4">
              <Skeleton className="h-3 w-20 mb-3 bg-clay-800 rounded" />
              <Skeleton className="h-7 w-14 bg-clay-800 rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div
      className={`grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 transition-opacity duration-300 ${stale ? "opacity-70" : ""}`}
      aria-live="polite"
    >
      {CARDS.map((c) => {
        const value = getStatValue(stats, c.key);
        const isFail =
          (c.key === "success_rate" && value < 0.9) ||
          (c.key === "cache_hit_rate" && value < 0.1);
        const sparkData = history[c.key] || [];
        const sparkColor = isFail ? "#dc2626" : "#0099ff";
        const Icon = c.icon;

        return (
          <Tooltip key={c.key}>
            <TooltipTrigger asChild>
              <Card
                className={`border-clay-800 bg-clay-900 hover:border-kiln-teal/30 transition-all duration-200 group ${
                  c.group === "health" ? "lg:col-span-1" : ""
                }`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-clay-500 uppercase tracking-wide font-[family-name:var(--font-sans)]">
                      {c.label}
                    </p>
                    <Icon className="h-5 w-5 text-clay-600 opacity-60 group-hover:opacity-90 group-hover:text-clay-400 transition-all" />
                  </div>
                  <p
                    className={`text-2xl font-semibold font-[family-name:var(--font-mono)] ${
                      isFail ? "text-kiln-coral" : "text-kiln-teal"
                    }`}
                  >
                    <AnimatedNumber value={value} format={c.format} />
                  </p>
                  <Sparkline data={sparkData} color={sparkColor} />
                </CardContent>
              </Card>
            </TooltipTrigger>
            <TooltipContent
              side="bottom"
              className="max-w-xs bg-clay-900 border-clay-700 text-clay-300 text-xs"
            >
              {METRIC_TOOLTIPS[c.key]}
              {stale && (
                <span className="block mt-1 text-kiln-mustard">
                  Data may be stale. Last updated {Math.round((Date.now() - lastUpdateRef.current) / 1000)}s ago.
                </span>
              )}
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
