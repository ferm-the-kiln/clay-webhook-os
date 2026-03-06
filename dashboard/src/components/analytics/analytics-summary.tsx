"use client";

import type { FeedbackSummary } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { ThumbsUp, BarChart3, TrendingUp, Award } from "lucide-react";

export function AnalyticsSummary({ data }: { data: FeedbackSummary | null }) {
  if (!data) return null;

  const topSkill = data.by_skill.length > 0
    ? [...data.by_skill].sort((a, b) => b.approval_rate - a.approval_rate)[0]
    : null;

  const cards = [
    {
      label: "Total Ratings",
      value: data.total_ratings,
      icon: BarChart3,
      color: "text-kiln-teal",
    },
    {
      label: "Approval Rate",
      value: `${Math.round(data.overall_approval_rate * 100)}%`,
      icon: ThumbsUp,
      color: data.overall_approval_rate >= 0.7 ? "text-kiln-teal" : "text-kiln-coral",
    },
    {
      label: "Top Skill",
      value: topSkill ? topSkill.skill : "N/A",
      sub: topSkill ? `${Math.round(topSkill.approval_rate * 100)}% approval` : undefined,
      icon: Award,
      color: "text-kiln-mustard",
    },
    {
      label: "Skills Rated",
      value: data.by_skill.length,
      icon: TrendingUp,
      color: "text-kiln-teal",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <Card key={c.label} className="border-clay-800 bg-clay-900">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <c.icon className={`h-4 w-4 ${c.color}`} />
              <span className="text-xs text-clay-500 uppercase tracking-wide">
                {c.label}
              </span>
            </div>
            <p className="text-2xl font-bold text-clay-100">{c.value}</p>
            {c.sub && <p className="text-xs text-clay-500 mt-0.5">{c.sub}</p>}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
