"use client";

import { useEffect, useState } from "react";
import { fetchStats } from "@/lib/api";
import type { Stats } from "@/lib/types";
import { formatDuration } from "@/lib/utils";

export function StatsCards() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    let active = true;
    const poll = () =>
      fetchStats()
        .then((s) => active && setStats(s))
        .catch(() => {});
    poll();
    const id = setInterval(poll, 5000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  if (!stats) {
    return (
      <div className="grid grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 animate-pulse h-24" />
        ))}
      </div>
    );
  }

  const cards = [
    { label: "Processed", value: stats.total_processed },
    { label: "Active Workers", value: stats.active_workers },
    { label: "Queue Depth", value: stats.queue_depth },
    { label: "Avg Duration", value: formatDuration(stats.avg_duration_ms) },
    {
      label: "Success Rate",
      value: `${(stats.success_rate * 100).toFixed(1)}%`,
    },
  ];

  return (
    <div className="grid grid-cols-5 gap-4">
      {cards.map((c) => (
        <div
          key={c.label}
          className="rounded-xl border border-zinc-800 bg-zinc-900 p-4"
        >
          <p className="text-xs text-zinc-500 uppercase tracking-wide">
            {c.label}
          </p>
          <p className="mt-1 text-2xl font-semibold font-mono text-zinc-100">
            {c.value}
          </p>
        </div>
      ))}
    </div>
  );
}
