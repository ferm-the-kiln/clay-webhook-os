"use client";

import { useState } from "react";
import {
  Clock,
  Bell,
  Milestone,
  Package,
  StickyNote,
  Eye,
  FileText,
  MessageSquare,
  Image,
  CheckSquare,
} from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { PortalDetail } from "@/lib/types";
import { NotificationSettings } from "./notification-settings";

const TIMELINE_COLORS: Record<string, { dot: string; icon: React.ElementType }> = {
  update: { dot: "bg-blue-400", icon: Bell },
  milestone: { dot: "bg-emerald-400", icon: Milestone },
  deliverable: { dot: "bg-purple-400", icon: Package },
  note: { dot: "bg-amber-400", icon: StickyNote },
};

// ── Main sidebar ──

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
  onPortalUpdated,
}: TimelineSidebarProps) {
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(["update", "milestone", "deliverable", "note"])
  );

  const updates = [...portal.recent_updates].sort((a, b) => b.created_at - a.created_at);
  const visibleUpdates = updates.filter((u) => activeFilters.has(u.type));

  function toggleFilter(type: string) {
    const next = new Set(activeFilters);
    if (next.has(type)) {
      if (next.size > 1) next.delete(type);
    } else {
      next.add(type);
    }
    setActiveFilters(next);
  }

  return (
    <div className="sticky top-4 space-y-4 max-h-[calc(100vh-6rem)] overflow-y-auto">
      {/* Client view status + quick stats */}
      <div className="space-y-2 px-1">
        <div className="flex items-center gap-2">
          <Eye className="h-3.5 w-3.5 text-clay-500" />
          <span className="text-[11px] text-clay-400">
            {portal.view_stats?.last_viewed_at
              ? `Client viewed ${formatRelativeTime(portal.view_stats.last_viewed_at)}`
              : "Client hasn\u2019t viewed yet"}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[11px] text-clay-400">
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
      </div>

      {/* Timeline */}
      <div className="rounded-xl border border-clay-700 bg-clay-800 p-4">
        <h3 className="text-xs font-semibold text-clay-200 mb-3 flex items-center gap-2">
          <Clock className="h-3.5 w-3.5 text-clay-400" />
          Timeline
          <span className="text-[10px] bg-clay-700 text-clay-400 px-1.5 py-0.5 rounded-full ml-auto">
            {visibleUpdates.length}
          </span>
        </h3>

        {/* Type filters */}
        <div className="flex items-center gap-2 mb-3">
          {Object.entries(TIMELINE_COLORS).map(([type, { dot }]) => (
            <button
              key={type}
              onClick={() => toggleFilter(type)}
              className={cn(
                "h-3 w-3 rounded-full transition-opacity",
                dot,
                !activeFilters.has(type) && "opacity-20"
              )}
              title={type.charAt(0).toUpperCase() + type.slice(1)}
            />
          ))}
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

            <div className="space-y-2.5">
              {visibleUpdates.map((update) => {
                const config = TIMELINE_COLORS[update.type] || TIMELINE_COLORS.update;
                const isActive = update.id === activeUpdateId;

                return (
                  <button
                    key={update.id}
                    onClick={() => onSelectUpdate(update.id, update.title)}
                    className={cn(
                      "relative flex items-start gap-2 w-full text-left rounded-md px-2 py-1.5 -ml-2 transition-colors",
                      isActive ? "bg-clay-750" : "hover:bg-clay-750/50"
                    )}
                  >
                    {/* Dot */}
                    <span
                      className={cn(
                        "absolute -left-[13px] top-2.5 h-2.5 w-2.5 rounded-full border-2 border-clay-800 shrink-0 z-10",
                        config.dot
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-clay-200 truncate">{update.title}</p>
                      <span className="text-[10px] text-clay-500">
                        {formatRelativeTime(update.created_at)}
                      </span>
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
