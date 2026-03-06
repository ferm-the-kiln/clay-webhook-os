"use client";

import { useState } from "react";
import type { ReviewItem } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { formatRelativeTime } from "@/lib/utils";
import { reviewAction, rerunReviewItem } from "@/lib/api";
import { toast } from "sonner";
import {
  CheckCircle2,
  XCircle,
  Pencil,
  RotateCcw,
  X,
  ChevronDown,
  ChevronRight,
  Clock,
  RefreshCw,
} from "lucide-react";

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

export function ReviewDetail({
  item,
  campaignName,
  onClose,
  onUpdated,
}: {
  item: ReviewItem;
  campaignName?: string | null;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [note, setNote] = useState(item.reviewer_note || "");
  const [revisedInstructions, setRevisedInstructions] = useState("");
  const [showReviseForm, setShowReviseForm] = useState(false);
  const [showInput, setShowInput] = useState(false);
  const [acting, setActing] = useState<string | null>(null);

  const status = statusConfig(item.status);
  const StatusIcon = status.icon;

  const confidencePct = Math.round(item.confidence_score * 100);
  const barColor =
    item.confidence_score >= 0.8
      ? "bg-kiln-teal"
      : item.confidence_score >= 0.5
        ? "bg-kiln-mustard"
        : "bg-kiln-coral";

  const handleAction = async (
    action: "approve" | "reject",
    actionNote?: string
  ) => {
    setActing(action);
    try {
      await reviewAction(item.id, {
        action,
        note: actionNote || note || undefined,
      });
      toast.success(
        action === "approve" ? "Item approved and pushed" : "Item rejected"
      );
      onUpdated();
    } catch (e) {
      toast.error(`Failed to ${action}`, {
        description: (e as Error).message,
      });
    } finally {
      setActing(null);
    }
  };

  const handleRevise = async () => {
    if (!revisedInstructions.trim()) {
      toast.error("Please provide revised instructions");
      return;
    }
    setActing("revise");
    try {
      const result = await reviewAction(item.id, {
        action: "revise",
        note: note || undefined,
        revised_instructions: revisedInstructions,
      });
      toast.success("Item revised and re-run", {
        description: result.confidence
          ? `New confidence: ${Math.round(result.confidence * 100)}%`
          : undefined,
      });
      setShowReviseForm(false);
      setRevisedInstructions("");
      onUpdated();
    } catch (e) {
      toast.error("Failed to revise", {
        description: (e as Error).message,
      });
    } finally {
      setActing(null);
    }
  };

  const handleRerun = async () => {
    setActing("rerun");
    try {
      const result = await rerunReviewItem(item.id);
      toast.success("Re-run complete", {
        description: `New confidence: ${Math.round(result.confidence * 100)}%`,
      });
      onUpdated();
    } catch (e) {
      toast.error("Failed to re-run", {
        description: (e as Error).message,
      });
    } finally {
      setActing(null);
    }
  };

  const isActing = acting !== null;

  return (
    <Card className="border-clay-800 bg-clay-900">
      <CardContent className="p-0">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-clay-800 px-4 py-3">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold font-[family-name:var(--font-sans)] text-clay-100">
              Review Item
            </h3>
            <Badge variant="outline" className={`${status.className} text-xs`}>
              <StatusIcon className="h-3 w-3 mr-1" />
              {status.label}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            className="text-clay-400 hover:text-clay-200"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-4 space-y-4">
          {/* Meta info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <p className="text-xs text-clay-500 uppercase tracking-wide">
                Skill
              </p>
              <p className="text-sm text-clay-200 mt-0.5">{item.skill}</p>
            </div>
            <div>
              <p className="text-xs text-clay-500 uppercase tracking-wide">
                Model
              </p>
              <p className="text-sm text-clay-200 mt-0.5">{item.model}</p>
            </div>
            <div>
              <p className="text-xs text-clay-500 uppercase tracking-wide">
                Created
              </p>
              <p className="text-sm text-clay-200 mt-0.5">
                {formatRelativeTime(item.created_at)}
              </p>
            </div>
            {campaignName && (
              <div>
                <p className="text-xs text-clay-500 uppercase tracking-wide">
                  Campaign
                </p>
                <p className="text-sm text-clay-200 mt-0.5">{campaignName}</p>
              </div>
            )}
            {item.client_slug && (
              <div>
                <p className="text-xs text-clay-500 uppercase tracking-wide">
                  Client
                </p>
                <p className="text-sm text-clay-200 mt-0.5">
                  {item.client_slug}
                </p>
              </div>
            )}
          </div>

          {/* Confidence bar */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-xs text-clay-500 uppercase tracking-wide">
                Confidence Score
              </p>
              <span
                className={`text-sm font-mono font-semibold ${
                  item.confidence_score >= 0.8
                    ? "text-kiln-teal"
                    : item.confidence_score >= 0.5
                      ? "text-kiln-mustard"
                      : "text-kiln-coral"
                }`}
              >
                {confidencePct}%
              </span>
            </div>
            <div className="h-2 bg-clay-800 rounded-full overflow-hidden">
              <div
                className={`h-full ${barColor} rounded-full transition-all duration-500`}
                style={{ width: `${confidencePct}%` }}
              />
            </div>
          </div>

          {/* Input data — collapsible */}
          <div>
            <button
              className="flex items-center gap-1.5 text-xs text-clay-500 uppercase tracking-wide mb-1 hover:text-clay-400 transition-colors"
              onClick={() => setShowInput(!showInput)}
            >
              {showInput ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              Input Data
            </button>
            {showInput && (
              <pre className="text-xs text-clay-300 bg-clay-950 border border-clay-800 rounded-md p-3 overflow-x-auto max-h-40">
                {JSON.stringify(item.input_data, null, 2)}
              </pre>
            )}
          </div>

          {/* Output */}
          <div>
            <p className="text-xs text-clay-500 uppercase tracking-wide mb-1">
              Output
            </p>
            <pre className="text-xs text-clay-300 bg-clay-950 border border-clay-800 rounded-md p-3 overflow-x-auto max-h-72">
              {JSON.stringify(item.output, null, 2)}
            </pre>
          </div>

          {/* Note textarea */}
          <div>
            <p className="text-xs text-clay-500 uppercase tracking-wide mb-1">
              Reviewer Note
            </p>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add notes about this output (optional)"
              className="h-20 border-clay-700 bg-clay-950 text-clay-200 placeholder:text-clay-600 text-sm resize-none"
              disabled={isActing}
            />
          </div>

          {/* Revise form */}
          {showReviseForm && (
            <div className="border border-kiln-mustard/20 bg-kiln-mustard/5 rounded-md p-3 space-y-2">
              <p className="text-xs text-kiln-mustard uppercase tracking-wide font-medium">
                Revised Instructions
              </p>
              <Textarea
                value={revisedInstructions}
                onChange={(e) => setRevisedInstructions(e.target.value)}
                placeholder="Describe what should change (e.g., 'Make the tone more casual' or 'Focus on the ROI angle')"
                className="h-24 border-kiln-mustard/20 bg-clay-950 text-clay-200 placeholder:text-clay-600 text-sm resize-none"
                disabled={isActing}
              />
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  disabled={isActing}
                  onClick={handleRevise}
                  className="bg-kiln-mustard text-clay-950 hover:bg-kiln-mustard/80 text-xs"
                >
                  {acting === "revise" ? (
                    <>
                      <RotateCcw className="h-3 w-3 mr-1 animate-spin" />
                      Revising...
                    </>
                  ) : (
                    <>
                      <Pencil className="h-3 w-3 mr-1" />
                      Revise & Re-run
                    </>
                  )}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isActing}
                  onClick={() => {
                    setShowReviseForm(false);
                    setRevisedInstructions("");
                  }}
                  className="border-clay-700 text-clay-400 text-xs"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-clay-800">
            <Button
              size="sm"
              disabled={isActing}
              onClick={() => handleAction("approve")}
              className="bg-kiln-teal text-white hover:bg-kiln-teal/80 text-xs"
            >
              {acting === "approve" ? (
                <>
                  <RotateCcw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  Approving...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
                  Approve
                </>
              )}
            </Button>

            <Button
              size="sm"
              disabled={isActing}
              onClick={() => handleAction("reject", note)}
              className="bg-kiln-coral text-white hover:bg-kiln-coral/80 text-xs"
            >
              {acting === "reject" ? (
                <>
                  <RotateCcw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  Rejecting...
                </>
              ) : (
                <>
                  <XCircle className="h-3.5 w-3.5 mr-1.5" />
                  Reject
                </>
              )}
            </Button>

            <Button
              size="sm"
              variant="outline"
              disabled={isActing}
              onClick={() => setShowReviseForm(!showReviseForm)}
              className="border-kiln-mustard/30 text-kiln-mustard hover:bg-kiln-mustard/10 text-xs"
            >
              <Pencil className="h-3.5 w-3.5 mr-1.5" />
              Revise
            </Button>

            <Button
              size="sm"
              variant="outline"
              disabled={isActing}
              onClick={handleRerun}
              className="border-clay-700 text-clay-400 hover:text-clay-200 text-xs"
            >
              {acting === "rerun" ? (
                <>
                  <RotateCcw className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  Re-running...
                </>
              ) : (
                <>
                  <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                  Re-run
                </>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
