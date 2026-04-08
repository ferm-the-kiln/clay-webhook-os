"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import {
  fetchPublicPortal,
  publicToggleAction,
  publicAcknowledgeSOP,
  publicProcessApproval,
  publicPostComment,
} from "@/lib/api";
import type { PublicPortalView } from "@/lib/types";
import { cn, formatRelativeTime } from "@/lib/utils";
import {
  FileText,
  MessageSquare,
  CheckSquare,
  Square,
  ChevronDown,
  ChevronRight,
  User,
  ShieldAlert,
  CheckCircle,
  AlertCircle,
  Check,
  RotateCcw,
  Send,
  Loader2,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-400",
  onboarding: "bg-blue-500/15 text-blue-400",
  paused: "bg-amber-500/15 text-amber-400",
  churned: "bg-red-500/15 text-red-400",
};

const CATEGORY_COLORS: Record<string, string> = {
  onboarding: "text-blue-400 bg-blue-500/10",
  reporting: "text-emerald-400 bg-emerald-500/10",
  communication: "text-purple-400 bg-purple-500/10",
  approval: "text-amber-400 bg-amber-500/10",
  general: "text-clay-300 bg-clay-700",
};

const PRIORITY_DOTS: Record<string, string> = {
  high: "bg-red-400",
  normal: "bg-clay-400",
  low: "bg-clay-600",
};

const TYPE_COLORS: Record<string, string> = {
  update: "text-blue-400 bg-blue-500/10",
  milestone: "text-emerald-400 bg-emerald-500/10",
  deliverable: "text-purple-400 bg-purple-500/10",
  note: "text-amber-400 bg-amber-500/10",
};

