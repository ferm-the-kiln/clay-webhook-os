"use client";

import { useState, useEffect, useRef } from "react";
import { createJobStream } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";

interface Bucket {
  time: string;
  completed: number;
  failed: number;
}

function getBucketKey(date: Date): string {
  return `${date.getHours().toString().padStart(2, "0")}:${(Math.floor(date.getMinutes() / 10) * 10).toString().padStart(2, "0")}`;
}

export function ActivityChart() {
  const [buckets, setBuckets] = useState<Map<string, { completed: number; failed: number }>>(
    new Map()
  );
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let active = true;

    // Initialize with empty buckets for the last hour
    const now = new Date();
    const initial = new Map<string, { completed: number; failed: number }>();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 10 * 60 * 1000);
      initial.set(getBucketKey(d), { completed: 0, failed: 0 });
    }
    setBuckets(initial);

    try {
      const es = createJobStream((eventType, data) => {
        if (!active) return;
        if (eventType === "job_updated") {
          const status = data.status as string;
          if (status === "completed" || status === "failed" || status === "dead_letter") {
            const key = getBucketKey(new Date());
            setBuckets((prev) => {
              const next = new Map(prev);
              const bucket = next.get(key) || { completed: 0, failed: 0 };
              if (status === "completed") {
                next.set(key, { ...bucket, completed: bucket.completed + 1 });
              } else {
                next.set(key, { ...bucket, failed: bucket.failed + 1 });
              }
              return next;
            });
          }
        }
      });
      esRef.current = es;
    } catch {
      // SSE not available — chart stays empty
    }

    return () => {
      active = false;
      if (esRef.current) esRef.current.close();
    };
  }, []);

  const data: Bucket[] = Array.from(buckets.entries()).map(([time, val]) => ({
    time,
    completed: val.completed,
    failed: val.failed,
  }));

  if (data.every((d) => d.completed === 0 && d.failed === 0)) {
    return null; // Don't render empty chart
  }

  return (
    <Card className="border-clay-800 bg-white shadow-sm">
      <CardContent className="p-5">
        <h3 className="text-xs text-clay-500 uppercase tracking-wider mb-3 font-[family-name:var(--font-sans)]">
          Activity
        </h3>
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
            <defs>
              <linearGradient id="tealFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#015870" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#015870" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="coralFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f03603" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#f03603" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="time"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#a8a8a5", fontSize: 10 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#a8a8a5", fontSize: 10 }}
              allowDecimals={false}
            />
            <RechartsTooltip
              contentStyle={{
                backgroundColor: "#ffffff",
                border: "1px solid #e5e5e3",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "#737371" }}
            />
            <Area
              type="monotone"
              dataKey="completed"
              stroke="#015870"
              fill="url(#tealFill)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="failed"
              stroke="#f03603"
              fill="url(#coralFill)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
