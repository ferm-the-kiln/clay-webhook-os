"use client";

import { useState } from "react";
import { Check, RotateCcw, Send, ChevronDown, ChevronUp, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { processApproval } from "@/lib/api";
import { toast } from "sonner";
import type { PortalUpdate, ApprovalStatus } from "@/lib/types";

const STATUS_CONFIG: Record<string, { label: string; color: string; bgColor: string; borderColor: string }> = {
  pending_review: { label: "Pending Review", color: "text-amber-400", bgColor: "bg-amber-500/10", borderColor: "border-amber-500/20" },
  approved: { label: "Approved", color: "text-emerald-400", bgColor: "bg-emerald-500/10", borderColor: "border-emerald-500/20" },
  revision_requested: { label: "Revision Requested", color: "text-orange-400", bgColor: "bg-orange-500/10", borderColor: "border-orange-500/20" },
  resubmitted: { label: "Resubmitted", color: "text-purple-400", bgColor: "bg-purple-500/10", borderColor: "border-purple-500/20" },
};

function getStoredAuthor(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("portal_author_name") || "";
}

function formatTime(epoch: number): string {
  return new Date(epoch * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface ApprovalBannerProps {
  slug: string;
  update: PortalUpdate;
  onUpdated: () => void;
}

export function ApprovalBanner({ slug, update, onUpdated }: ApprovalBannerProps) {
  const [showRevisionInput, setShowRevisionInput] = useState(false);
  const [revisionNotes, setRevisionNotes] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [processing, setProcessing] = useState(false);

  const status = update.approval_status;
  if (!status) return null;

  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending_review;
  const history = update.approval_history || [];

  const handleAction = async (action: "approve" | "request_revision" | "resubmit", notes = "") => {
    const author = getStoredAuthor() || "Anonymous";
    setProcessing(true);
    try {
      await processApproval(slug, update.id, {
        action,
        actor_name: author,
        notes,
      });
      toast.success(
        action === "approve" ? "Deliverable approved" :
        action === "request_revision" ? "Revision requested" :
        "Deliverable resubmitted"
      );
      setShowRevisionInput(false);
      setRevisionNotes("");
      onUpdated();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to process approval");
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className={cn("mt-3 rounded-lg border p-3", config.bgColor, config.borderColor)}>
      {/* Status badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={cn("text-xs font-semibold px-2 py-0.5 rounded-full", config.color, config.bgColor)}>
            {config.label}
          </span>
          {status === "approved" && update.approved_by && (
            <span className="text-xs text-clay-300">
              by {update.approved_by} {update.approved_at ? `on ${formatTime(update.approved_at)}` : ""}
            </span>
          )}
          {status === "revision_requested" && update.revision_notes && (
            <span className="text-xs text-orange-400/70 truncate max-w-[200px]">
              &ldquo;{update.revision_notes}&rdquo;
            </span>
          )}
        </div>

        {history.length > 0 && (
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="text-[11px] text-clay-300 hover:text-clay-100 flex items-center gap-0.5"
          >
            <Clock className="h-3 w-3" />
            {history.length} event{history.length !== 1 ? "s" : ""}
            {showHistory ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 mt-2.5">
        {(status === "pending_review" || status === "resubmitted") && (
          <>
            <Button
              size="sm"
              onClick={() => handleAction("approve")}
              disabled={processing}
              className="bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5 h-7 text-xs"
            >
              <Check className="h-3 w-3" />
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowRevisionInput(!showRevisionInput)}
              disabled={processing}
              className="border-orange-500/30 text-orange-400 hover:bg-orange-500/10 gap-1.5 h-7 text-xs"
            >
              <RotateCcw className="h-3 w-3" />
              Request Revision
            </Button>
          </>
        )}
        {status === "revision_requested" && (
          <Button
            size="sm"
            onClick={() => handleAction("resubmit")}
            disabled={processing}
            className="bg-purple-600 hover:bg-purple-500 text-white gap-1.5 h-7 text-xs"
          >
            <Send className="h-3 w-3" />
            Resubmit
          </Button>
        )}
      </div>

      {/* Revision notes input */}
      {showRevisionInput && (
        <div className="mt-2 flex gap-2">
          <input
            type="text"
            value={revisionNotes}
            onChange={(e) => setRevisionNotes(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAction("request_revision", revisionNotes);
            }}
            placeholder="What needs to change?"
            className="flex-1 bg-clay-900 border border-orange-500/30 rounded-md px-2.5 py-1 text-xs text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-orange-400"
            autoFocus
          />
          <Button
            size="sm"
            onClick={() => handleAction("request_revision", revisionNotes)}
            disabled={processing}
            className="bg-orange-600 hover:bg-orange-500 text-white h-7 text-xs"
          >
            Send
          </Button>
        </div>
      )}

      {/* History timeline */}
      {showHistory && history.length > 0 && (
        <div className="mt-3 border-t border-clay-700/40 pt-2 space-y-1.5">
          {history.map((h, i) => {
            const actionLabel = h.action === "approve" ? "Approved" : h.action === "request_revision" ? "Requested revision" : "Resubmitted";
            return (
              <div key={i} className="flex items-start gap-2 text-[10px]">
                <span className="text-clay-400 shrink-0">{formatTime(h.timestamp)}</span>
                <span className="text-clay-200">
                  <strong>{h.actor_name}</strong> {actionLabel.toLowerCase()}
                  {h.notes ? `: "${h.notes}"` : ""}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
