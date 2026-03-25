"use client";

import { useState } from "react";
import {
  Clock,
  Bell,
  Milestone,
  Package,
  StickyNote,
  FileText,
  MessageSquare,
  Image,
  CheckSquare,
  Check,
  User,
} from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { PortalDetail } from "@/lib/types";
import { NotificationSettings } from "./notification-settings";

const TIMELINE_TYPES: Record<string, { dot: string; textColor: string; label: string; icon: React.ElementType }> = {
  update: { dot: "bg-blue-400", textColor: "text-blue-400", label: "Update", icon: Bell },
  milestone: { dot: "bg-emerald-400", textColor: "text-emerald-400", label: "Milestone", icon: Milestone },
  deliverable: { dot: "bg-purple-400", textColor: "text-purple-400", label: "Deliverable", icon: Package },
  note: { dot: "bg-amber-400", textColor: "text-amber-400", label: "Note", icon: StickyNote },
};

const PRIORITY_ORDER: Record<string, number> = { high: 0, normal: 1, low: 2 };
const PRIORITY_DOTS: Record<string, string> = { high: "bg-red-400", normal: "bg-clay-400", low: "bg-clay-600" };
const OWNER_STYLE: Record<string, string> = {
  internal: "text-kiln-teal bg-kiln-teal/10",
  client: "text-orange-400 bg-orange-500/10",
};

interface TimelineSidebarProps {
  portal: PortalDetail;
  onSelectUpdate: (updateId: string, title?: string) => void;
  activeUpdateId: string | null;
  slug: string;
  onToggleAction: (actionId: string) => void;
  onPortalUpdated: () => void;
}

