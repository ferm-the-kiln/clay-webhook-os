"use client";

import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { fetchPublicPortal } from "@/lib/api";
import type { PublicPortalView } from "@/lib/types";
import { cn } from "@/lib/utils";
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
} from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";

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

const OWNER_BADGE: Record<string, string> = {
  internal: "text-blue-400 bg-blue-500/10",
  client: "text-orange-400 bg-orange-500/10",
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

  useEffect(() => {
    if (!token) {
      setError("No access token provided");
      setLoading(false);
      return;
    }
    fetchPublicPortal(slug, token)
      .then(setPortal)
      .catch((e) => setError(e instanceof Error ? e.message : "Access denied"))
      .finally(() => setLoading(false));
  }, [slug, token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-clay-900 flex items-center justify-center">
        <div className="animate-pulse text-clay-400">Loading portal...</div>
      </div>
    );
  }

  if (error || !portal) {
    return (
      <div className="min-h-screen bg-clay-900 flex items-center justify-center">
        <div className="text-center space-y-3">
          <ShieldAlert className="h-12 w-12 text-red-400 mx-auto" />
          <h1 className="text-lg font-semibold text-clay-100">Access Denied</h1>
          <p className="text-sm text-clay-400">{error || "Invalid or expired share link."}</p>
        </div>
      </div>
    );
  }

  const openActions = portal.actions.filter((a) => a.status !== "done");
  const doneActions = portal.actions.filter((a) => a.status === "done");

  return (
    <div className="min-h-screen bg-clay-900">
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div
          className="space-y-2"
          style={portal.brand_color ? { borderTop: `3px solid ${portal.brand_color}`, paddingTop: "1rem" } : undefined}
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
            <h2 className="text-sm font-semibold text-clay-200 mb-3 flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Standard Operating Procedures ({portal.sops.length})
            </h2>
            <div className="space-y-2">
              {portal.sops.map((sop) => (
                <div key={sop.id} className="rounded-lg border border-clay-700 bg-clay-800 overflow-hidden">
                  <button
                    onClick={() => setExpandedSop(expandedSop === sop.id ? null : sop.id)}
                    className="w-full flex items-center gap-3 p-3 text-left hover:bg-clay-750 transition-colors"
                  >
                    {expandedSop === sop.id ? (
                      <ChevronDown className="h-4 w-4 text-clay-400 shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-clay-400 shrink-0" />
                    )}
                    <span className="flex-1 text-sm font-medium text-clay-100">{sop.title}</span>
                    {portal.sop_acks?.[sop.id] && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium flex items-center gap-1 shrink-0">
                        <CheckCircle className="h-2.5 w-2.5" />
                        Acknowledged {formatRelativeTime(portal.sop_acks[sop.id].acknowledged_at)}
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
                    <div className="border-t border-clay-700 p-4">
                      <div className="prose prose-invert prose-sm max-w-none text-clay-300 whitespace-pre-wrap">
                        {sop.content || "No content."}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Items */}
        {portal.actions.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-clay-200 mb-3 flex items-center gap-2">
              <CheckSquare className="h-4 w-4" />
              Action Items ({openActions.length} open)
            </h2>
            {portal.actions.length > 0 && (
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-clay-500">
                    {doneActions.length} of {portal.actions.length} complete
                  </span>
                  <span className="text-[10px] text-clay-500">
                    {Math.round((doneActions.length / portal.actions.length) * 100)}%
                  </span>
                </div>
                <div className="h-1.5 bg-clay-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-400 rounded-full transition-all duration-300"
                    style={{ width: `${(doneActions.length / portal.actions.length) * 100}%` }}
                  />
                </div>
              </div>
            )}
            <div className="space-y-2">
              {[...openActions, ...doneActions].map((action) => (
                <div
                  key={action.id}
                  className="flex items-start gap-3 rounded-lg border border-clay-700 bg-clay-800 p-3"
                >
                  {action.status === "done" ? (
                    <CheckSquare className="h-4 w-4 text-emerald-400 mt-0.5 shrink-0" />
                  ) : (
                    <Square className="h-4 w-4 text-clay-400 mt-0.5 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={cn("h-2 w-2 rounded-full shrink-0", PRIORITY_DOTS[action.priority])} />
                      <span
                        className={cn(
                          "text-sm font-medium",
                          action.status === "done" ? "text-clay-500 line-through" : "text-clay-100"
                        )}
                      >
                        {action.title}
                      </span>
                      <span
                        className={cn(
                          "text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0",
                          OWNER_BADGE[action.owner] || OWNER_BADGE.internal
                        )}
                      >
                        <User className="h-2.5 w-2.5 inline mr-0.5" />
                        {action.owner}
                      </span>
                    </div>
                    {action.description && (
                      <p className="text-xs text-clay-400 mt-0.5">{action.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Updates */}
        {portal.recent_updates.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-clay-200 mb-3 flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Recent Updates
            </h2>
            <div className="space-y-2">
              {portal.recent_updates.map((update) => (
                <div
                  key={update.id}
                  className="rounded-lg border border-clay-700 bg-clay-800 p-3"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-clay-700 text-clay-300 uppercase font-medium">
                      {update.type}
                    </span>
                    <h4 className="text-sm font-medium text-clay-100">{update.title}</h4>
                    <span className="ml-auto text-[10px] text-clay-500">
                      {new Date(update.created_at * 1000).toLocaleDateString()}
                    </span>
                  </div>
                  {update.body && (
                    <p className="text-xs text-clay-300 whitespace-pre-wrap">{update.body}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="pt-8 border-t border-clay-700 text-center">
          <p className="text-xs text-clay-500">Powered by The Kiln</p>
        </div>
      </div>
    </div>
  );
}
