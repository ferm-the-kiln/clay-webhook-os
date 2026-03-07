"use client";

import { useEffect, useState, useRef } from "react";
import { fetchJobs, createJobStream } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";

const COLORS = [
  "#015870",
  "#C4A093",
  "#ca8a04",
  "#f03603",
  "#4a9eb8",
  "#0a7a9e",
  "#737371",
  "#d4d4d2",
  "#013d55",
];

interface SkillCount {
  name: string;
  value: number;
}

export function SkillDistribution() {
  const [data, setData] = useState<SkillCount[]>([]);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let active = true;

    const refresh = () =>
      fetchJobs()
        .then((d) => {
          if (!active) return;
          const counts = new Map<string, number>();
          for (const j of d.jobs) {
            counts.set(j.skill, (counts.get(j.skill) || 0) + 1);
          }
          setData(
            Array.from(counts.entries())
              .map(([name, value]) => ({ name, value }))
              .sort((a, b) => b.value - a.value)
          );
        })
        .catch(() => {});

    refresh();

    try {
      const es = createJobStream(() => refresh());
      esRef.current = es;
      es.onerror = () => {
        es.close();
        esRef.current = null;
      };
    } catch {
      // SSE not available
    }

    return () => {
      active = false;
      if (esRef.current) esRef.current.close();
    };
  }, []);

  if (data.length === 0) return null;

  return (
    <Card className="border-clay-800 bg-white shadow-sm">
      <CardContent className="p-4">
        <h3 className="text-xs text-clay-500 uppercase tracking-wider mb-3 font-[family-name:var(--font-sans)]">
          Skill Distribution
        </h3>
        <div className="flex items-center gap-4">
          <div className="w-32 h-32 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={30}
                  outerRadius={55}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e5e5e3",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-1.5">
            {data.slice(0, 5).map((d, i) => (
              <div key={d.name} className="flex items-center gap-2 text-xs">
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="text-clay-300 truncate flex-1">{d.name}</span>
                <span className="text-clay-500 font-[family-name:var(--font-mono)]">
                  {d.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