export function TimelineSidebar({
  portal,
  onSelectUpdate,
  activeUpdateId,
  slug,
  onToggleAction,
  onPortalUpdated,
}: TimelineSidebarProps) {
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(["update", "milestone", "deliverable", "note"])
  );

  const updates = [...portal.recent_updates].sort((a, b) => b.created_at - a.created_at);
  const visibleUpdates = updates.filter((u) => activeFilters.has(u.type));

  const openActions = portal.actions
    .filter((a) => a.status !== "done")
    .sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 1) - (PRIORITY_ORDER[b.priority] ?? 1));

  const allTypes = Object.keys(TIMELINE_TYPES);

  function toggleFilter(type: string) {
    const isSolo = activeFilters.size === 1 && activeFilters.has(type);
    if (isSolo) {
      setActiveFilters(new Set(allTypes));
    } else {
      setActiveFilters(new Set([type]));
    }
  }

  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="sticky top-4 space-y-4 max-h-[calc(100vh-6rem)] overflow-y-auto">
      {/* Quick stats */}
      <div className="flex items-center gap-4 text-[11px] text-clay-400 px-1">
        <span className="flex items-center gap-1" title="SOPs">
          <FileText className="h-3 w-3" />{portal.sops.length}
        </span>
        <span className="flex items-center gap-1" title="Updates">
          <MessageSquare className="h-3 w-3" />{portal.recent_updates.length}
        </span>
        <span className="flex items-center gap-1" title="Files">
          <Image className="h-3 w-3" />{portal.media.length}
        </span>
        <span className="flex items-center gap-1" title="Actions">
          <CheckSquare className="h-3 w-3" />{portal.actions.length}
        </span>
      </div>

      {/* Open Actions */}
      {openActions.length > 0 && (
        <div className="rounded-xl border border-clay-700 bg-clay-800 p-4">
          <h3 className="text-xs font-semibold text-clay-200 mb-3 flex items-center gap-2">
            <CheckSquare className="h-3.5 w-3.5 text-clay-400" />
            Open Actions
            <span className="text-[10px] bg-clay-700 text-clay-400 px-1.5 py-0.5 rounded-full ml-auto">
              {openActions.length}
            </span>
          </h3>
          <div className="space-y-1.5">
            {openActions.slice(0, 8).map((action) => {
              const isOverdue = action.due_date && action.due_date < today;
              return (
                <div key={action.id} className="flex items-start gap-2 group">
                  <button
                    onClick={() => onToggleAction(action.id)}
                    className="mt-0.5 h-3.5 w-3.5 rounded border border-clay-600 flex items-center justify-center shrink-0 hover:border-emerald-400 hover:bg-emerald-400/10 transition-colors"
                    title="Mark done"
                  >
                    <Check className="h-2 w-2 text-clay-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", PRIORITY_DOTS[action.priority] || PRIORITY_DOTS.normal)} />
                      <span className={cn("text-[11px] truncate", isOverdue ? "text-red-400" : "text-clay-200")}>
                        {action.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className={cn("text-[9px] px-1 py-0.5 rounded font-medium", OWNER_STYLE[action.owner] || OWNER_STYLE.internal)}>
                        {action.owner}
                      </span>
                      {action.due_date && (
                        <span className={cn("text-[9px]", isOverdue ? "text-red-400" : "text-clay-500")}>
                          {isOverdue ? "Overdue" : action.due_date}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            {openActions.length > 8 && (
              <p className="text-[10px] text-clay-500 pl-5">+{openActions.length - 8} more</p>
            )}
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="rounded-xl border border-clay-700 bg-clay-800 p-4">
        <h3 className="text-xs font-semibold text-clay-200 mb-3 flex items-center gap-2">
          <Clock className="h-3.5 w-3.5 text-clay-400" />
          Timeline
          <span className="text-[10px] bg-clay-700 text-clay-400 px-1.5 py-0.5 rounded-full ml-auto">
            {visibleUpdates.length}
          </span>
        </h3>

        {/* Labeled filter chips */}
        <div className="flex flex-wrap items-center gap-1.5 mb-3">
          {Object.entries(TIMELINE_TYPES).map(([type, config]) => {
            const active = activeFilters.has(type);
            return (
              <button
                key={type}
                onClick={() => toggleFilter(type)}
                className={cn(
                  "flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium transition-all border",
                  active
                    ? `${config.textColor} border-current/20 bg-current/5`
                    : "text-clay-500 border-clay-700 bg-transparent opacity-50"
                )}
              >
                <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
                {config.label}
              </button>
            );
          })}
        </div>

        {visibleUpdates.length === 0 ? (
          <div className="text-center py-6 space-y-2">
            <Clock className="h-8 w-8 text-clay-600 mx-auto" />
            <p className="text-xs text-clay-400 font-medium">No activity yet</p>
            <p className="text-[10px] text-clay-500">
              Create your first post to start<br />building the timeline.
            </p>
          </div>
        ) : (
          <div className="relative pl-5">
            {/* Vertical line */}
            <div className="absolute left-[7px] top-1 bottom-1 w-px bg-clay-700" />

            <div className="space-y-1">
              {visibleUpdates.map((update) => {
                const config = TIMELINE_TYPES[update.type] || TIMELINE_TYPES.update;
                const isActive = update.id === activeUpdateId;
                const bodySnippet = update.body
                  ? update.body.replace(/[#*_`>\-\[\]()]/g, "").trim().slice(0, 60)
                  : null;

                return (
                  <button
                    key={update.id}
                    onClick={() => onSelectUpdate(update.id, update.title)}
                    className={cn(
                      "relative flex items-start gap-2 w-full text-left rounded-md px-2 py-1.5 -ml-2 transition-colors group",
                      isActive
                        ? "bg-clay-700/60 border-l-2 border-l-kiln-teal ml-[-10px] pl-3"
                        : "hover:bg-clay-750/50"
                    )}
                  >
                    {/* Dot */}
                    <span
                      className={cn(
                        "absolute top-2.5 h-2.5 w-2.5 rounded-full border-2 border-clay-800 shrink-0 z-10",
                        isActive ? "-left-[11px]" : "-left-[13px]",
                        config.dot
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <p className={cn(
                        "text-xs truncate",
                        isActive ? "text-clay-100 font-medium" : "text-clay-200"
                      )}>
                        {update.title}
                      </p>
                      {bodySnippet && (
                        <p className="text-[10px] text-clay-500 truncate mt-0.5">
                          {bodySnippet}{update.body && update.body.length > 60 ? "..." : ""}
                        </p>
                      )}
                      <div className="flex items-center gap-1 mt-0.5">
                        <span className={cn("text-[9px] font-medium", config.textColor)}>
                          {config.label}
                        </span>
                        <span className="text-clay-600 text-[9px]">&middot;</span>
                        <span className="text-[10px] text-clay-500">
                          {formatRelativeTime(update.created_at)}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Notification Settings */}
      <NotificationSettings
        slug={slug}
        slackWebhookUrl={portal.meta.slack_webhook_url ?? null}
        notificationEmails={portal.meta.notification_emails ?? []}
        onSaved={onPortalUpdated}
        compact
      />
    </div>
  );
}
