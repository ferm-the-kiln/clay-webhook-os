"use client";

import { motion } from "framer-motion";
import { Send, ThumbsUp, Megaphone, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn, formatNumber, formatPercent } from "@/lib/utils";
import type { OutcomeDashboard } from "@/lib/types";

interface OutcomeCardsProps {
  data: OutcomeDashboard;
}

function approvalColor(rate: number): string {
  if (rate >= 0.8) return "text-kiln-teal";
  if (rate >= 0.6) return "text-kiln-mustard";
  return "text-kiln-coral";
}

function approvalBorderColor(rate: number): string {
  if (rate >= 0.8) return "border-kiln-teal/30";
  if (rate >= 0.6) return "border-kiln-mustard/30";
  return "border-kiln-coral/30";
}

const cards = [
  {
    key: "emails_sent" as const,
    label: "Emails Sent",
    icon: Send,
    getValue: (d: OutcomeDashboard) => formatNumber(d.overview.total_sent),
    getAccent: () => "text-kiln-teal",
    getBorder: () => "border-kiln-teal/30",
    getSubtitle: (d: OutcomeDashboard) =>
      `${formatNumber(d.overview.total_processed)} processed`,
  },
  {
    key: "approval_rate" as const,
    label: "Approval Rate",
    icon: ThumbsUp,
    getValue: (d: OutcomeDashboard) =>
      formatPercent(d.overview.overall_approval_rate),
    getAccent: (d: OutcomeDashboard) =>
      approvalColor(d.overview.overall_approval_rate),
    getBorder: (d: OutcomeDashboard) =>
      approvalBorderColor(d.overview.overall_approval_rate),
    getSubtitle: (d: OutcomeDashboard) =>
      `${formatNumber(d.overview.total_approved)} approved`,
  },
  {
    key: "active_campaigns" as const,
    label: "Active Campaigns",
    icon: Megaphone,
    getValue: (d: OutcomeDashboard) =>
      String(d.overview.active_campaigns),
    getAccent: () => "text-kiln-teal",
    getBorder: () => "border-clay-700",
    getSubtitle: (d: OutcomeDashboard) =>
      `${d.overview.total_campaigns} total`,
  },
  {
    key: "pending_review" as const,
    label: "Pending Review",
    icon: Clock,
    getValue: (d: OutcomeDashboard) =>
      String(d.review_queue.pending),
    getAccent: (d: OutcomeDashboard) =>
      d.review_queue.pending > 0 ? "text-kiln-mustard" : "text-clay-400",
    getBorder: (d: OutcomeDashboard) =>
      d.review_queue.pending > 0
        ? "border-kiln-mustard/30"
        : "border-clay-700",
    getSubtitle: (d: OutcomeDashboard) =>
      `${d.review_queue.total} total reviews`,
  },
];

export function OutcomeCards({ data }: OutcomeCardsProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, index) => {
        const Icon = card.icon;
        const accent = card.getAccent(data);
        const border = card.getBorder(data);

        return (
          <motion.div
            key={card.key}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
          >
            <Card
              className={cn(
                "bg-clay-800 border-clay-700 hover:border-kiln-teal/30 transition-all duration-200",
                border
              )}
            >
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs text-clay-500 uppercase tracking-wide font-[family-name:var(--font-sans)]">
                    {card.label}
                  </p>
                  <Icon className={cn("h-4 w-4", accent)} />
                </div>
                <p
                  className={cn(
                    "text-3xl font-semibold font-[family-name:var(--font-mono)]",
                    accent
                  )}
                >
                  {card.getValue(data)}
                </p>
                <p className="text-xs text-clay-500 mt-1">
                  {card.getSubtitle(data)}
                </p>
              </CardContent>
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}