export default function PublicPortalPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const slug = params.slug as string;
  const token = searchParams.get("token") || "";

  const [portal, setPortal] = useState<PublicPortalView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSop, setExpandedSop] = useState<string | null>(null);
  const [clientName, setClientName] = useState("");
  const [commentTexts, setCommentTexts] = useState<Record<string, string>>({});
  const [postingComment, setPostingComment] = useState<string | null>(null);
  const [processingAction, setProcessingAction] = useState<string | null>(null);
  const [revisionInput, setRevisionInput] = useState<string | null>(null);
  const [revisionNotes, setRevisionNotes] = useState("");

  const loadPortal = useCallback(() => {
    if (!token) return;
    fetchPublicPortal(slug, token)
      .then(setPortal)
      .catch((e) => setError(e instanceof Error ? e.message : "Access denied"))
      .finally(() => setLoading(false));
  }, [slug, token]);

  useEffect(() => {
    if (!token) {
      setError("No access token provided");
      setLoading(false);
      return;
    }
    loadPortal();
  }, [token, loadPortal]);

  // Get client name from localStorage or prompt
  useEffect(() => {
    const stored = localStorage.getItem(`portal-client-name:${slug}`);
    if (stored) setClientName(stored);
  }, [slug]);

  const saveClientName = (name: string) => {
    setClientName(name);
    localStorage.setItem(`portal-client-name:${slug}`, name);
  };

  const brandColor = portal?.brand_color || undefined;

  const handleToggleAction = async (actionId: string) => {
    setProcessingAction(actionId);
    try {
      await publicToggleAction(slug, token, actionId);
      loadPortal();
    } catch {
      // silently fail
    } finally {
      setProcessingAction(null);
    }
  };

  const handleAcknowledgeSOP = async (sopId: string) => {
    const name = clientName || "Client";
    try {
      await publicAcknowledgeSOP(slug, token, sopId, name);
      loadPortal();
    } catch {
      // silently fail
    }
  };

  const handleApproval = async (updateId: string, action: "approve" | "request_revision", notes = "") => {
    const name = clientName || "Client";
    try {
      await publicProcessApproval(slug, token, updateId, {
        action,
        actor_name: name,
        actor_org: "client",
        notes,
      });
      setRevisionInput(null);
      setRevisionNotes("");
      loadPortal();
    } catch {
      // silently fail
    }
  };

  const handlePostComment = async (updateId: string) => {
    const text = commentTexts[updateId]?.trim();
    if (!text) return;
    const name = clientName || "Client";
    setPostingComment(updateId);
    try {
      await publicPostComment(slug, token, updateId, { body: text, author: name });
      setCommentTexts((prev) => ({ ...prev, [updateId]: "" }));
      loadPortal();
    } catch {
      // silently fail
    } finally {
      setPostingComment(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-clay-900 flex items-center justify-center">
        <div className="animate-pulse text-clay-300">Loading portal...</div>
      </div>
    );
  }

  if (error || !portal) {
    return (
      <div className="min-h-screen bg-clay-900 flex items-center justify-center">
        <div className="text-center space-y-3">
          <ShieldAlert className="h-12 w-12 text-red-400 mx-auto" />
          <h1 className="text-lg font-semibold text-clay-100">Access Denied</h1>
          <p className="text-sm text-clay-300">{error || "Invalid or expired share link."}</p>
        </div>
      </div>
    );
  }

  const openActions = portal.actions.filter((a) => a.status !== "done");
  const clientOpenActions = openActions.filter((a) => a.owner === "client");
  const doneActions = portal.actions.filter((a) => a.status === "done");

  return (
    <div className="min-h-screen bg-clay-900">
      {/* Client name prompt — shown once */}
      {!clientName && (
        <div className="bg-clay-800 border-b border-clay-700 py-3">
          <div className="max-w-3xl mx-auto px-4 flex items-center gap-3">
            <span className="text-sm text-clay-300">Your name:</span>
            <input
              type="text"
              placeholder="Enter your name to interact..."
              className="flex-1 bg-clay-900 border border-clay-600 rounded-lg px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-300 focus:outline-none focus:border-clay-400"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  const val = (e.target as HTMLInputElement).value.trim();
                  if (val) saveClientName(val);
                }
              }}
            />
          </div>
        </div>
      )}

      {/* Sticky attention banner */}
      {clientOpenActions.length > 0 && (
        <div className="sticky top-0 z-10 bg-gradient-to-r from-amber-500/10 to-orange-500/10 border-b border-amber-500/20 py-2.5">
          <div className="max-w-3xl mx-auto px-4 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
            <span className="text-sm font-medium text-amber-400">
              You have {clientOpenActions.length} action{clientOpenActions.length !== 1 ? "s" : ""} that need{clientOpenActions.length === 1 ? "s" : ""} your attention
            </span>
          </div>
        </div>
      )}

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-5">
        {/* Header */}
        <div
          className="space-y-2"
          style={brandColor ? { borderTop: `3px solid ${brandColor}`, paddingTop: "1rem" } : undefined}
        >
          <h1 className="text-2xl font-bold text-clay-100">{portal.name}</h1>
          <span
            className={cn(
              "text-[11px] px-2 py-0.5 rounded-full font-medium inline-block",
              STATUS_COLORS[portal.status] || STATUS_COLORS.active
            )}
          >
            {portal.status}
          </span>
        </div>

        {/* SOPs */}
        {portal.sops.length > 0 && (
          <div>
            <h2
              className="text-base font-semibold text-clay-200 mb-3 flex items-center gap-2"
              style={brandColor ? { color: brandColor } : undefined}
            >
              <FileText className="h-4 w-4" />
              Standard Operating Procedures ({portal.sops.length})
            </h2>
            <div className="space-y-2">
              {portal.sops.map((sop) => {
                const isAcked = !!portal.sop_acks?.[sop.id];
                return (
                  <div key={sop.id} className="rounded-lg border border-clay-700 bg-clay-850 overflow-hidden retro-raised">
                    <button
                      onClick={() => setExpandedSop(expandedSop === sop.id ? null : sop.id)}
                      className="w-full flex items-center gap-3 p-3.5 text-left hover:bg-clay-750 transition-colors"
                    >
                      {expandedSop === sop.id ? (
                        <ChevronDown className="h-4 w-4 text-clay-300 shrink-0" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-clay-300 shrink-0" />
                      )}
                      <span className="flex-1 text-sm font-medium text-clay-100">{sop.title}</span>
                      {isAcked && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium flex items-center gap-1 shrink-0">
                          <CheckCircle className="h-2.5 w-2.5" />
                          Acknowledged
                        </span>
                      )}
                      <span
                        className={cn(
                          "text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0",
                          CATEGORY_COLORS[sop.category] || CATEGORY_COLORS.general
                        )}
                      >
                        {sop.category}
                      </span>
                    </button>
                    {expandedSop === sop.id && (
                      <div className="border-t border-clay-700 p-4 space-y-3">
                        <div className="prose prose-invert prose-sm max-w-none text-clay-300 whitespace-pre-wrap">
                          {sop.content || "No content."}
                        </div>
                        {!isAcked && clientName && (
                          <button
                            onClick={() => handleAcknowledgeSOP(sop.id)}
                            className="text-sm px-4 py-2 rounded-lg font-medium transition-colors"
                            style={brandColor
                              ? { backgroundColor: `${brandColor}20`, color: brandColor, border: `1px solid ${brandColor}30` }
                              : { backgroundColor: "rgba(46, 196, 182, 0.1)", color: "#2ec4b6", border: "1px solid rgba(46, 196, 182, 0.2)" }
                            }
                          >
                            <CheckCircle className="h-3.5 w-3.5 inline mr-1.5" />
                            I Acknowledge
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action Items */}
        {portal.actions.length > 0 && (
          <div>
            <h2
              className="text-base font-semibold text-clay-200 mb-3 flex items-center gap-2"
              style={brandColor ? { color: brandColor } : undefined}
            >
              <CheckSquare className="h-4 w-4" />
              Action Items ({openActions.length} open)
            </h2>
            {/* Progress bar */}
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-clay-300">
                  {doneActions.length} of {portal.actions.length} complete
                </span>
                <span className="text-xs text-clay-300">
                  {Math.round((doneActions.length / portal.actions.length) * 100)}%
                </span>
              </div>
              <div className="h-2 bg-clay-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${(doneActions.length / portal.actions.length) * 100}%`,
                    backgroundColor: brandColor || "#2ec4b6",
                  }}
                />
              </div>
            </div>
            <div className="space-y-2">
              {[...openActions, ...doneActions].map((action) => {
                const isDone = action.status === "done";
                const isClient = action.owner === "client";
                const isProcessing = processingAction === action.id;
                return (
                  <div
                    key={action.id}
                    className={cn(
                      "flex items-start gap-3 rounded-lg border bg-clay-850 p-3.5 retro-raised transition-colors",
                      isClient && !isDone ? "border-amber-500/20" : "border-clay-700"
                    )}
                  >
                    {/* Interactive checkbox for client-owned actions */}
                    {isClient && !isDone ? (
                      <button
                        onClick={() => handleToggleAction(action.id)}
                        disabled={isProcessing}
                        className="mt-0.5 h-5 w-5 rounded border-2 border-clay-500 flex items-center justify-center shrink-0 hover:border-emerald-400 hover:bg-emerald-400/10 transition-colors"
                      >
                        {isProcessing ? (
                          <Loader2 className="h-3 w-3 text-clay-300 animate-spin" />
                        ) : (
                          <Check className="h-3 w-3 text-transparent hover:text-emerald-400" />
                        )}
                      </button>
                    ) : isDone ? (
                      <CheckSquare className="h-5 w-5 text-emerald-400 mt-0.5 shrink-0" />
                    ) : (
                      <Square className="h-5 w-5 text-clay-300 mt-0.5 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={cn("h-2 w-2 rounded-full shrink-0", PRIORITY_DOTS[action.priority])} />
                        <span
                          className={cn(
                            "text-sm font-medium",
                            isDone ? "text-clay-300 line-through" : "text-clay-100"
                          )}
                        >
                          {action.title}
                        </span>
                        {isClient && !isDone && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 font-medium">
                            Your action
                          </span>
                        )}
                      </div>
                      {action.description && (
                        <p className="text-sm text-clay-300 mt-1">{action.description}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Updates */}
        {portal.recent_updates.length > 0 && (
          <div>
            <h2
              className="text-base font-semibold text-clay-200 mb-3 flex items-center gap-2"
              style={brandColor ? { color: brandColor } : undefined}
            >
              <MessageSquare className="h-4 w-4" />
              Recent Updates
            </h2>
            <div className="space-y-3">
              {portal.recent_updates.map((update) => {
                const hasAuthor = update.author_name || update.author_org;
                const isInternal = !update.author_org || update.author_org === "internal";
                const orgLabel = isInternal ? "The Kiln" : (portal.name || "Client");
                const initial = isInternal ? "K" : (orgLabel[0] || "C").toUpperCase();
                const isDeliverable = update.type === "deliverable";
                const needsApproval = isDeliverable && update.approval_status && (update.approval_status === "pending_review" || update.approval_status === "resubmitted");

                return (
                  <div
                    key={update.id}
                    className={cn(
                      "rounded-lg border bg-clay-850 p-4 retro-raised",
                      isDeliverable ? "border-purple-500/20" : "border-clay-700"
                    )}
                  >
                    {/* Header */}
                    <div className="flex items-center gap-2 mb-2">
                      <span className={cn(
                        "text-[11px] px-2 py-0.5 rounded-full font-medium",
                        TYPE_COLORS[update.type] || TYPE_COLORS.update
                      )}>
                        {update.type}
                      </span>
                      <h4 className="text-base font-medium text-clay-100 flex-1">{update.title}</h4>
                      <span className="text-xs text-clay-300 shrink-0">
                        {new Date(update.created_at * 1000).toLocaleDateString()}
                      </span>
                    </div>

                    {/* Author */}
                    {hasAuthor && (
                      <div className="flex items-center gap-2 mb-3">
                        <div
                          className={cn(
                            "h-7 w-7 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0",
                            isInternal
                              ? "bg-kiln-teal/20 text-kiln-teal"
                              : "bg-purple-500/20 text-purple-400"
                          )}
                        >
                          {initial}
                        </div>
                        <div className="min-w-0">
                          {update.author_name && (
                            <span className="text-sm font-medium text-clay-200">{update.author_name}</span>
                          )}
                          <span
                            className={cn(
                              "text-xs ml-1.5",
                              isInternal ? "text-kiln-teal/60" : "text-purple-400/60"
                            )}
                          >
                            {orgLabel}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Body */}
                    {update.body && (
                      <p className="text-sm text-clay-300 whitespace-pre-wrap leading-relaxed">{update.body}</p>
                    )}

                    {/* Approval actions for deliverables */}
                    {needsApproval && clientName && (
                      <div className="mt-3 pt-3 border-t border-clay-700/40">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
                            {update.approval_status === "resubmitted" ? "Resubmitted for Review" : "Pending Your Review"}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleApproval(update.id, "approve")}
                            className="text-sm px-4 py-2 rounded-lg font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5"
                          >
                            <Check className="h-3.5 w-3.5" />
                            Approve
                          </button>
                          <button
                            onClick={() => setRevisionInput(revisionInput === update.id ? null : update.id)}
                            className="text-sm px-4 py-2 rounded-lg font-medium border border-orange-500/30 text-orange-400 hover:bg-orange-500/10 transition-colors flex items-center gap-1.5"
                          >
                            <RotateCcw className="h-3.5 w-3.5" />
                            Request Revision
                          </button>
                        </div>
                        {revisionInput === update.id && (
                          <div className="mt-2 flex gap-2">
                            <input
                              type="text"
                              value={revisionNotes}
                              onChange={(e) => setRevisionNotes(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleApproval(update.id, "request_revision", revisionNotes);
                              }}
                              placeholder="What needs to change?"
                              className="flex-1 bg-clay-900 border border-orange-500/30 rounded-lg px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-300 focus:outline-none focus:border-orange-400"
                              autoFocus
                            />
                            <button
                              onClick={() => handleApproval(update.id, "request_revision", revisionNotes)}
                              className="text-sm px-3 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-white transition-colors"
                            >
                              Send
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Approval status badge */}
                    {isDeliverable && update.approval_status === "approved" && (
                      <div className="mt-3 pt-3 border-t border-clay-700/40">
                        <span className="text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                          <CheckCircle className="h-3 w-3 inline mr-1" />
                          Approved
                        </span>
                      </div>
                    )}

                    {/* Comment input */}
                    {clientName && (
                      <div className="mt-3 pt-3 border-t border-clay-700/40">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={commentTexts[update.id] || ""}
                            onChange={(e) => setCommentTexts((prev) => ({ ...prev, [update.id]: e.target.value }))}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handlePostComment(update.id);
                              }
                            }}
                            placeholder={`Comment as ${clientName}...`}
                            className="flex-1 bg-clay-900 border border-clay-600 rounded-lg px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-300 focus:outline-none focus:border-clay-400"
                          />
                          <button
                            onClick={() => handlePostComment(update.id)}
                            disabled={postingComment === update.id || !(commentTexts[update.id]?.trim())}
                            className="h-9 w-9 rounded-lg bg-clay-700 hover:bg-clay-600 flex items-center justify-center text-clay-300 transition-colors disabled:opacity-50"
                          >
                            {postingComment === update.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Send className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="pt-8 border-t border-clay-700 text-center">
          <p className="text-xs text-clay-300">Powered by The Kiln</p>
        </div>
      </div>
    </div>
  );
}
