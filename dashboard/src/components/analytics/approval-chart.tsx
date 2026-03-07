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
    <div className="rounded-xl border border-clay-800 bg-white shadow-sm p-4">
      <h4 className="text-sm font-medium text-clay-300 mb-4">
        Approval Rate by Skill
      </h4>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e3" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fill: "#a8a8a5", fontSize: 11 }}
            tickFormatter={(v) => `${v}%`}
          />
          <YAxis
            type="category"
            dataKey="skill"
            tick={{ fill: "#737371", fontSize: 12 }}
            width={120}
          />
          <Tooltip
            contentStyle={{
              background: "#ffffff",
              border: "1px solid #e5e5e3",
              borderRadius: 8,
              color: "#111111",
            }}
            formatter={(value) => [`${value}%`, "Approval"]}
          />
          <Bar dataKey="rate" radius={[0, 4, 4, 0]} maxBarSize={24}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={
                  entry.rate >= 70
                    ? "#015870"
                    : entry.rate >= 40
                      ? "#ca8a04"
                      : "#f03603"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
