"use client";

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

export function ClientBreakdown({
  byClient,
}: {
  byClient: Record<
    string,
    { total: number; thumbs_up: number; approval_rate: number }
  >;
}) {
  const entries = Object.entries(byClient);
  if (entries.length === 0) {
    return (
      <div className="rounded-xl border border-clay-800 bg-white shadow-sm p-4">
        <h4 className="text-sm font-medium text-clay-300 mb-4">
          By Client
        </h4>
        <p className="text-sm text-clay-500 text-center py-4">
          No client-specific feedback yet.
        </p>
      </div>
    );
  }

  const data = entries
    .map(([slug, v]) => ({
      client: slug,
      rate: Math.round(v.approval_rate * 100),
      total: v.total,
    }))
    .sort((a, b) => b.rate - a.rate);

  return (
    <div className="rounded-xl border border-clay-800 bg-white shadow-sm p-4">
      <h4 className="text-sm font-medium text-clay-300 mb-4">
        Approval by Client
      </h4>
      <ResponsiveContainer width="100%" height={Math.max(200, data.length * 40)}>
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
            dataKey="client"
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
