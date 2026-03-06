"use client";

import type { SkillAnalytics } from "@/lib/types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

export function ApprovalChart({ skills }: { skills: SkillAnalytics[] }) {
  if (skills.length === 0) return null;

  const data = [...skills]
    .sort((a, b) => b.approval_rate - a.approval_rate)
    .map((s) => ({
      skill: s.skill,
      rate: Math.round(s.approval_rate * 100),
      total: s.total,
    }));

  return (
    <div className="rounded-xl border border-clay-800 bg-clay-900 p-4">
      <h4 className="text-sm font-medium text-clay-300 mb-4">
        Approval Rate by Skill
      </h4>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2724" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fill: "#7a7570", fontSize: 11 }}
            tickFormatter={(v) => `${v}%`}
          />
          <YAxis
            type="category"
            dataKey="skill"
            tick={{ fill: "#a09a94", fontSize: 12 }}
            width={120}
          />
          <Tooltip
            contentStyle={{
              background: "#1e1c1a",
              border: "1px solid #3a3632",
              borderRadius: 8,
              color: "#e8e2da",
            }}
            formatter={(value) => [`${value}%`, "Approval"]}
          />
          <Bar dataKey="rate" radius={[0, 4, 4, 0]} maxBarSize={24}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={
                  entry.rate >= 70
                    ? "#5ce0d2"
                    : entry.rate >= 40
                      ? "#e0c85c"
                      : "#e07a5c"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
