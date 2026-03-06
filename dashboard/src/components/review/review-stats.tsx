"use client";

import type { ReviewStats as ReviewStatsType } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Clock, CheckCircle2, XCircle, TrendingUp } from "lucide-react";

export function ReviewStatsBar({ stats }: { stats: ReviewStatsType | null }) {
  if (!stats) return null;

  const approvalPct =
    stats.total > 0 ? Math.round(stats.approval_rate * 100) : 0;

  const cards = [
    {
      label: "Pending Review",
      value: stats.pending,
      icon: Clock,
      color: "text-kiln-mustard",
      highlight: stats.pending > 0,
    },
    {
      label: "Approved",
      value: stats.approved,
      icon: CheckCircle2,
      color: "text-kiln-teal",
      highlight: false,
    },
    {
      label: "Rejected",
      value: stats.rejected,
      icon: XCircle,
      color: "text-kiln-coral",
      highlight: false,
    },
    {
      label: "Approval Rate",
      value: stats.total > 0 ? `${approvalPct}%` : "N/A",
      icon: TrendingUp,
      color: approvalPct >= 70 ? "text-kiln-teal" : "text-kiln-coral",
      highlight: false,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <Card
          key={c.label}
          className={
            c.highlight
              ? "border-kiln-mustard/30 bg-kiln-mustard/5"
              : "border-clay-800 bg-clay-900"
          }
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <c.icon className={`h-4 w-4 ${c.color}`} />
              <span className="text-xs text-clay-500 uppercase tracking-wide">
                {c.label}
              </span>
            </div>
            <p className="text-2xl font-bold text-clay-100">{c.value}</p>
            {c.label === "Pending Review" && stats.pending > 0 && (
              <p className="text-xs text-kiln-mustard mt-0.5">
                {stats.pending === 1
                  ? "1 item needs review"
                  : `${stats.pending} items need review`}
              </p>
            )}
            {c.label === "Approval Rate" && stats.revised > 0 && (
              <p className="text-xs text-clay-500 mt-0.5">
                {stats.revised} revised
              </p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
