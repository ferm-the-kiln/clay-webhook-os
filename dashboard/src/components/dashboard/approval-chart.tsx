"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  Cell,
} from "recharts";
import type { FeedbackSummary } from "@/lib/types";

interface ApprovalChartProps {
  feedback: FeedbackSummary;
}

function getBarColor(rate: number): string {
  if (rate >= 80) return "#015870";
  if (rate >= 60) return "#ca8a04";
  return "#f03603";
}

interface ChartEntry {
  skill: string;
  approval_rate: number;
  total: number;
}

interface TooltipPayloadItem {
  payload: ChartEntry;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;

  const entry = payload[0].payload;
  const rateColor = getBarColor(entry.approval_rate);

  return (
    <div className="bg-white border border-clay-800 rounded-lg px-3 py-2 shadow-md">
      <p className="text-xs text-clay-300 font-medium mb-1">{label}</p>
      <div className="flex items-center gap-2">
        <span
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: rateColor }}
        />
        <span className="text-xs text-clay-400">
          Approval:{" "}
          <span className="text-clay-100 font-[family-name:var(--font-mono)]">
            {entry.approval_rate.toFixed(1)}%
          </span>
        </span>
      </div>
      <p className="text-xs text-clay-500 mt-0.5">
        {entry.total} total rating{entry.total !== 1 ? "s" : ""}
      </p>
    </div>
  );
}

export function ApprovalChart({ feedback }: ApprovalChartProps) {
  const data: ChartEntry[] = feedback.by_skill.map((s) => ({
    skill: s.skill,
    approval_rate: s.approval_rate * 100,
    total: s.total,
  }));

  if (data.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
    >
      <Card className="border-clay-800 bg-white shadow-sm">
        <CardContent className="p-5">
          <h3 className="text-xs text-clay-500 uppercase tracking-wider mb-4 font-[family-name:var(--font-sans)]">
            Approval Rate by Skill (7d)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={data}
              margin={{ top: 4, right: 8, bottom: 0, left: -16 }}
            >
              <XAxis
                dataKey="skill"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#a8a8a5", fontSize: 11 }}
                interval={0}
                angle={data.length > 5 ? -30 : 0}
                textAnchor={data.length > 5 ? "end" : "middle"}
                height={data.length > 5 ? 60 : 30}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#a8a8a5", fontSize: 11 }}
                domain={[0, 100]}
                tickFormatter={(v: number) => `${v}%`}
              />
              <RechartsTooltip
                content={<CustomTooltip />}
                cursor={{ fill: "rgba(91, 154, 139, 0.08)" }}
              />
              <Bar dataKey="approval_rate" radius={[4, 4, 0, 0]} maxBarSize={48}>
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getBarColor(entry.approval_rate)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </motion.div>
  );
}
