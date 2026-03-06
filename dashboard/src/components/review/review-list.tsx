"use client";

import { useState } from "react";
import type { ReviewItem } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeTime } from "@/lib/utils";
import {
  ChevronDown,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Inbox,
} from "lucide-react";

function confidenceColor(score: number): string {
  if (score >= 0.8) return "text-kiln-teal";
  if (score >= 0.5) return "text-kiln-mustard";
  return "text-kiln-coral";
}

function confidenceBg(score: number): string {
  if (score >= 0.8) return "bg-kiln-teal/10 border-kiln-teal/30";
  if (score >= 0.5) return "bg-kiln-mustard/10 border-kiln-mustard/30";
  return "bg-kiln-coral/10 border-kiln-coral/30";
}

function statusConfig(status: string) {
  switch (status) {
    case "pending":
      return {
        label: "Pending",
        icon: Clock,
        className:
          "bg-kiln-mustard/15 text-kiln-mustard border-kiln-mustard/30",
      };
    case "approved":
      return {
        label: "Approved",
        icon: CheckCircle2,
        className: "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30",
      };
    case "rejected":
      return {
        label: "Rejected",
        icon: XCircle,
        className: "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/30",
      };
    case "revised":
      return {
        label: "Revised",
        icon: RefreshCw,
        className: "bg-blue-500/15 text-blue-400 border-blue-500/30",
      };
    default:
      return {
        label: status,
        icon: Clock,
        className: "bg-clay-800 text-clay-400 border-clay-700",
      };
  }
}

function ReviewItemRow({
  item,
  onSelect,
}: {
  item: ReviewItem;
  onSelect: (item: ReviewItem) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const status = statusConfig(item.status);
  const StatusIcon = status.icon;

  return (
    <Card className="border-clay-800 bg-clay-900 hover:border-clay-700 transition-colors">
      <CardContent className="p-0">
        {/* Main row — clickable header */}
        <button
          className="w-full flex items-center gap-4 px-4 py-3 text-left"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-clay-500 shrink-0" />
          ) : (
            <ChevronRight className="h-4 w-4 text-clay-500 shrink-0" />
          )}

          {/* Skill */}
          <span className="text-sm font-medium text-clay-200 min-w-[100px]">
            {item.skill}
          </span>

          {/* Confidence */}
          <Badge
            variant="outline"
            className={`${confidenceBg(item.confidence_score)} ${confidenceColor(item.confidence_score)} text-xs font-mono`}
          >
            {(item.confidence_score * 100).toFixed(0)}%
          </Badge>

          {/* Status */}
          <Badge variant="outline" className={`${status.className} text-xs`}>
            <StatusIcon className="h-3 w-3 mr-1" />
            {status.label}
          </Badge>

          {/* Row ID */}
          {item.row_id && (
            <span className="text-xs text-clay-500 hidden md:inline">
              Row: {item.row_id}
            </span>
          )}

          {/* Spacer */}
          <span className="flex-1" />

          {/* Timestamp */}
          <span className="text-xs text-clay-500">
            {formatRelativeTime(item.created_at)}
          </span>
        </button>

        {/* Expanded content */}
        {expanded && (
          <div className="border-t border-clay-800 px-4 py-3 space-y-3">
            {/* Input data */}
            <div>
              <p className="text-xs text-clay-500 uppercase tracking-wide mb-1">
                Input Data
              </p>
              <pre className="text-xs text-clay-300 bg-clay-950 border border-clay-800 rounded-md p-3 overflow-x-auto max-h-40">
                {JSON.stringify(item.input_data, null, 2)}
              </pre>
            </div>

            {/* Output */}
            <div>
              <p className="text-xs text-clay-500 uppercase tracking-wide mb-1">
                Output
              </p>
              <pre className="text-xs text-clay-300 bg-clay-950 border border-clay-800 rounded-md p-3 overflow-x-auto max-h-60">
                {JSON.stringify(item.output, null, 2)}
              </pre>
            </div>

            {/* Reviewer note */}
            {item.reviewer_note && (
              <div>
                <p className="text-xs text-clay-500 uppercase tracking-wide mb-1">
                  Reviewer Note
                </p>
                <p className="text-sm text-clay-300 bg-clay-950 border border-clay-800 rounded-md p-3">
                  {item.reviewer_note}
                </p>
              </div>
            )}

            {/* Action button */}
            <div className="flex justify-end pt-1">
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect(item);
                }}
                className="border-kiln-teal/30 text-kiln-teal hover:bg-kiln-teal/10 text-xs"
              >
                Open Review Panel
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function ReviewList({
  items,
  loading,
  onSelect,
}: {
  items: ReviewItem[];
  loading: boolean;
  onSelect: (item: ReviewItem) => void;
}) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i} className="border-clay-800 bg-clay-900 animate-pulse">
            <CardContent className="p-4">
              <div className="flex items-center gap-4">
                <div className="h-4 w-4 bg-clay-800 rounded" />
                <div className="h-4 w-24 bg-clay-800 rounded" />
                <div className="h-5 w-12 bg-clay-800 rounded-full" />
                <div className="h-5 w-16 bg-clay-800 rounded-full" />
                <div className="flex-1" />
                <div className="h-4 w-16 bg-clay-800 rounded" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <Card className="border-clay-800 bg-clay-900">
        <CardContent className="p-12 text-center">
          <Inbox className="h-10 w-10 text-clay-600 mx-auto mb-3" />
          <p className="text-clay-400 text-sm">No review items found</p>
          <p className="text-clay-600 text-xs mt-1">
            Items will appear here when outputs fall below the confidence
            threshold
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <ReviewItemRow key={item.id} item={item} onSelect={onSelect} />
      ))}
    </div>
  );
}
